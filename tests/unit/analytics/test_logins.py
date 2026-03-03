"""Unit tests for the login analytics service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.anomalies import AnomalyType
from src.analytics.geo_ip import GeoLocation
from src.analytics.logins import LoginAnalyticsService
from src.models.analytics import AnomalyDetectionConfig, LoginAnalyticsModel, UserLoginHistoryModel


class TestLoginAnalyticsService:
    """Tests for LoginAnalyticsService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_geo_client(self):
        """Create a mock Geo-IP client."""
        client = AsyncMock()
        client.lookup.return_value = GeoLocation(
            ip_address="8.8.8.8",
            country="United States",
            country_code="US",
            city="Mountain View",
            region="California",
            latitude=37.386,
            longitude=-122.0838,
            lookup_success=True
        )
        return client

    @pytest.fixture
    def service(self, mock_db, mock_geo_client):
        """Create a LoginAnalyticsService with mocks."""
        return LoginAnalyticsService(
            db=mock_db,
            geo_ip_client=mock_geo_client
        )

    @pytest.mark.asyncio
    async def test_process_login_event_success(self, service, mock_db, mock_geo_client):
        """Test processing a successful login event."""
        # Setup mock for user history query (no existing history)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        login_time = datetime.utcnow()

        result = await service.process_login_event(
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="8.8.8.8",
            login_time=login_time,
            is_success=True
        )

        # Verify Geo-IP lookup was called
        mock_geo_client.lookup.assert_called_once_with("8.8.8.8")

        # Verify record was added
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

        # Verify record properties
        assert result.user_email == "user@example.com"
        assert result.tenant_id == "tenant-123"
        assert result.ip_address == "8.8.8.8"
        assert result.country == "United States"
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_process_login_event_with_failure(self, service, mock_db, mock_geo_client):
        """Test processing a failed login event."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        login_time = datetime.utcnow()

        result = await service.process_login_event(
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="8.8.8.8",
            login_time=login_time,
            is_success=False,
            failure_reason="Invalid password"
        )

        assert result.is_success is False
        assert result.failure_reason == "Invalid password"
        # Should have failure anomaly flag
        assert AnomalyType.FAILED_LOGIN.value in result.anomaly_flags

    @pytest.mark.asyncio
    async def test_query_logins_with_filters(self, service, mock_db):
        """Test querying logins with filters."""
        # Create mock login records
        mock_logins = [
            LoginAnalyticsModel(
                id=uuid4(),
                user_email="user1@example.com",
                tenant_id="tenant-123",
                ip_address="1.1.1.1",
                country_code="US",
                login_time=datetime.utcnow(),
                is_success=True,
                anomaly_flags=[],
                risk_score=0
            ),
            LoginAnalyticsModel(
                id=uuid4(),
                user_email="user2@example.com",
                tenant_id="tenant-123",
                ip_address="2.2.2.2",
                country_code="JP",
                login_time=datetime.utcnow(),
                is_success=False,
                anomaly_flags=[AnomalyType.FAILED_LOGIN.value],
                risk_score=20
            )
        ]

        # Mock execute to return logins
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logins
        mock_result.scalar.return_value = len(mock_logins)
        mock_db.execute.return_value = mock_result

        logins, total = await service.query_logins(
            tenant_id="tenant-123",
            is_success=True,
            limit=10
        )

        assert len(logins) == 2
        assert total == 2
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_user_login_summary_with_history(self, service, mock_db):
        """Test getting user login summary with existing history."""
        # Create user history
        history = UserLoginHistoryModel(
            user_email="user@example.com",
            tenant_id="tenant-123",
            known_countries=["US", "JP"],
            known_ips=["1.1.1.1", "2.2.2.2"],
            last_login_time=datetime.utcnow(),
            last_login_country="US",
            last_latitude=40.7128,
            last_longitude=-74.0060,
            total_logins=10,
            failed_attempts_24h=2
        )

        # Mock execute results
        def mock_execute(query):
            result = MagicMock()
            if "user_login_history" in str(query).lower():
                result.scalar_one_or_none.return_value = history
            else:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute.side_effect = mock_execute

        summary = await service.get_user_login_summary(
            user_email="user@example.com",
            tenant_id="tenant-123"
        )

        assert summary["user_email"] == "user@example.com"
        assert summary["total_logins"] == 10
        assert summary["known_countries"] == ["US", "JP"]
        assert summary["known_ips_count"] == 2
        assert summary["failed_attempts_24h"] == 2

    @pytest.mark.asyncio
    async def test_get_user_login_summary_no_history(self, service, mock_db):
        """Test getting user login summary without existing history."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        summary = await service.get_user_login_summary(
            user_email="newuser@example.com",
            tenant_id="tenant-123"
        )

        assert summary["user_email"] == "newuser@example.com"
        assert summary["total_logins"] == 0
        assert summary["known_countries"] == []
        assert summary["known_ips_count"] == 0

    @pytest.mark.asyncio
    async def test_get_or_create_user_history_new_user(self, service, mock_db):
        """Test creating user history for new user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        history = await service._get_or_create_user_history(
            "newuser@example.com",
            "tenant-123"
        )

        assert history.user_email == "newuser@example.com"
        assert history.tenant_id == "tenant-123"
        assert history.known_countries == []
        assert history.known_ips == []
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_history_existing_user(self, service, mock_db):
        """Test retrieving existing user history."""
        existing_history = UserLoginHistoryModel(
            user_email="existing@example.com",
            tenant_id="tenant-123",
            known_countries=["US"],
            known_ips=["1.1.1.1"],
            total_logins=5
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_history
        mock_db.execute.return_value = mock_result

        history = await service._get_or_create_user_history(
            "existing@example.com",
            "tenant-123"
        )

        assert history.user_email == "existing@example.com"
        assert history.total_logins == 5
        assert "US" in history.known_countries


class TestAnomalyDetectionIntegration:
    """Tests for anomaly detection in service context - simplified."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        return LoginAnalyticsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_geo_ip_called_during_processing(self, service, mock_db):
        """Test that Geo-IP lookup is called during login processing."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock Geo-IP
        service.geo_ip.lookup = AsyncMock(return_value=GeoLocation(
            ip_address="8.8.8.8",
            country="United States",
            country_code="US",
            city="Mountain View",
            latitude=37.386,
            longitude=-122.0838,
            lookup_success=True
        ))

        result = await service.process_login_event(
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="8.8.8.8",
            login_time=datetime.utcnow(),
            is_success=True
        )

        # Verify Geo-IP was called
        service.geo_ip.lookup.assert_called_once_with("8.8.8.8")
        assert result.country_code == "US"
        assert result.city == "Mountain View"


class TestAnomalyConfig:
    """Tests for anomaly detection configuration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        return LoginAnalyticsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_anomaly_config_exists(self, service, mock_db):
        """Test retrieving existing anomaly config."""
        config = AnomalyDetectionConfig(
            tenant_id="tenant-123",
            enabled=True,
            auto_add_known_countries=True,
            impossible_travel_speed_kmh=900
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_db.execute.return_value = mock_result

        result = await service._get_anomaly_config("tenant-123")

        assert result is not None
        assert result.tenant_id == "tenant-123"
        assert result.enabled is True
        assert result.impossible_travel_speed_kmh == 900

    @pytest.mark.asyncio
    async def test_get_anomaly_config_not_exists(self, service, mock_db):
        """Test retrieving non-existent anomaly config."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service._get_anomaly_config("tenant-123")

        assert result is None


class TestProcessAuditLogSignins:
    """Tests for processing audit log signins."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        return LoginAnalyticsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_process_audit_logs_empty(self, service, mock_db):
        """Test processing when no audit logs exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await service.process_audit_log_signins("tenant-123", limit=10)

        assert count == 0

    @pytest.mark.asyncio
    async def test_skip_invalid_audit_logs(self, service, mock_db):
        """Test skipping audit logs with missing data."""
        from src.models.audit_log import AuditLogModel, LogType

        # Create audit log missing required fields
        audit_log = AuditLogModel(
            id=uuid4(),
            tenant_id="tenant-123",
            log_type=LogType.SIGNIN,
            raw_data={
                # Missing UserId and ClientIP
                "CreationTime": "2024-01-01T12:00:00Z"
            },
            processed=False
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit_log]
        mock_db.execute.return_value = mock_result

        await service.process_audit_log_signins("tenant-123")

        # Should skip the invalid log but mark as processed
        assert audit_log.processed is True


class TestLoginAnalyticsEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        svc = LoginAnalyticsService(db=mock_db)
        # Properly mock the geo_ip client
        svc.geo_ip = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_geo_ip_failure_handling(self, service, mock_db):
        """Test handling of Geo-IP lookup failure."""
        # Mock Geo-IP to return failed lookup
        service.geo_ip.lookup.return_value = GeoLocation(
            ip_address="8.8.8.8",
            lookup_success=False,
            error_message="API error"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.process_login_event(
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="8.8.8.8",
            login_time=datetime.utcnow(),
            is_success=True
        )

        # Should still create record even if Geo-IP fails
        assert result.user_email == "user@example.com"
        assert result.country is None

    @pytest.mark.asyncio
    async def test_missing_coordinates_handling(self, service, mock_db):
        """Test handling when coordinates are missing."""
        service.geo_ip.lookup.return_value = GeoLocation(
            ip_address="8.8.8.8",
            country="US",
            country_code="US",
            lookup_success=True
            # No latitude/longitude
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.process_login_event(
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="8.8.8.8",
            login_time=datetime.utcnow(),
            is_success=True
        )

        # Should not have impossible travel anomaly without coordinates
        assert AnomalyType.IMPOSSIBLE_TRAVEL.value not in result.anomaly_flags


class TestUpdateUserHistory:
    """Tests for _update_user_history method."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        return LoginAnalyticsService(db=mock_db)

    @pytest.fixture
    def user_history(self):
        """Create a sample user history."""
        return UserLoginHistoryModel(
            user_email="user@example.com",
            tenant_id="tenant-123",
            known_countries=["US"],
            known_ips=["192.168.1.1"],
            total_logins=5,
            failed_attempts_24h=0
        )

    @pytest.fixture
    def login_record(self):
        """Create a sample login record."""
        return LoginAnalyticsModel(
            id=uuid4(),
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="192.168.1.2",
            country="Canada",
            country_code="CA",
            city="Toronto",
            latitude=43.6532,
            longitude=-79.3832,
            login_time=datetime.utcnow(),
            is_success=True
        )

    @pytest.mark.asyncio
    async def test_update_user_history_failed_login(self, service, mock_db, user_history, login_record):
        """Test that failed login increments failure counter."""
        login_record.is_success = False
        login_record.failure_reason = "Invalid password"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        anomaly_results = [
            MagicMock(type=AnomalyType.FAILED_LOGIN, detected=True),
            MagicMock(type=AnomalyType.NEW_COUNTRY, detected=False)
        ]

        await service._update_user_history(user_history, login_record, anomaly_results)

        assert user_history.failed_attempts_24h == 1
        assert user_history.total_logins == 5  # Should not increment on failure

    @pytest.mark.asyncio
    async def test_update_user_history_successful_login_resets_failures(self, service, mock_db, user_history, login_record):
        """Test that successful login resets failure counter."""
        user_history.failed_attempts_24h = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        anomaly_results = [
            MagicMock(type=AnomalyType.NEW_COUNTRY, detected=False),
            MagicMock(type=AnomalyType.NEW_IP, detected=True)
        ]

        await service._update_user_history(user_history, login_record, anomaly_results)

        assert user_history.failed_attempts_24h == 0  # Should reset on success
        assert user_history.total_logins == 6  # Should increment on success

    @pytest.mark.asyncio
    async def test_update_user_history_new_country_auto_add(self, service, mock_db, user_history, login_record):
        """Test auto-adding new country when config allows."""
        config = AnomalyDetectionConfig(
            tenant_id="tenant-123",
            auto_add_known_countries=True
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_db.execute.return_value = mock_result

        anomaly_results = [
            MagicMock(type=AnomalyType.NEW_COUNTRY, detected=True)
        ]

        await service._update_user_history(user_history, login_record, anomaly_results)

        assert "CA" in user_history.known_countries
        assert "US" in user_history.known_countries

    @pytest.mark.asyncio
    async def test_update_user_history_new_country_no_auto_add(self, service, mock_db, user_history, login_record):
        """Test not adding new country when config disables auto-add."""
        config = AnomalyDetectionConfig(
            tenant_id="tenant-123",
            auto_add_known_countries=False
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_db.execute.return_value = mock_result

        anomaly_results = [
            MagicMock(type=AnomalyType.NEW_COUNTRY, detected=True)
        ]

        await service._update_user_history(user_history, login_record, anomaly_results)

        # CA should NOT be added when auto_add is False
        assert "CA" not in user_history.known_countries
        assert "US" in user_history.known_countries

    @pytest.mark.asyncio
    async def test_update_user_history_known_country_added_if_missing(self, service, mock_db, user_history, login_record):
        """Test that known country is added to list if somehow missing."""
        login_record.country_code = "US"  # Already known country
        user_history.known_countries = []  # But list is empty (data inconsistency)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        anomaly_results = [
            MagicMock(type=AnomalyType.NEW_COUNTRY, detected=False)
        ]

        await service._update_user_history(user_history, login_record, anomaly_results)

        assert "US" in user_history.known_countries

    @pytest.mark.asyncio
    async def test_update_user_history_new_ip_added(self, service, mock_db, user_history, login_record):
        """Test that new IP is added to known IPs list."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        anomaly_results = []

        await service._update_user_history(user_history, login_record, anomaly_results)

        assert "192.168.1.2" in user_history.known_ips
        assert "192.168.1.1" in user_history.known_ips

    @pytest.mark.asyncio
    async def test_update_user_history_no_config(self, service, mock_db, user_history, login_record):
        """Test behavior when no anomaly config exists (defaults to auto-add)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No config
        mock_db.execute.return_value = mock_result

        anomaly_results = [
            MagicMock(type=AnomalyType.NEW_COUNTRY, detected=True)
        ]

        await service._update_user_history(user_history, login_record, anomaly_results)

        # Should still add country when config is None (default behavior)
        assert "CA" in user_history.known_countries


class TestQueryLoginsExtended:
    """Extended tests for query_logins with all filter combinations."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        return LoginAnalyticsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_query_with_user_email_filter(self, service, mock_db):
        """Test filtering by user_email."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(user_email="user@example.com")

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_time_range_filters(self, service, mock_db):
        """Test filtering by start_time and end_time."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        await service.query_logins(start_time=start, end_time=end)

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_ip_filter(self, service, mock_db):
        """Test filtering by IP address."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(ip_address="192.168.1.1")

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_country_filters(self, service, mock_db):
        """Test filtering by country and country_code."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(country="United States", country_code="US")

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_has_anomaly_true(self, service, mock_db):
        """Test filtering for records with anomalies."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(has_anomaly=True)

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_has_anomaly_false(self, service, mock_db):
        """Test filtering for records without anomalies."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(has_anomaly=False)

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_anomaly_type_filter(self, service, mock_db):
        """Test filtering by specific anomaly type."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(anomaly_type="impossible_travel")

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_min_risk_score(self, service, mock_db):
        """Test filtering by minimum risk score."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        await service.query_logins(min_risk_score=50)

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, service, mock_db):
        """Test pagination with limit and offset."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 100
        mock_db.execute.return_value = mock_result

        logins, total = await service.query_logins(limit=10, offset=20)

        assert total == 100
        mock_db.execute.assert_called()


class TestGetPreviousLogin:
    """Tests for _get_previous_login method."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        return LoginAnalyticsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_previous_login_exists(self, service, mock_db):
        """Test retrieving previous successful login."""
        previous_login = LoginAnalyticsModel(
            id=uuid4(),
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="192.168.1.1",
            country_code="US",
            city="New York",
            latitude=40.7128,
            longitude=-74.0060,
            login_time=datetime.utcnow() - timedelta(hours=1),
            is_success=True
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = previous_login
        mock_db.execute.return_value = mock_result

        result = await service._get_previous_login("user@example.com", "tenant-123")

        assert result is not None
        assert result.user_email == "user@example.com"
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_get_previous_login_none(self, service, mock_db):
        """Test when no previous login exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service._get_previous_login("user@example.com", "tenant-123")

        assert result is None


class TestProcessAuditLogExtended:
    """Extended tests for process_audit_log_signins."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService with mocked geo_ip."""
        svc = LoginAnalyticsService(db=mock_db)
        svc.geo_ip = AsyncMock(return_value=GeoLocation(
            ip_address="8.8.8.8",
            country="US",
            country_code="US",
            lookup_success=True
        ))
        return svc

    @pytest.mark.asyncio
    async def test_process_successful_audit_log(self, service, mock_db):
        """Test processing a successful signin audit log."""
        from src.models.audit_log import AuditLogModel, LogType

        audit_log = AuditLogModel(
            id=uuid4(),
            tenant_id="tenant-123",
            log_type=LogType.SIGNIN,
            raw_data={
                "UserId": "user@example.com",
                "ClientIP": "8.8.8.8",
                "CreationTime": "2024-01-01T12:00:00Z",
                "Status": {"ErrorCode": 0}
            },
            processed=False,
            o365_created_at=datetime.utcnow()
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit_log]
        mock_db.execute.return_value = mock_result

        await service.process_audit_log_signins("tenant-123")

        assert audit_log.processed is True

    @pytest.mark.asyncio
    async def test_process_failed_audit_log(self, service, mock_db):
        """Test processing a failed signin audit log."""
        from src.models.audit_log import AuditLogModel, LogType

        audit_log = AuditLogModel(
            id=uuid4(),
            tenant_id="tenant-123",
            log_type=LogType.SIGNIN,
            raw_data={
                "UserPrincipalName": "user@example.com",
                "IpAddress": "8.8.8.8",
                "CreatedDateTime": "2024-01-01T12:00:00Z",
                "Status": {
                    "ErrorCode": 50126,
                    "FailureReason": "Invalid username or password"
                }
            },
            processed=False,
            o365_created_at=datetime.utcnow()
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit_log]
        mock_db.execute.return_value = mock_result

        await service.process_audit_log_signins("tenant-123")

        assert audit_log.processed is True

    @pytest.mark.asyncio
    async def test_process_audit_log_exception_handling(self, service, mock_db):
        """Test exception handling during audit log processing."""
        from src.models.audit_log import AuditLogModel, LogType

        audit_log = AuditLogModel(
            id=uuid4(),
            tenant_id="tenant-123",
            log_type=LogType.SIGNIN,
            raw_data={
                "UserId": "user@example.com",
                "ClientIP": "8.8.8.8",
                # Missing CreationTime - will cause exception
            },
            processed=False,
            o365_created_at=None,
            created_at=datetime.utcnow()
        )

        # Make geo_ip.lookup raise an exception
        service.geo_ip.lookup = AsyncMock(side_effect=Exception("Unexpected error"))

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit_log]
        mock_db.execute.return_value = mock_result

        # Should not raise exception
        await service.process_audit_log_signins("tenant-123")

        # Should mark as processed even on error
        assert audit_log.processed is True

    @pytest.mark.asyncio
    async def test_process_audit_log_with_alternative_fields(self, service, mock_db):
        """Test processing audit log with alternative field names."""
        from src.models.audit_log import AuditLogModel, LogType

        audit_log = AuditLogModel(
            id=uuid4(),
            tenant_id="tenant-123",
            log_type=LogType.SIGNIN,
            raw_data={
                "UserPrincipalName": "user@example.com",  # Alternative to UserId
                "IpAddress": "8.8.8.8",  # Alternative to ClientIP
                "CreationTime": "2024-01-01T12:00:00Z"
            },
            processed=False,
            o365_created_at=datetime.utcnow()
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit_log]
        mock_db.execute.return_value = mock_result

        await service.process_audit_log_signins("tenant-123")

        assert audit_log.processed is True


class TestAnomaliesWithPreviousLogin:
    """Tests for anomaly detection with previous login context."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a LoginAnalyticsService."""
        svc = LoginAnalyticsService(db=mock_db)
        svc.geo_ip = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_process_login_with_previous_for_travel_analysis(self, service, mock_db):
        """Test that previous login is used for impossible travel detection."""
        # First mock call returns None (no history), second returns previous login
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = MagicMock()

            if "user_login_history" in str(query).lower():
                result.scalar_one_or_none.return_value = None
            elif call_count == 0:
                # First call for previous login
                previous = LoginAnalyticsModel(
                    id=uuid4(),
                    user_email="user@example.com",
                    tenant_id="tenant-123",
                    ip_address="192.168.1.1",
                    country_code="US",
                    city="New York",
                    latitude=40.7128,
                    longitude=-74.0060,
                    login_time=datetime.utcnow() - timedelta(hours=2),
                    is_success=True
                )
                result.scalar_one_or_none.return_value = previous
                call_count += 1
            else:
                result.scalar_one_or_none.return_value = None

            return result

        mock_db.execute.side_effect = mock_execute

        # Current login from Tokyo
        service.geo_ip.lookup.return_value = GeoLocation(
            ip_address="1.1.1.1",
            country="Japan",
            country_code="JP",
            city="Tokyo",
            latitude=35.6762,
            longitude=139.6503,
            lookup_success=True
        )

        result = await service.process_login_event(
            user_email="user@example.com",
            tenant_id="tenant-123",
            ip_address="1.1.1.1",
            login_time=datetime.utcnow(),
            is_success=True
        )

        # Should detect impossible travel
        assert AnomalyType.IMPOSSIBLE_TRAVEL.value in result.anomaly_flags


class TestLoginAnalyticsInit:
    """Tests for LoginAnalyticsService initialization."""

    @pytest.mark.asyncio
    async def test_service_init_with_defaults(self):
        """Test service initialization with default clients."""
        mock_db = AsyncMock(spec=AsyncSession)

        with patch('src.analytics.logins.get_geo_ip_client') as mock_geo:
            mock_geo.return_value = AsyncMock()
            service = LoginAnalyticsService(db=mock_db)

            assert service.db is mock_db
            assert service.geo_ip is not None
            assert service.detector is not None

    @pytest.mark.asyncio
    async def test_service_init_with_custom_clients(self):
        """Test service initialization with custom clients."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_geo = AsyncMock()
        mock_detector = MagicMock()

        service = LoginAnalyticsService(
            db=mock_db,
            geo_ip_client=mock_geo,
            anomaly_detector=mock_detector
        )

        assert service.db is mock_db
        assert service.geo_ip is mock_geo
        assert service.detector is mock_detector
