"""Unit tests for MFA report service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.mfa_report import (
    ComplianceStatus,
    MFAComplianceAlertModel,
    MFAEnrollmentHistoryModel,
    MFAStrengthLevel,
    MFAUserModel,
)
from src.services.mfa_report import MFAReportService


class TestMFAReportService:
    """Test cases for MFAReportService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create an MFAReportService instance."""
        return MFAReportService(mock_db_session)

    @pytest.fixture
    def sample_tenant(self):
        """Return a sample tenant."""
        tenant = MagicMock()
        tenant.id = str(uuid4())
        tenant.tenant_id = "ms-tenant-123"
        tenant.name = "Test Tenant"
        tenant.client_id = "client-123"
        tenant.client_secret = "encrypted-secret"
        return tenant

    @pytest.fixture
    def sample_user_data(self):
        """Return sample user MFA data."""
        return {
            "user_id": "user-123",
            "user_principal_name": "john.doe@example.com",
            "display_name": "John Doe",
            "is_mfa_registered": True,
            "mfa_methods": ["microsoftAuthenticator"],
            "primary_method": "microsoftAuthenticator",
            "strength": "moderate",
            "is_admin": False,
            "admin_roles": [],
            "account_enabled": True,
            "user_type": "Member",
            "sign_in_activity": datetime.utcnow(),
            "raw_user_data": {},
        }

    @pytest.fixture
    def sample_admin_user_data(self):
        """Return sample admin user MFA data."""
        return {
            "user_id": "admin-123",
            "user_principal_name": "admin@example.com",
            "display_name": "Admin User",
            "is_mfa_registered": True,
            "mfa_methods": ["fido2"],
            "primary_method": "fido2",
            "strength": "strong",
            "is_admin": True,
            "admin_roles": ["Global Administrator"],
            "account_enabled": True,
            "user_type": "Member",
            "sign_in_activity": datetime.utcnow(),
            "raw_user_data": {},
        }

    def test_service_initialization(self, mock_db_session):
        """Test service initialization."""
        service = MFAReportService(mock_db_session)
        assert service.db == mock_db_session

    def test_compliance_thresholds(self, service):
        """Test compliance thresholds are set."""
        assert service.ADMIN_MFA_REQUIRED is True
        assert service.USER_MFA_TARGET_PERCENTAGE == 95.0

    def test_strength_priority(self, service):
        """Test MFA strength priority ordering."""
        assert service.STRENGTH_PRIORITY[MFAStrengthLevel.STRONG] == 3
        assert service.STRENGTH_PRIORITY[MFAStrengthLevel.MODERATE] == 2
        assert service.STRENGTH_PRIORITY[MFAStrengthLevel.WEAK] == 1
        assert service.STRENGTH_PRIORITY[MFAStrengthLevel.NONE] == 0

    @pytest.mark.asyncio
    async def test_scan_tenant_mfa_tenant_not_found(self, service):
        """Test scan with non-existent tenant."""
        with patch.object(service, "_get_tenant", return_value=None):
            with pytest.raises(ValueError, match="Tenant.*not found"):
                await service.scan_tenant_mfa("nonexistent-tenant-id")

    @pytest.mark.asyncio
    async def test_process_user_mfa_data_create_new(self, service, sample_user_data):
        """Test creating new user MFA data."""
        tenant_id = "tenant-123"

        with patch.object(service, "_get_existing_user", return_value=None):
            with patch.object(service, "_create_user_mfa_data") as mock_create:
                mock_create.return_value = MagicMock(spec=MFAUserModel)

                result = await service._process_user_mfa_data(tenant_id, sample_user_data)

                mock_create.assert_called_once()
                assert result["is_new_registration"] is False
                assert result["is_critical_finding"] is False

    @pytest.mark.asyncio
    async def test_process_user_mfa_data_update_existing(self, service, sample_user_data):
        """Test updating existing user MFA data."""
        tenant_id = "tenant-123"
        existing_user = MagicMock(spec=MFAUserModel)
        existing_user.is_mfa_registered = False
        existing_user.compliance_exempt = False

        with patch.object(service, "_get_existing_user", return_value=existing_user):
            with patch.object(service, "_update_user_mfa_data") as mock_update:
                with patch.object(service, "_create_compliance_alert", return_value=None):
                    result = await service._process_user_mfa_data(tenant_id, sample_user_data)

                    mock_update.assert_called_once()
                    assert result["is_new_registration"] is True  # User newly registered MFA

    @pytest.mark.asyncio
    async def test_process_user_mfa_data_admin_without_mfa(self, service):
        """Test processing admin user without MFA (critical finding)."""
        tenant_id = "tenant-123"
        admin_data = {
            "user_id": "admin-123",
            "user_principal_name": "admin@example.com",
            "display_name": "Admin User",
            "is_mfa_registered": False,
            "mfa_methods": [],
            "primary_method": None,
            "strength": "none",
            "is_admin": True,
            "admin_roles": ["Global Administrator"],
            "account_enabled": True,
            "raw_user_data": {},
        }

        with patch.object(service, "_get_existing_user", return_value=None):
            with patch.object(service, "_create_user_mfa_data", return_value=MagicMock(id=uuid4())):
                with patch.object(service, "_create_compliance_alert", return_value=None):
                    result = await service._process_user_mfa_data(tenant_id, admin_data)

                    assert result["is_critical_finding"] is True

    @pytest.mark.asyncio
    async def test_create_user_mfa_data(self, service, mock_db_session, sample_user_data):
        """Test creating new user MFA record."""
        tenant_id = "tenant-123"

        result = await service._create_user_mfa_data(
            tenant_id=tenant_id,
            user_data=sample_user_data,
            mfa_strength=MFAStrengthLevel.MODERATE,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        assert result.is_mfa_registered is True
        assert result.mfa_strength == MFAStrengthLevel.MODERATE

    @pytest.mark.asyncio
    async def test_update_user_mfa_data(self, service, mock_db_session):
        """Test updating existing user MFA record."""
        user = MagicMock(spec=MFAUserModel)
        user.is_mfa_registered = False

        user_data = {
            "display_name": "Updated Name",
            "is_mfa_registered": True,
            "mfa_methods": ["microsoftAuthenticator"],
            "primary_method": "microsoftAuthenticator",
            "is_admin": False,
            "admin_roles": [],
            "account_enabled": True,
            "user_type": "Member",
            "sign_in_activity": datetime.utcnow(),
            "raw_user_data": {},
        }

        await service._update_user_mfa_data(
            user=user,
            user_data=user_data,
            mfa_strength=MFAStrengthLevel.MODERATE,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        assert user.display_name == "Updated Name"
        assert user.is_mfa_registered is True
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_tenant_compliance(self, service, mock_db_session):
        """Test tenant compliance check."""
        tenant_id = "tenant-123"

        # Create mock non-compliant users
        user1 = MagicMock(spec=MFAUserModel)
        user1.is_admin = True
        user2 = MagicMock(spec=MFAUserModel)
        user2.is_admin = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [user1, user2]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service._check_tenant_compliance(tenant_id)

        assert result["total_violations"] == 2
        assert result["admin_violations"] == 1
        assert result["user_violations"] == 1

    @pytest.mark.asyncio
    async def test_create_compliance_alert_new(self, service, mock_db_session):
        """Test creating new compliance alert."""
        tenant_id = "tenant-123"
        user_id = uuid4()

        # Mock no existing alert
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        await service._create_compliance_alert(
            tenant_id=tenant_id,
            user_id=user_id,
            alert_type="admin_no_mfa",
            severity="critical",
            title="Test Alert",
            description="Test Description",
        )

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_compliance_alert_duplicate(self, service, mock_db_session):
        """Test that duplicate alerts are not created."""
        tenant_id = "tenant-123"
        user_id = uuid4()

        # Mock existing alert
        existing_alert = MagicMock(spec=MFAComplianceAlertModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_alert
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service._create_compliance_alert(
            tenant_id=tenant_id,
            user_id=user_id,
            alert_type="admin_no_mfa",
            severity="critical",
            title="Test Alert",
            description="Test Description",
        )

        # Should return None when alert already exists
        assert result is None

    @pytest.mark.asyncio
    async def test_get_users_with_filters(self, service, mock_db_session):
        """Test getting users with filters."""
        # Create mock users
        user1 = MagicMock(spec=MFAUserModel)
        user1.is_admin = True
        user2 = MagicMock(spec=MFAUserModel)
        user2.is_admin = False

        # Mock for count query
        count_mock = MagicMock()
        count_mock.scalar.return_value = 2

        # Mock for data query
        data_mock = MagicMock()
        data_mock.scalars.return_value.all.return_value = [user1, user2]

        # Use side_effect to return different results for different calls
        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return count_mock  # First call is count
            return data_mock  # Second call is data

        mock_db_session.execute = mock_execute

        result = await service.get_users(
            tenant_id="tenant-123",
            is_mfa_registered=True,
            is_admin=None,
            limit=100,
        )

        assert result["total"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_users_without_mfa(self, service, mock_db_session):
        """Test getting users without MFA."""
        user1 = MagicMock(spec=MFAUserModel)
        user1.is_admin = True
        user2 = MagicMock(spec=MFAUserModel)
        user2.is_admin = False

        # Mock for count query
        count_mock = MagicMock()
        count_mock.scalar.return_value = 2

        # Mock for data query
        data_mock = MagicMock()
        data_mock.scalars.return_value.all.return_value = [user1, user2]

        # Use side_effect to return different results for different calls
        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return count_mock  # First call is count
            return data_mock  # Second call is data

        mock_db_session.execute = mock_execute

        result = await service.get_users_without_mfa(
            tenant_id="tenant-123",
            include_exempt=False,
            limit=100,
        )

        assert result["total"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_admins_without_mfa(self, service, mock_db_session):
        """Test getting admins without MFA."""
        admin1 = MagicMock(spec=MFAUserModel)
        admin1.is_admin = True
        admin1.is_mfa_registered = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin1]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_admins_without_mfa(tenant_id="tenant-123")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_enrollment_summary(self, service, mock_db_session):
        """Test getting enrollment summary."""
        tenant_id = "tenant-123"

        # Mock count queries
        count_results = [100, 85, 10, 9, 50, 35, 0, 5]  # Various counts

        async def mock_execute(query):
            mock_result = MagicMock()
            mock_result.scalar.return_value = count_results.pop(0) if count_results else 0
            return mock_result

        mock_db_session.execute = mock_execute

        result = await service.get_enrollment_summary(tenant_id)

        assert result["tenant_id"] == tenant_id
        assert result["total_users"] == 100
        assert result["mfa_registered_users"] == 85
        assert result["admins_without_mfa"] == 1  # 10 total admins - 9 with MFA

    @pytest.mark.asyncio
    async def test_get_enrollment_trends(self, service, mock_db_session):
        """Test getting enrollment trends."""
        tenant_id = "tenant-123"

        # Create mock history entries
        history1 = MagicMock(spec=MFAEnrollmentHistoryModel)
        history1.snapshot_date = datetime.utcnow() - timedelta(days=1)
        history1.total_users = 100
        history1.mfa_registered_users = 80
        history1.mfa_coverage_percentage = 80.0
        history1.admin_mfa_coverage_percentage = 90.0

        history2 = MagicMock(spec=MFAEnrollmentHistoryModel)
        history2.snapshot_date = datetime.utcnow()
        history2.total_users = 100
        history2.mfa_registered_users = 85
        history2.mfa_coverage_percentage = 85.0
        history2.admin_mfa_coverage_percentage = 95.0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [history1, history2]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_enrollment_trends(tenant_id, days=30)

        assert result["tenant_id"] == tenant_id
        assert len(result["trends"]) == 2
        assert result["period_days"] == 30

    @pytest.mark.asyncio
    async def test_get_mfa_method_distribution(self, service, mock_db_session):
        """Test getting MFA method distribution."""
        tenant_id = "tenant-123"

        # Create mock users with different methods
        user1 = MagicMock(spec=MFAUserModel)
        user1.mfa_methods = ["microsoftAuthenticator"]
        user2 = MagicMock(spec=MFAUserModel)
        user2.mfa_methods = ["fido2"]
        user3 = MagicMock(spec=MFAUserModel)
        user3.mfa_methods = ["microsoftAuthenticator", "sms"]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [user1, user2, user3]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_mfa_method_distribution(tenant_id)

        assert result["tenant_id"] == tenant_id
        assert result["total_mfa_users"] == 3
        # microsoftAuthenticator should have highest count (2 users)
        assert result["distribution"][0]["method_type"] == "microsoftAuthenticator"

    @pytest.mark.asyncio
    async def test_get_mfa_strength_distribution(self, service, mock_db_session):
        """Test getting MFA strength distribution."""
        tenant_id = "tenant-123"

        # Mock count queries for each strength level
        count_sequence = [100, 20, 50, 25]  # total, strong, moderate, weak

        async def mock_execute(query):
            mock_result = MagicMock()
            mock_result.scalar.return_value = count_sequence.pop(0) if count_sequence else 0
            return mock_result

        mock_db_session.execute = mock_execute

        result = await service.get_mfa_strength_distribution(tenant_id)

        assert result["tenant_id"] == tenant_id
        # 100 total, 20 strong, 50 moderate, 25 weak = 5 none
        assert result["strong_mfa_percentage"] == 20.0
        assert result["moderate_mfa_percentage"] == 50.0
        assert result["weak_mfa_percentage"] == 25.0
        assert result["no_mfa_percentage"] == 5.0

    @pytest.mark.asyncio
    async def test_set_user_exemption_grant(self, service, mock_db_session):
        """Test granting MFA exemption."""
        user_id = str(uuid4())
        user = MagicMock(spec=MFAUserModel)
        user.id = user_id
        user.compliance_exempt = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.set_user_exemption(
            user_id=user_id,
            exempt=True,
            reason="Service account",
            expires_at=None,
        )

        assert result.compliance_exempt is True
        assert result.exemption_reason == "Service account"
        assert result.compliance_status == ComplianceStatus.EXEMPT

    @pytest.mark.asyncio
    async def test_set_user_exemption_revoke(self, service, mock_db_session):
        """Test revoking MFA exemption."""
        user_id = str(uuid4())
        user = MagicMock(spec=MFAUserModel)
        user.id = user_id
        user.compliance_exempt = True
        user.exemption_reason = "Old reason"
        user.is_mfa_registered = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.set_user_exemption(
            user_id=user_id,
            exempt=False,
        )

        assert result.compliance_exempt is False
        assert result.exemption_reason is None
        assert result.compliance_status == ComplianceStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_set_user_exemption_not_found(self, service, mock_db_session):
        """Test exemption for non-existent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.set_user_exemption(
            user_id="nonexistent-id",
            exempt=True,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_alert(self, service, mock_db_session):
        """Test resolving a compliance alert."""
        alert_id = str(uuid4())
        alert = MagicMock(spec=MFAComplianceAlertModel)
        alert.id = alert_id
        alert.is_resolved = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.resolve_alert(
            alert_id=alert_id,
            resolved_by="admin@example.com",
        )

        assert result.is_resolved is True
        assert result.resolved_by == "admin@example.com"

    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(self, service, mock_db_session):
        """Test resolving non-existent alert."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.resolve_alert(
            alert_id="nonexistent-id",
            resolved_by="admin@example.com",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_alerts(self, service, mock_db_session):
        """Test getting MFA compliance alerts."""
        alert1 = MagicMock(spec=MFAComplianceAlertModel)
        alert1.id = uuid4()
        alert2 = MagicMock(spec=MFAComplianceAlertModel)
        alert2.id = uuid4()

        # Mock for count query
        count_mock = MagicMock()
        count_mock.scalar.return_value = 2

        # Mock for data query
        data_mock = MagicMock()
        data_mock.scalars.return_value.all.return_value = [alert1, alert2]

        # Use side_effect to return different results for different calls
        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return count_mock  # First call is count
            return data_mock  # Second call is data

        mock_db_session.execute = mock_execute

        result = await service.get_alerts(
            tenant_id="tenant-123",
            resolved=False,
            severity="critical",
            limit=100,
        )

        assert result["total"] == 2
        assert len(result["items"]) == 2
