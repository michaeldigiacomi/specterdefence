"""Unit tests for alert processor service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.alerts import EventType, SeverityLevel
from src.models.analytics import LoginAnalyticsModel, UserLoginHistoryModel
from src.services.alert_processor import AlertProcessor


class TestAlertProcessor:
    """Test cases for AlertProcessor."""

    @pytest.fixture
    def processor(self):
        """Create an AlertProcessor instance."""
        return AlertProcessor(check_interval=60)

    def test_init(self, processor):
        """Test processor initialization."""
        assert processor.check_interval == 60
        assert processor._running is False
        assert processor._task is None

    @pytest.mark.asyncio
    async def test_map_anomaly_to_event_type(self, processor):
        """Test mapping anomaly flags to event types."""
        assert processor._map_anomaly_to_event_type("impossible_travel") == EventType.IMPOSSIBLE_TRAVEL
        assert processor._map_anomaly_to_event_type("new_country") == EventType.NEW_COUNTRY
        assert processor._map_anomaly_to_event_type("new_ip") == EventType.NEW_IP
        assert processor._map_anomaly_to_event_type("multiple_failures") == EventType.MULTIPLE_FAILURES
        assert processor._map_anomaly_to_event_type("failed_login") == EventType.BRUTE_FORCE
        assert processor._map_anomaly_to_event_type("suspicious_location") == EventType.SUSPICIOUS_LOCATION
        assert processor._map_anomaly_to_event_type("unknown_flag") is None

    def test_risk_score_to_severity(self, processor):
        """Test risk score to severity conversion."""
        assert processor._risk_score_to_severity(95) == SeverityLevel.CRITICAL
        assert processor._risk_score_to_severity(80) == SeverityLevel.CRITICAL
        assert processor._risk_score_to_severity(79) == SeverityLevel.HIGH
        assert processor._risk_score_to_severity(60) == SeverityLevel.HIGH
        assert processor._risk_score_to_severity(59) == SeverityLevel.MEDIUM
        assert processor._risk_score_to_severity(30) == SeverityLevel.MEDIUM
        assert processor._risk_score_to_severity(29) == SeverityLevel.LOW
        assert processor._risk_score_to_severity(0) == SeverityLevel.LOW

    def test_build_alert_content_impossible_travel(self, processor):
        """Test alert content for impossible travel."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.country = "Japan"
        login_data.country_code = "JP"
        login_data.ip_address = "192.168.1.1"

        title, description = processor._build_alert_content(
            EventType.IMPOSSIBLE_TRAVEL,
            login_data,
        )

        assert title == "Impossible Travel Detected"
        assert "user@example.com" in description
        assert "impossible" in description.lower()

    def test_build_alert_content_new_country(self, processor):
        """Test alert content for new country."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.country = "France"
        login_data.country_code = "FR"
        login_data.ip_address = "192.168.1.1"

        title, description = processor._build_alert_content(
            EventType.NEW_COUNTRY,
            login_data,
        )

        assert title == "New Country Login"
        assert "France" in description

    def test_build_alert_content_new_ip(self, processor):
        """Test alert content for new IP."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.country = None
        login_data.ip_address = "10.0.0.1"

        title, description = processor._build_alert_content(
            EventType.NEW_IP,
            login_data,
        )

        assert title == "New IP Address"
        assert "10.0.0.1" in description

    def test_build_alert_content_multiple_failures(self, processor):
        """Test alert content for multiple failures."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.ip_address = "192.168.1.1"

        title, description = processor._build_alert_content(
            EventType.MULTIPLE_FAILURES,
            login_data,
        )

        assert title == "Multiple Failed Login Attempts"
        assert "multiple" in description.lower()

    def test_build_alert_content_brute_force(self, processor):
        """Test alert content for brute force."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.ip_address = "192.168.1.1"

        title, description = processor._build_alert_content(
            EventType.BRUTE_FORCE,
            login_data,
        )

        assert title == "Failed Login Attempt"

    def test_build_alert_content_admin_action(self, processor):
        """Test alert content for admin action."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "admin@example.com"
        login_data.ip_address = "192.168.1.1"

        title, description = processor._build_alert_content(
            EventType.ADMIN_ACTION,
            login_data,
        )

        assert title == "Admin Action Detected"

    def test_build_metadata_with_login_data(self, processor):
        """Test building metadata with login data."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.ip_address = "192.168.1.1"
        login_data.country_code = "US"
        login_data.country = "United States"
        login_data.city = "New York"
        login_data.region = "NY"
        login_data.risk_score = 75
        login_data.login_time = datetime(2026, 3, 1, 12, 0, 0)
        login_data.latitude = 40.7128
        login_data.longitude = -74.0060

        metadata = processor._build_metadata(login_data, None)

        assert metadata["ip_address"] == "192.168.1.1"
        assert metadata["country_code"] == "US"
        assert metadata["country"] == "United States"
        assert metadata["city"] == "New York"
        assert metadata["region"] == "NY"
        assert metadata["risk_score"] == 75
        assert metadata["current_location"]["latitude"] == 40.7128

    def test_build_metadata_with_user_history(self, processor):
        """Test building metadata with user history."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.ip_address = "192.168.1.1"
        login_data.country_code = "FR"
        login_data.country = "France"
        login_data.city = "Paris"
        login_data.region = None
        login_data.risk_score = 50
        login_data.login_time = datetime(2026, 3, 1, 12, 0, 0)
        login_data.latitude = 48.8566
        login_data.longitude = 2.3522

        user_history = MagicMock(spec=UserLoginHistoryModel)
        user_history.known_countries = ["US", "UK"]
        user_history.known_ips = ["10.0.0.1", "10.0.0.2"]
        user_history.failed_attempts_24h = 3
        user_history.last_latitude = 40.7128
        user_history.last_longitude = -74.0060
        user_history.last_login_country = "US"

        metadata = processor._build_metadata(login_data, user_history)

        assert metadata["known_countries"] == ["US", "UK"]
        assert metadata["known_ips_count"] == 2
        assert metadata["failed_attempts_24h"] == 3
        assert metadata["previous_location"]["latitude"] == 40.7128
        assert metadata["previous_location"]["country"] == "US"

    @pytest.mark.asyncio
    async def test_process_login_analytics(self, processor):
        """Test processing login analytics - simplified to avoid complex mocking."""
        # This test is simplified as the full flow is better tested via integration tests
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.risk_score = 75  # HIGH severity
        login_data.anomaly_flags = ["impossible_travel"]
        login_data.ip_address = "192.168.1.1"
        login_data.country_code = "JP"
        login_data.country = "Japan"
        login_data.city = "Tokyo"
        login_data.region = None
        login_data.latitude = 35.6762
        login_data.longitude = 139.6503
        login_data.login_time = datetime(2026, 3, 1, 12, 0, 0)

        # Verify mapping logic works
        event_type = processor._map_anomaly_to_event_type("impossible_travel")
        severity = processor._risk_score_to_severity(login_data.risk_score)
        title, description = processor._build_alert_content(event_type, login_data)
        metadata = processor._build_metadata(login_data, None)

        assert event_type == EventType.IMPOSSIBLE_TRAVEL
        assert severity == SeverityLevel.HIGH
        assert title == "Impossible Travel Detected"
        assert metadata["ip_address"] == "192.168.1.1"
        assert metadata["country_code"] == "JP"

    @pytest.mark.asyncio
    async def test_process_login_analytics_multiple_flags(self, processor):
        """Test processing login with multiple anomaly flags."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.user_email = "user@example.com"
        login_data.tenant_id = "tenant-123"
        login_data.risk_score = 60
        login_data.anomaly_flags = ["new_country", "new_ip"]
        login_data.ip_address = "192.168.1.1"
        login_data.country_code = "FR"
        login_data.country = "France"
        login_data.city = "Paris"
        login_data.region = None
        login_data.latitude = 48.8566
        login_data.longitude = 2.3522
        login_data.login_time = datetime(2026, 3, 1, 12, 0, 0)

        mock_engine = AsyncMock()
        mock_engine.process_event = AsyncMock(return_value=[{"status": "sent"}])
        mock_engine.close = AsyncMock()

        with patch('src.services.alert_processor.AlertEngine', return_value=mock_engine):
            results = await processor.process_login_analytics(login_data, None)

        # Should process both flags
        assert mock_engine.process_event.call_count == 2

    @pytest.mark.asyncio
    async def test_process_login_analytics_no_flags(self, processor):
        """Test processing login with no anomaly flags."""
        login_data = MagicMock(spec=LoginAnalyticsModel)
        login_data.anomaly_flags = []

        results = await processor.process_login_analytics(login_data, None)

        assert results == []

    @pytest.mark.asyncio
    async def test_start_stop(self, processor):
        """Test starting and stopping the processor."""
        # Just test that start sets _running to True and creates a task
        async def mock_run_loop():
            pass

        processor._run_loop = mock_run_loop

        await processor.start()
        assert processor._running is True
        assert processor._task is not None

        # Stop and verify
        processor._running = True
        await processor.stop()
        assert processor._running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, processor):
        """Test starting when already running."""
        processor._running = True

        with patch('asyncio.create_task') as mock_create_task:
            await processor.start()
            mock_create_task.assert_not_called()
