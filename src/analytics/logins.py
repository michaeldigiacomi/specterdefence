"""Login analytics service for tracking and analyzing login events."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, and_, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.anomalies import AnomalyDetector, AnomalyResult, AnomalyType
from src.analytics.geo_ip import GeoIPClient, get_geo_ip_client
from src.analytics.threat_intel import ThreatIntelClient, get_threat_intel_client
from src.models.analytics import AnomalyDetectionConfig, LoginAnalyticsModel, UserLoginHistoryModel
from src.models.audit_log import AuditLogModel, LogType

logger = logging.getLogger(__name__)


class LoginAnalyticsService:
    """Service for processing and analyzing login events."""

    def __init__(
        self,
        db: AsyncSession,
        geo_ip_client: GeoIPClient | None = None,
        anomaly_detector: AnomalyDetector | None = None,
        threat_intel_client: ThreatIntelClient | None = None,
    ):
        """
        Initialize the login analytics service.

        Args:
            db: Database session
            geo_ip_client: Geo-IP client (creates default if not provided)
            anomaly_detector: Anomaly detector (creates default if not provided)
            threat_intel_client: CTI client (creates default if not provided)
        """
        self.db = db
        self.geo_ip = geo_ip_client or get_geo_ip_client()
        self.detector = anomaly_detector or AnomalyDetector()
        self.threat_intel = threat_intel_client or get_threat_intel_client()

    def _apply_tenant_filter(self, query: Any, model_class: Any, tenant_id: str | list[str] | None) -> Any:
        if tenant_id is None:
            return query
        if tenant_id == "NONE":
            return query.where(model_class.tenant_id == "NONE_ASSIGNED")
        if isinstance(tenant_id, list):
            return query.where(model_class.tenant_id.in_(tenant_id))
        return query.where(model_class.tenant_id == tenant_id)

    async def process_login_event(
        self,
        user_email: str,
        tenant_id: str,
        ip_address: str,
        login_time: datetime,
        is_success: bool = True,
        failure_reason: str | None = None,
        audit_log_id: UUID | None = None,
    ) -> LoginAnalyticsModel:
        """
        Process a login event and store analytics data.

        Args:
            user_email: User's email address
            tenant_id: Internal tenant UUID
            ip_address: IP address of the login
            login_time: Timestamp of the login
            is_success: Whether the login was successful
            failure_reason: Reason for failure if applicable
            audit_log_id: Reference to original audit log

        Returns:
            Created LoginAnalyticsModel instance
        """
        # Look up geographic information
        geo = await self.geo_ip.lookup(ip_address)

        # Get user's login history
        user_history = await self._get_or_create_user_history(user_email, tenant_id)

        # Get previous login for travel analysis
        previous_login = await self._get_previous_login(user_email, tenant_id)

        # Build login data for anomaly detection
        current_login = {
            "user_email": user_email,
            "ip_address": ip_address,
            "country_code": geo.country_code,
            "city": geo.city,
            "latitude": geo.latitude,
            "longitude": geo.longitude,
            "login_time": login_time,
            "is_success": is_success,
            "failure_reason": failure_reason,
        }

        prev_login_data = None
        if previous_login:
            prev_login_data = {
                "latitude": previous_login.latitude,
                "longitude": previous_login.longitude,
                "country_code": previous_login.country_code,
                "city": previous_login.city,
                "login_time": previous_login.login_time,
            }

        user_history_data = {
            "known_countries": user_history.known_countries,
            "known_ips": user_history.known_ips,
            "failed_attempts_24h": user_history.failed_attempts_24h,
        }

        # Look up IP reputation
        cti_data = await self.threat_intel.lookup_ip(ip_address)

        # Perform anomaly detection
        anomaly_results = self.detector.analyze_login(
            current_login=current_login,
            previous_login=prev_login_data,
            user_history=user_history_data,
            cti_data=cti_data,
        )

        # Extract anomaly flags and calculate max risk score
        anomaly_flags = []
        max_risk_score = 0

        for result in anomaly_results:
            if result.detected:
                anomaly_flags.append(result.type.value)
                max_risk_score = max(max_risk_score, result.risk_score)
                logger.info(f"Anomaly detected for {user_email}: {result.message}")

        # Create login analytics record
        login_record = LoginAnalyticsModel(
            audit_log_id=audit_log_id,
            user_email=user_email,
            tenant_id=tenant_id,
            ip_address=ip_address,
            country=geo.country,
            country_code=geo.country_code,
            city=geo.city,
            region=geo.region,
            latitude=geo.latitude,
            longitude=geo.longitude,
            login_time=login_time,
            is_success=is_success,
            failure_reason=failure_reason,
            anomaly_flags=anomaly_flags,
            risk_score=max_risk_score,
            is_malicious=cti_data.get("is_malicious", False),
            threat_score=cti_data.get("threat_score", 0),
            threat_tags=cti_data.get("tags", []),
            threat_sources=cti_data.get("sources", []),
        )

        self.db.add(login_record)
        await self.db.flush()

        # Update user history
        await self._update_user_history(
            user_history=user_history, login_record=login_record, anomaly_results=anomaly_results
        )

        await self.db.commit()

        return login_record

    async def _get_or_create_user_history(
        self, user_email: str, tenant_id: str
    ) -> UserLoginHistoryModel:
        """Get or create user login history record."""
        result = await self.db.execute(
            select(UserLoginHistoryModel).where(
                and_(
                    UserLoginHistoryModel.user_email == user_email,
                    UserLoginHistoryModel.tenant_id == tenant_id,
                )
            )
        )

        history = result.scalar_one_or_none()

        if history is None:
            history = UserLoginHistoryModel(
                user_email=user_email,
                tenant_id=tenant_id,
                known_countries=[],
                known_ips=[],
                total_logins=0,
                failed_attempts_24h=0,
            )
            self.db.add(history)
            await self.db.flush()

        return history

    async def _get_previous_login(
        self, user_email: str, tenant_id: str
    ) -> LoginAnalyticsModel | None:
        """Get the most recent successful login for a user."""
        result = await self.db.execute(
            select(LoginAnalyticsModel)
            .where(
                and_(
                    LoginAnalyticsModel.user_email == user_email,
                    LoginAnalyticsModel.tenant_id == tenant_id,
                    LoginAnalyticsModel.is_success,
                )
            )
            .order_by(desc(LoginAnalyticsModel.login_time))
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def _update_user_history(
        self,
        user_history: UserLoginHistoryModel,
        login_record: LoginAnalyticsModel,
        anomaly_results: list[AnomalyResult],
    ):
        """Update user login history based on new login."""
        # Update failed attempts counter
        if not login_record.is_success:
            user_history.failed_attempts_24h += 1
        else:
            # Reset counter on successful login
            user_history.failed_attempts_24h = 0

        # Only update known countries/IPs for successful logins
        if login_record.is_success:
            # Update known countries
            if login_record.country_code:
                country_result = next(
                    (r for r in anomaly_results if r.type == AnomalyType.NEW_COUNTRY), None
                )

                # Add to known countries if configured to auto-add
                if country_result and country_result.detected:
                    config = await self._get_anomaly_config(user_history.tenant_id)
                    if config is None or config.auto_add_known_countries:
                        user_history.known_countries = user_history.known_countries + [
                            login_record.country_code
                        ]
                elif not country_result or not country_result.detected:
                    # Already known, ensure it's in the list
                    if login_record.country_code not in user_history.known_countries:
                        user_history.known_countries = user_history.known_countries + [
                            login_record.country_code
                        ]

            # Update known IPs
            if login_record.ip_address and login_record.ip_address not in user_history.known_ips:
                user_history.known_ips = user_history.known_ips + [login_record.ip_address]

            # Update last login info
            user_history.last_login_time = login_record.login_time
            user_history.last_login_country = login_record.country_code
            user_history.last_login_ip = login_record.ip_address
            user_history.last_latitude = login_record.latitude
            user_history.last_longitude = login_record.longitude
            user_history.total_logins += 1

    async def _get_anomaly_config(self, tenant_id: str) -> AnomalyDetectionConfig | None:
        """Get anomaly detection configuration for a tenant."""
        result = await self.db.execute(
            select(AnomalyDetectionConfig).where(AnomalyDetectionConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def query_logins(
        self,
        tenant_id: str | list[str] | None = None,
        user_email: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        ip_address: str | None = None,
        country: str | None = None,
        country_code: str | None = None,
        is_success: bool | None = None,
        has_anomaly: bool | None = None,
        anomaly_type: str | None = None,
        min_risk_score: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LoginAnalyticsModel], int]:
        """
        Query login analytics with filters.

        Returns:
            Tuple of (login records list, total count)
        """
        query = select(LoginAnalyticsModel)
        count_query = select(func.count(LoginAnalyticsModel.id))

        filters = []

        query = self._apply_tenant_filter(query, LoginAnalyticsModel, tenant_id)
        count_query = self._apply_tenant_filter(count_query, LoginAnalyticsModel, tenant_id)

        if user_email:
            filters.append(LoginAnalyticsModel.user_email == user_email)

        if start_time:
            # Strip timezone info — the DB column is TIMESTAMP WITHOUT TIME ZONE
            if start_time.tzinfo is not None:
                start_time = start_time.replace(tzinfo=None)
            filters.append(LoginAnalyticsModel.login_time >= start_time)

        if end_time:
            if end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)
            filters.append(LoginAnalyticsModel.login_time <= end_time)

        if ip_address:
            filters.append(LoginAnalyticsModel.ip_address == ip_address)

        if country:
            filters.append(LoginAnalyticsModel.country.ilike(f"%{country}%"))

        if country_code:
            filters.append(LoginAnalyticsModel.country_code == country_code.upper())

        if is_success is not None:
            filters.append(LoginAnalyticsModel.is_success == is_success)

        if has_anomaly is not None:
            if has_anomaly:
                filters.append(cast(LoginAnalyticsModel.anomaly_flags, String) != '[]')
            else:
                filters.append(
                    or_(
                        cast(LoginAnalyticsModel.anomaly_flags, String) == '[]',
                        LoginAnalyticsModel.anomaly_flags.is_(None),
                    )
                )

        if anomaly_type:
            filters.append(LoginAnalyticsModel.anomaly_flags.contains([anomaly_type]))

        if min_risk_score is not None:
            filters.append(LoginAnalyticsModel.risk_score >= min_risk_score)

        # Apply filters
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Apply ordering, limit, offset
        query = query.order_by(desc(LoginAnalyticsModel.login_time)).offset(offset).limit(limit)

        result = await self.db.execute(query)
        logins = result.scalars().all()

        return list(logins), total

    async def get_user_login_summary(self, user_email: str, tenant_id: str) -> dict[str, Any]:
        """Get summary statistics for a user's login activity."""
        # Get user history
        result = await self.db.execute(
            select(UserLoginHistoryModel).where(
                and_(
                    UserLoginHistoryModel.user_email == user_email,
                    UserLoginHistoryModel.tenant_id == tenant_id,
                )
            )
        )
        history = result.scalar_one_or_none()

        if history is None:
            return {
                "user_email": user_email,
                "tenant_id": tenant_id,
                "total_logins": 0,
                "known_countries": [],
                "known_ips_count": 0,
                "failed_attempts_24h": 0,
            }

        # Get recent anomalies
        result = await self.db.execute(
            select(LoginAnalyticsModel)
            .where(
                and_(
                    LoginAnalyticsModel.user_email == user_email,
                    LoginAnalyticsModel.tenant_id == tenant_id,
                    cast(LoginAnalyticsModel.anomaly_flags, String) != '[]',
                )
            )
            .order_by(desc(LoginAnalyticsModel.login_time))
            .limit(10)
        )
        recent_anomalies = result.scalars().all()

        return {
            "user_email": user_email,
            "tenant_id": tenant_id,
            "total_logins": history.total_logins,
            "known_countries": history.known_countries,
            "known_ips_count": len(history.known_ips),
            "last_login_time": history.last_login_time.isoformat()
            if history.last_login_time
            else None,
            "last_login_country": history.last_login_country,
            "failed_attempts_24h": history.failed_attempts_24h,
            "recent_anomalies": [
                {
                    "time": a.login_time.isoformat(),
                    "anomaly_flags": a.anomaly_flags,
                    "risk_score": a.risk_score,
                    "country": a.country,
                    "ip_address": a.ip_address,
                }
                for a in recent_anomalies
            ],
        }

    async def process_audit_log_signins(self, tenant_id: str, limit: int = 100) -> int:
        """
        Process unprocessed signin audit logs and create login analytics.

        Args:
            tenant_id: Tenant ID to process
            limit: Maximum number of logs to process

        Returns:
            Number of logs processed
        """
        # Get unprocessed signin logs
        result = await self.db.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    # Handle both signin and general audit types that are signin-related
                    AuditLogModel.log_type == LogType.SIGNIN,
                    AuditLogModel.processed.is_(False),
                )
            )
            .order_by(AuditLogModel.o365_created_at)
            .limit(limit)
        )

        logs = result.scalars().all()
        processed_count = 0

        for log in logs:
            try:
                raw_data = log.raw_data

                if not isinstance(raw_data, dict):
                    logger.warning(f"Skipping audit log {log.id}: raw_data is not a dict")
                    log.processed = True
                    continue

                # Extract relevant fields from O365 signin log
                user_email = raw_data.get("UserId") or raw_data.get("UserPrincipalName")
                ip_address = raw_data.get("ClientIP") or raw_data.get("IpAddress")

                if not user_email or not ip_address:
                    logger.warning(f"Skipping audit log {log.id}: missing user_email or ip_address")
                    log.processed = True
                    continue

                # Parse login time
                login_time_str = raw_data.get("CreationTime") or raw_data.get("CreatedDateTime")
                if login_time_str:
                    try:
                        login_time = datetime.fromisoformat(login_time_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        login_time = log.o365_created_at or log.created_at
                else:
                    login_time = log.o365_created_at or log.created_at

                # Determine success/failure
                is_success = True
                failure_reason = None

                if "ResultStatus" in raw_data:
                    # Check both ResultStatus and ErrorNumber
                    # ErrorNumber != "0" indicates failures like account lockouts, policy violations
                    is_success = raw_data.get("ResultStatus") == "Success" and raw_data.get("ErrorNumber", "0") == "0"
                    if not is_success:
                        # Try to find reason in ExtendedProperties
                        ext_props = raw_data.get("ExtendedProperties", [])
                        if isinstance(ext_props, list):
                            for prop in ext_props:
                                if isinstance(prop, dict) and prop.get("Name") == "ResultStatusDetail":
                                    failure_reason = prop.get("Value")
                                    break
                elif "Status" in raw_data:
                    status = raw_data.get("Status", {})
                    if isinstance(status, dict):
                        is_success = status.get("ErrorCode") == 0
                        if not is_success:
                            failure_reason = status.get("FailureReason") or status.get("AdditionalDetails")

                # Process the login event
                await self.process_login_event(
                    user_email=user_email,
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    login_time=login_time,
                    is_success=is_success,
                    failure_reason=failure_reason,
                    audit_log_id=log.id,
                )

                log.processed = True
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing audit log {log.id}: {e}")
                log.processed = True  # Mark as processed to avoid reprocessing

        await self.db.commit()
        return processed_count

    async def process_audit_log_general(self, tenant_id: str, limit: int = 100) -> int:
        """
        Process unprocessed non-signin audit logs and mark as processed.
        Can be extended to detect specific administrative anomalies.

        Args:
            tenant_id: Tenant ID to process
            limit: Maximum number of logs to process

        Returns:
            Number of logs processed
        """
        # Get unprocessed non-signin logs
        result = await self.db.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.log_type != LogType.SIGNIN,
                    AuditLogModel.processed.is_(False),
                )
            )
            .order_by(AuditLogModel.o365_created_at)
            .limit(limit)
        )

        logs = result.scalars().all()
        processed_count = 0

        for log in logs:
            try:
                # Placeholder for complex audit log analysis
                # e.g., identifying elevation of privilege, mass deletions, etc.

                log.processed = True
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing general audit log {log.id}: {e}")
                log.processed = True

        await self.db.commit()
        return processed_count
