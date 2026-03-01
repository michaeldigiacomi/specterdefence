"""Unit tests for the login analytics service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.logins import LoginAnalyticsService
from src.analytics.geo_ip import GeoLocation
from src.analytics.anomalies import AnomalyType
from src.models.analytics import LoginAnalyticsModel, UserLoginHistoryModel, AnomalyDetectionConfig


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
        
        count = await service.process_audit_log_signins("tenant-123")
        
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
