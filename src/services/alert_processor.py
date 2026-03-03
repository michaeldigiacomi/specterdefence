"""Alert processing service for SpecterDefence."""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.engine import AlertEngine
from src.database import async_session_maker
from src.models.alerts import EventType, SeverityLevel
from src.models.analytics import LoginAnalyticsModel, UserLoginHistoryModel

logger = logging.getLogger(__name__)


class AlertProcessor:
    """Background service for processing security events and sending alerts."""

    def __init__(self, check_interval: int = 60):
        """Initialize the alert processor.

        Args:
            check_interval: Seconds between checks for new events
        """
        self.check_interval = check_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the alert processor loop."""
        if self._running:
            logger.warning("Alert processor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Alert processor started")

    async def stop(self) -> None:
        """Stop the alert processor loop."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        logger.info("Alert processor stopped")

    async def _run_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                await self._process_pending_events()
            except Exception as e:
                logger.error(f"Error processing events: {e}")

            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

    async def _process_pending_events(self) -> None:
        """Process pending security events and send alerts."""
        async with async_session_maker() as session:
            engine = AlertEngine(session)

            try:
                # Process login analytics events
                await self._process_login_events(session, engine)

            finally:
                await engine.close()

    async def _process_login_events(
        self,
        session: AsyncSession,
        engine: AlertEngine,
    ) -> None:
        """Process login events and send alerts.

        Args:
            session: Database session
            engine: Alert engine
        """

        # Look for recent login events with anomalies (last 5 minutes)
        datetime.utcnow() - timedelta(minutes=5)

        # This is a placeholder - in production, you'd query for unprocessed events
        # For now, we rely on real-time processing via the API
        pass

    async def process_login_analytics(
        self,
        login_data: LoginAnalyticsModel,
        user_history: UserLoginHistoryModel | None = None,
    ) -> list[dict[str, Any]]:
        """Process a login analytics record and send alerts if needed.

        This is called when a new login is analyzed.

        Args:
            login_data: Login analytics data
            user_history: User's login history

        Returns:
            List of alert results
        """
        results = []

        async with async_session_maker() as session:
            engine = AlertEngine(session)

            try:
                # Process each anomaly flag
                for flag in login_data.anomaly_flags or []:
                    event_type = self._map_anomaly_to_event_type(flag)
                    if not event_type:
                        continue

                    # Determine severity based on risk score
                    severity = self._risk_score_to_severity(login_data.risk_score)

                    # Build alert content
                    title, description = self._build_alert_content(
                        event_type=event_type,
                        login_data=login_data,
                    )

                    # Build metadata
                    metadata = self._build_metadata(
                        login_data=login_data,
                        user_history=user_history,
                    )

                    # Process the event
                    result = await engine.process_event(
                        event_type=event_type,
                        severity=severity,
                        title=title,
                        description=description,
                        user_email=login_data.user_email,
                        tenant_id=login_data.tenant_id,
                        metadata=metadata,
                    )

                    results.extend(result)

            finally:
                await engine.close()

        return results

    def _map_anomaly_to_event_type(self, anomaly_flag: str) -> EventType | None:
        """Map an anomaly flag to an event type.

        Args:
            anomaly_flag: Anomaly flag string

        Returns:
            Event type or None
        """
        mapping = {
            "impossible_travel": EventType.IMPOSSIBLE_TRAVEL,
            "new_country": EventType.NEW_COUNTRY,
            "new_ip": EventType.NEW_IP,
            "multiple_failures": EventType.MULTIPLE_FAILURES,
            "failed_login": EventType.BRUTE_FORCE,
            "suspicious_location": EventType.SUSPICIOUS_LOCATION,
        }
        return mapping.get(anomaly_flag)

    def _risk_score_to_severity(self, risk_score: int) -> SeverityLevel:
        """Convert risk score to severity level.

        Args:
            risk_score: Risk score (0-100)

        Returns:
            Severity level
        """
        if risk_score >= 80:
            return SeverityLevel.CRITICAL
        elif risk_score >= 60:
            return SeverityLevel.HIGH
        elif risk_score >= 30:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def _build_alert_content(
        self,
        event_type: EventType,
        login_data: LoginAnalyticsModel,
    ) -> tuple[str, str]:
        """Build alert title and description.

        Args:
            event_type: Type of event
            login_data: Login data

        Returns:
            Tuple of (title, description)
        """
        user = login_data.user_email

        if event_type == EventType.IMPOSSIBLE_TRAVEL:
            title = "Impossible Travel Detected"
            description = f"User {user} logged in from physically impossible locations."

        elif event_type == EventType.NEW_COUNTRY:
            country = login_data.country or login_data.country_code or "Unknown"
            title = "New Country Login"
            description = f"User {user} logged in from {country} for the first time."

        elif event_type == EventType.NEW_IP:
            title = "New IP Address"
            description = f"User {user} logged in from a new IP address: {login_data.ip_address}"

        elif event_type == EventType.MULTIPLE_FAILURES:
            title = "Multiple Failed Login Attempts"
            description = f"User {user} has multiple failed login attempts in the last 24 hours."

        elif event_type == EventType.BRUTE_FORCE:
            title = "Failed Login Attempt"
            description = f"Failed login attempt for user {user}."

        elif event_type == EventType.SUSPICIOUS_LOCATION:
            title = "Suspicious Location"
            description = f"User {user} logged in from a suspicious location."

        elif event_type == EventType.ADMIN_ACTION:
            title = "Admin Action Detected"
            description = f"Administrative action detected for user {user}."

        else:
            title = "Security Alert"
            description = f"Security event detected for user {user}."

        return title, description

    def _build_metadata(
        self,
        login_data: LoginAnalyticsModel,
        user_history: UserLoginHistoryModel | None,
    ) -> dict[str, Any]:
        """Build metadata for alert.

        Args:
            login_data: Login data
            user_history: User history

        Returns:
            Metadata dictionary
        """
        metadata: dict[str, Any] = {
            "ip_address": login_data.ip_address,
            "country_code": login_data.country_code,
            "country": login_data.country,
            "city": login_data.city,
            "region": login_data.region,
            "risk_score": login_data.risk_score,
            "login_time": login_data.login_time.isoformat() if login_data.login_time else None,
        }

        # Add location data
        if login_data.latitude and login_data.longitude:
            metadata["current_location"] = {
                "latitude": login_data.latitude,
                "longitude": login_data.longitude,
                "city": login_data.city,
                "country": login_data.country,
            }

        # Add user history data
        if user_history:
            metadata["known_countries"] = user_history.known_countries
            metadata["known_ips_count"] = len(user_history.known_ips)
            metadata["failed_attempts_24h"] = user_history.failed_attempts_24h

            # Add previous location if available
            if user_history.last_latitude and user_history.last_longitude:
                metadata["previous_location"] = {
                    "latitude": user_history.last_latitude,
                    "longitude": user_history.last_longitude,
                    "city": None,  # Not stored in history
                    "country": user_history.last_login_country,
                }

        return metadata


# Global alert processor instance
alert_processor = AlertProcessor()
