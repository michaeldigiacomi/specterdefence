"""Failed login tracking service with Redis sliding window for brute force detection."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

logger = logging.getLogger(__name__)


@dataclass
class FailureCount:
    """Failure count result."""

    count: int
    window_start: datetime
    window_end: datetime
    key: str


@dataclass
class BruteForceAlert:
    """Brute force alert details."""

    triggered: bool
    user_email: str | None
    ip_address: str | None
    failure_count: int
    threshold: int
    window_minutes: int
    alert_type: str  # 'user', 'ip', or 'both'
    details: dict[str, Any]
    suppressed: bool = False


class FailedLoginTracker:
    """Track failed login attempts using Redis sliding window."""

    # Default configuration
    DEFAULT_FAILURE_THRESHOLD = 5
    DEFAULT_WINDOW_MINUTES = 5
    DEFAULT_SUPPRESS_AFTER_ALERT_MINUTES = 30

    # Redis key prefixes
    KEY_PREFIX_USER = "failed_login:user"
    KEY_PREFIX_IP = "failed_login:ip"
    KEY_PREFIX_ALERT_SUPPRESS = "brute_force_alert:suppress"

    # Error code mapping from Graph API
    ERROR_CODES = {
        0: "success",
        50126: "badPassword",
        50034: "userNotFound",
        50076: "mfaRequired",
        50079: "mfaRequired",
        50057: "userDisabled",
        50055: "passwordExpired",
        50053: "accountLocked",
        50058: "invalidRequest",
        50059: "invalidRequest",
        50061: "invalidRequest",
        50064: "accountDisabled",
        50127: "brokerNotAvailable",
        50128: "invalidDomain",
        50129: "deviceNotManaged",
        50132: "passwordExpired",
        50133: "sessionExpired",
        50144: "passwordExpired",
        50173: "refreshTokenExpired",
        80012: "policyRestriction",
        80014: "policyRestriction",
        80045: "conditionalAccessFailed",
        50072: "userNotFound",
        50074: "strongAuthRequired",
    }

    def __init__(
        self,
        redis_client: Any | None = None,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        window_minutes: int = DEFAULT_WINDOW_MINUTES,
        suppress_after_alert_minutes: int = DEFAULT_SUPPRESS_AFTER_ALERT_MINUTES,
    ):
        """
        Initialize the failed login tracker.

        Args:
            redis_client: Redis client instance (optional)
            failure_threshold: Number of failures to trigger alert
            window_minutes: Sliding window size in minutes
            suppress_after_alert_minutes: How long to suppress alerts after triggering
        """
        self.redis = redis_client
        self.failure_threshold = failure_threshold
        self.window_minutes = window_minutes
        self.suppress_after_alert_minutes = suppress_after_alert_minutes
        self._local_cache: dict[str, list[datetime]] = {}  # Fallback if Redis unavailable

    async def _get_redis(self) -> Any | None:
        """Get Redis client or None if unavailable."""
        if self.redis is None and HAS_REDIS:
            try:
                self.redis = await redis.from_url(
                    "redis://localhost:6379", encoding="utf-8", decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis unavailable, using local cache: {e}")
                return None
        return self.redis

    def _get_user_key(self, user_email: str, tenant_id: str) -> str:
        """Get Redis key for user failures."""
        return f"{self.KEY_PREFIX_USER}:{tenant_id}:{user_email.lower()}"

    def _get_ip_key(self, ip_address: str, tenant_id: str) -> str:
        """Get Redis key for IP failures."""
        return f"{self.KEY_PREFIX_IP}:{tenant_id}:{ip_address}"

    def _get_suppress_key(self, user_email: str, ip_address: str, tenant_id: str) -> str:
        """Get Redis key for alert suppression."""
        return f"{self.KEY_PREFIX_ALERT_SUPPRESS}:{tenant_id}:{user_email.lower()}:{ip_address}"

    @staticmethod
    def parse_error_code(error_code: int | None) -> str:
        """
        Parse Graph API error code to failure reason.

        Args:
            error_code: Error code from Graph API status.errorCode

        Returns:
            Human-readable failure reason
        """
        if error_code is None or error_code == 0:
            return "success"
        return FailedLoginTracker.ERROR_CODES.get(error_code, f"unknownError_{error_code}")

    async def record_failure(
        self,
        user_email: str,
        tenant_id: str,
        ip_address: str,
        error_code: int | None = None,
        failure_reason: str | None = None,
        timestamp: datetime | None = None,
    ) -> FailureCount:
        """
        Record a failed login attempt.

        Args:
            user_email: User's email address
            tenant_id: Tenant ID
            ip_address: IP address of the attempt
            error_code: Graph API error code
            failure_reason: Human-readable failure reason
            timestamp: When the failure occurred (defaults to now)

        Returns:
            FailureCount with current count in window
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Parse error code if not provided
        if failure_reason is None and error_code is not None:
            failure_reason = self.parse_error_code(error_code)

        user_key = self._get_user_key(user_email, tenant_id)
        ip_key = self._get_ip_key(ip_address, tenant_id)

        # Store failure details (for future use)
        _failure_data = {
            "timestamp": timestamp.isoformat(),
            "error_code": error_code,
            "failure_reason": failure_reason,
            "ip_address": ip_address,
        }

        redis_client = await self._get_redis()

        if redis_client:
            # Use Redis sorted sets for sliding window
            score = timestamp.timestamp()
            member = f"{timestamp.isoformat()}:{ip_address}"

            # Add to user failures
            await redis_client.zadd(user_key, {member: score})

            # Add to IP failures
            ip_member = f"{timestamp.isoformat()}:{user_email.lower()}"
            await redis_client.zadd(ip_key, {ip_member: score})

            # Set expiration on keys
            expire_seconds = self.window_minutes * 60 * 2  # 2x window for cleanup buffer
            await redis_client.expire(user_key, expire_seconds)
            await redis_client.expire(ip_key, expire_seconds)

            # Clean old entries outside window
            window_start = timestamp - timedelta(minutes=self.window_minutes)
            await redis_client.zremrangebyscore(user_key, 0, window_start.timestamp())
            await redis_client.zremrangebyscore(ip_key, 0, window_start.timestamp())

            # Get current counts
            user_count = await redis_client.zcard(user_key)
            ip_count = await redis_client.zcard(ip_key)
        else:
            # Fallback to local cache
            self._add_to_local_cache(user_key, timestamp)
            self._add_to_local_cache(ip_key, timestamp)
            user_count = len(self._local_cache.get(user_key, []))
            ip_count = len(self._local_cache.get(ip_key, []))

        window_end = timestamp
        window_start = timestamp - timedelta(minutes=self.window_minutes)

        return FailureCount(
            count=max(user_count, ip_count),
            window_start=window_start,
            window_end=window_end,
            key=f"{user_key}/{ip_key}",
        )

    def _add_to_local_cache(self, key: str, timestamp: datetime):
        """Add timestamp to local cache (fallback)."""
        if key not in self._local_cache:
            self._local_cache[key] = []

        # Clean old entries
        cutoff = timestamp - timedelta(minutes=self.window_minutes)
        self._local_cache[key] = [ts for ts in self._local_cache[key] if ts > cutoff]

        self._local_cache[key].append(timestamp)

    async def get_failure_count(
        self,
        user_email: str | None = None,
        ip_address: str | None = None,
        tenant_id: str | None = None,
    ) -> FailureCount:
        """
        Get current failure count for user and/or IP.

        Args:
            user_email: User's email (optional)
            ip_address: IP address (optional)
            tenant_id: Tenant ID (required if user_email or ip_address provided)

        Returns:
            FailureCount with current count
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)

        redis_client = await self._get_redis()

        user_count = 0
        ip_count = 0

        if redis_client:
            if user_email and tenant_id:
                user_key = self._get_user_key(user_email, tenant_id)
                await redis_client.zremrangebyscore(user_key, 0, window_start.timestamp())
                user_count = await redis_client.zcard(user_key)

            if ip_address and tenant_id:
                ip_key = self._get_ip_key(ip_address, tenant_id)
                await redis_client.zremrangebyscore(ip_key, 0, window_start.timestamp())
                ip_count = await redis_client.zcard(ip_key)
        else:
            # Local cache fallback
            if user_email and tenant_id:
                user_key = self._get_user_key(user_email, tenant_id)
                if user_key in self._local_cache:
                    self._local_cache[user_key] = [
                        ts for ts in self._local_cache[user_key] if ts > window_start
                    ]
                    user_count = len(self._local_cache[user_key])

            if ip_address and tenant_id:
                ip_key = self._get_ip_key(ip_address, tenant_id)
                if ip_key in self._local_cache:
                    self._local_cache[ip_key] = [
                        ts for ts in self._local_cache[ip_key] if ts > window_start
                    ]
                    ip_count = len(self._local_cache[ip_key])

        return FailureCount(
            count=max(user_count, ip_count),
            window_start=window_start,
            window_end=now,
            key=f"user:{user_email}/ip:{ip_address}",
        )

    async def check_brute_force(
        self, user_email: str, tenant_id: str, ip_address: str
    ) -> BruteForceAlert:
        """
        Check if brute force attack is detected.

        Args:
            user_email: User's email address
            tenant_id: Tenant ID
            ip_address: IP address

        Returns:
            BruteForceAlert with detection details
        """
        # Get failure counts
        user_count = await self.get_failure_count(user_email, None, tenant_id)
        ip_count = await self.get_failure_count(None, ip_address, tenant_id)

        # Determine if threshold exceeded
        user_exceeded = user_count.count >= self.failure_threshold
        ip_exceeded = ip_count.count >= self.failure_threshold

        # Check if alert should be suppressed
        suppress_key = self._get_suppress_key(user_email, ip_address, tenant_id)
        redis_client = await self._get_redis()

        suppressed = False
        if redis_client:
            suppress_ttl = await redis_client.ttl(suppress_key)
            suppressed = suppress_ttl > 0
        else:
            # Check local suppression
            suppressed = suppress_key in getattr(self, "_suppress_cache", {})

        # Build alert details
        alert_type = None
        failure_count = 0
        details = {}

        if user_exceeded and ip_exceeded:
            alert_type = "both"
            failure_count = max(user_count.count, ip_count.count)
            details = {
                "user_failures": user_count.count,
                "ip_failures": ip_count.count,
                "user_threshold": self.failure_threshold,
                "ip_threshold": self.failure_threshold,
            }
        elif user_exceeded:
            alert_type = "user"
            failure_count = user_count.count
            details = {
                "user_failures": user_count.count,
                "user_threshold": self.failure_threshold,
            }
        elif ip_exceeded:
            alert_type = "ip"
            failure_count = ip_count.count
            details = {
                "ip_failures": ip_count.count,
                "ip_threshold": self.failure_threshold,
            }

        triggered = alert_type is not None

        if triggered and not suppressed:
            # Set suppression
            if redis_client:
                suppress_seconds = self.suppress_after_alert_minutes * 60
                await redis_client.setex(suppress_key, suppress_seconds, "1")
            else:
                if not hasattr(self, "_suppress_cache"):
                    self._suppress_cache = {}
                self._suppress_cache[suppress_key] = datetime.utcnow()

        return BruteForceAlert(
            triggered=triggered,
            user_email=user_email,
            ip_address=ip_address,
            failure_count=failure_count,
            threshold=self.failure_threshold,
            window_minutes=self.window_minutes,
            alert_type=alert_type or "none",
            details=details,
            suppressed=suppressed and triggered,
        )

    async def clear_failures(
        self,
        user_email: str | None = None,
        ip_address: str | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Clear failure counts for user and/or IP.

        Called on successful login to reset counters.

        Args:
            user_email: User's email (optional)
            ip_address: IP address (optional)
            tenant_id: Tenant ID (required if user_email or ip_address provided)

        Returns:
            True if cleared successfully
        """
        redis_client = await self._get_redis()

        cleared = False

        if redis_client:
            if user_email and tenant_id:
                user_key = self._get_user_key(user_email, tenant_id)
                await redis_client.delete(user_key)
                cleared = True

            if ip_address and tenant_id:
                ip_key = self._get_ip_key(ip_address, tenant_id)
                await redis_client.delete(ip_key)
                cleared = True
        else:
            # Clear local cache
            if user_email and tenant_id:
                user_key = self._get_user_key(user_email, tenant_id)
                if user_key in self._local_cache:
                    del self._local_cache[user_key]
                    cleared = True

            if ip_address and tenant_id:
                ip_key = self._get_ip_key(ip_address, tenant_id)
                if ip_key in self._local_cache:
                    del self._local_cache[ip_key]
                    cleared = True

        # Also clear suppression
        if user_email and ip_address and tenant_id:
            suppress_key = self._get_suppress_key(user_email, ip_address, tenant_id)
            if redis_client:
                await redis_client.delete(suppress_key)
            elif hasattr(self, "_suppress_cache") and suppress_key in self._suppress_cache:
                del self._suppress_cache[suppress_key]

        return cleared

    async def get_failure_stats(self, tenant_id: str, minutes: int | None = None) -> dict[str, Any]:
        """
        Get failure statistics for a tenant.

        Args:
            tenant_id: Tenant ID
            minutes: Time window in minutes (defaults to window_minutes)

        Returns:
            Statistics dictionary
        """
        window = minutes or self.window_minutes
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window)

        redis_client = await self._get_redis()

        stats = {
            "tenant_id": tenant_id,
            "window_minutes": window,
            "window_start": window_start.isoformat(),
            "window_end": now.isoformat(),
            "total_user_failures": 0,
            "total_ip_failures": 0,
            "unique_users": 0,
            "unique_ips": 0,
            "top_users": [],
            "top_ips": [],
        }

        if redis_client:
            # Scan for user keys
            user_pattern = f"{self.KEY_PREFIX_USER}:{tenant_id}:*"
            user_keys = []
            async for key in redis_client.scan_iter(match=user_pattern):
                user_keys.append(key)
                count = await redis_client.zcard(key)
                stats["total_user_failures"] += count

            stats["unique_users"] = len(user_keys)

            # Get top users
            user_counts = []
            for key in user_keys[:10]:  # Limit to 10
                count = await redis_client.zcard(key)
                user_email = key.split(":")[-1]
                user_counts.append((user_email, count))

            user_counts.sort(key=lambda x: x[1], reverse=True)
            stats["top_users"] = [{"user": u, "failures": c} for u, c in user_counts[:5]]

            # Scan for IP keys
            ip_pattern = f"{self.KEY_PREFIX_IP}:{tenant_id}:*"
            ip_keys = []
            async for key in redis_client.scan_iter(match=ip_pattern):
                ip_keys.append(key)
                count = await redis_client.zcard(key)
                stats["total_ip_failures"] += count

            stats["unique_ips"] = len(ip_keys)

            # Get top IPs
            ip_counts = []
            for key in ip_keys[:10]:
                count = await redis_client.zcard(key)
                ip_address = key.split(":")[-1]
                ip_counts.append((ip_address, count))

            ip_counts.sort(key=lambda x: x[1], reverse=True)
            stats["top_ips"] = [{"ip": ip, "failures": c} for ip, c in ip_counts[:5]]

        return stats


# Singleton instance
_failed_login_tracker: FailedLoginTracker | None = None


def get_failed_login_tracker(
    redis_client: redis.Redis | None = None,
    failure_threshold: int = FailedLoginTracker.DEFAULT_FAILURE_THRESHOLD,
    window_minutes: int = FailedLoginTracker.DEFAULT_WINDOW_MINUTES,
) -> FailedLoginTracker:
    """Get or create singleton failed login tracker."""
    global _failed_login_tracker
    if _failed_login_tracker is None:
        _failed_login_tracker = FailedLoginTracker(
            redis_client=redis_client,
            failure_threshold=failure_threshold,
            window_minutes=window_minutes,
        )
    return _failed_login_tracker
