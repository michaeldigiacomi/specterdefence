"""Unit tests for MFA report API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

# Import endpoint functions with aliases to avoid pytest collection issues
import src.api.mfa_report as mfa_report_api
from src.models.mfa_report import (
    ComplianceStatus,
    MFAStrengthLevel,
)
from src.services.mfa_report import MFAReportService


class TestMFAReportAPI:
    """Test cases for MFA report API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock MFA report service."""
        service = AsyncMock(spec=MFAReportService)
        return service

    @pytest.fixture
    def sample_summary(self):
        """Return sample enrollment summary."""
        return {
            "tenant_id": "tenant-123",
            "snapshot_date": datetime.utcnow(),
            "total_users": 100,
            "mfa_registered_users": 85,
            "non_compliant_users": 10,
            "total_admins": 10,
            "admins_with_mfa": 10,
            "admins_without_mfa": 0,
            "fido2_users": 15,
            "authenticator_app_users": 60,
            "sms_users": 10,
            "voice_users": 0,
            "strong_mfa_users": 15,
            "moderate_mfa_users": 60,
            "weak_mfa_users": 10,
            "exempt_users": 5,
            "mfa_coverage_percentage": 85.0,
            "admin_mfa_coverage_percentage": 100.0,
            "compliance_rate": 90.0,
            "meets_admin_requirement": True,
            "meets_user_target": False,
        }

    @pytest.fixture
    def sample_user(self):
        """Return a sample MFA user."""
        user = MagicMock()
        user.id = uuid4()
        user.tenant_id = "tenant-123"
        user.user_id = "ms-user-123"
        user.user_principal_name = "john.doe@example.com"
        user.display_name = "John Doe"
        user.is_mfa_registered = True
        user.mfa_methods = ["microsoftAuthenticator"]
        user.primary_mfa_method = "microsoftAuthenticator"
        user.mfa_strength = MFAStrengthLevel.MODERATE
        user.is_admin = False
        user.admin_roles = []
        user.compliance_status = ComplianceStatus.COMPLIANT
        user.compliance_exempt = False
        user.exemption_reason = None
        user.first_mfa_registration = datetime.utcnow()
        user.last_mfa_update = datetime.utcnow()
        user.account_enabled = True
        user.user_type = "Member"
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.needs_attention = False
        return user

    @pytest.fixture
    def sample_non_compliant_user(self):
        """Return a sample non-compliant user."""
        user = MagicMock()
        user.id = uuid4()
        user.tenant_id = "tenant-123"
        user.user_id = "ms-user-456"
        user.user_principal_name = "user@example.com"
        user.display_name = "Regular User"
        user.is_mfa_registered = False
        user.mfa_methods = []
        user.primary_mfa_method = None
        user.mfa_strength = MFAStrengthLevel.NONE
        user.is_admin = False
        user.admin_roles = []
        user.compliance_status = ComplianceStatus.NON_COMPLIANT
        user.compliance_exempt = False
        user.exemption_reason = None
        user.first_mfa_registration = None
        user.last_mfa_update = None
        user.account_enabled = True
        user.user_type = "Member"
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.needs_attention = True
        return user

    @pytest.mark.asyncio
    async def test_get_mfa_summary(self, mock_service, sample_summary):
        """Test getting MFA enrollment summary."""
        mock_service.get_enrollment_summary.return_value = sample_summary

        result = await mfa_report_api.get_mfa_summary(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.tenant_id == "tenant-123"
        assert result.total_users == 100
        assert result.mfa_coverage_percentage == 85.0
        assert result.meets_admin_requirement is True
        assert result.meets_user_target is False
        mock_service.get_enrollment_summary.assert_called_once_with(tenant_id="tenant-123")

    @pytest.mark.asyncio
    async def test_list_mfa_users(self, mock_service, sample_user):
        """Test listing MFA users."""
        mock_service.get_users.return_value = {
            "items": [sample_user],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await mfa_report_api.list_mfa_users(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].user_principal_name == "john.doe@example.com"
        assert result.items[0].is_mfa_registered is True

    @pytest.mark.asyncio
    async def test_list_mfa_users_with_filters(self, mock_service, sample_user):
        """Test listing MFA users with filters."""
        mock_service.get_users.return_value = {
            "items": [sample_user],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await mfa_report_api.list_mfa_users(
            tenant_id="tenant-123",
            is_mfa_registered=True,
            is_admin=False,
            service=mock_service
        )

        assert result.total == 1
        mock_service.get_users.assert_called_once()
        call_kwargs = mock_service.get_users.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant-123"
        assert call_kwargs["is_mfa_registered"] is True
        assert call_kwargs["is_admin"] is False

    @pytest.mark.asyncio
    async def test_get_users_without_mfa(self, mock_service, sample_non_compliant_user):
        """Test getting users without MFA."""
        mock_service.get_users_without_mfa.return_value = {
            "items": [sample_non_compliant_user],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await mfa_report_api.get_users_without_mfa(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].is_mfa_registered is False
        assert result.critical_count == 0  # Not an admin

    @pytest.mark.asyncio
    async def test_get_users_without_mfa_with_admin(self, mock_service, sample_non_compliant_user):
        """Test getting users without MFA including admin."""
        sample_non_compliant_user.is_admin = True
        mock_service.get_users_without_mfa.return_value = {
            "items": [sample_non_compliant_user],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await mfa_report_api.get_users_without_mfa(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.total == 1
        assert result.critical_count == 1  # Admin without MFA

    @pytest.mark.asyncio
    async def test_get_admins_without_mfa_empty(self, mock_service):
        """Test getting admins without MFA when none exist."""
        mock_service.get_admins_without_mfa.return_value = []

        result = await mfa_report_api.get_admins_without_mfa(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.total == 0
        assert "All admins have MFA" in result.message

    @pytest.mark.asyncio
    async def test_get_admins_without_mfa_with_findings(self, mock_service):
        """Test getting admins without MFA when findings exist."""
        admin_user = MagicMock()
        admin_user.id = uuid4()
        admin_user.user_principal_name = "admin@example.com"
        admin_user.display_name = "Admin User"
        admin_user.is_mfa_registered = False
        admin_user.is_admin = True
        admin_user.compliance_status = ComplianceStatus.NON_COMPLIANT
        admin_user.compliance_exempt = False
        admin_user.exemption_reason = None
        admin_user.first_mfa_registration = None
        admin_user.last_mfa_update = None
        admin_user.account_enabled = True
        admin_user.user_type = "Member"
        admin_user.created_at = datetime.utcnow()
        admin_user.updated_at = datetime.utcnow()
        admin_user.needs_attention = True
        admin_user.tenant_id = "tenant-123"
        admin_user.user_id = "ms-admin-123"
        admin_user.mfa_methods = []
        admin_user.primary_mfa_method = None
        admin_user.mfa_strength = MFAStrengthLevel.NONE
        admin_user.admin_roles = ["Global Administrator"]

        mock_service.get_admins_without_mfa.return_value = [admin_user]

        result = await mfa_report_api.get_admins_without_mfa(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.total == 1
        assert "CRITICAL" in result.message
        assert "Immediate action required" in result.message

    @pytest.mark.asyncio
    async def test_get_mfa_trends(self, mock_service):
        """Test getting MFA enrollment trends."""
        now = datetime.utcnow()
        mock_service.get_enrollment_trends.return_value = {
            "tenant_id": "tenant-123",
            "trends": [
                {
                    "date": now - timedelta(days=7),
                    "total_users": 100,
                    "mfa_registered_users": 80,
                    "mfa_coverage_percentage": 80.0,
                    "admin_mfa_coverage_percentage": 90.0,
                },
                {
                    "date": now,
                    "total_users": 100,
                    "mfa_registered_users": 85,
                    "mfa_coverage_percentage": 85.0,
                    "admin_mfa_coverage_percentage": 100.0,
                },
            ],
            "period_days": 30,
        }

        result = await mfa_report_api.get_mfa_trends(
            tenant_id="tenant-123",
            days=30,
            service=mock_service
        )

        assert result.tenant_id == "tenant-123"
        assert len(result.trends) == 2
        assert result.period_days == 30

    @pytest.mark.asyncio
    async def test_get_method_distribution(self, mock_service):
        """Test getting MFA method distribution."""
        mock_service.get_mfa_method_distribution.return_value = {
            "tenant_id": "tenant-123",
            "total_mfa_users": 85,
            "distribution": [
                {"method_type": "microsoftAuthenticator", "count": 60, "percentage": 70.59},
                {"method_type": "fido2", "count": 15, "percentage": 17.65},
                {"method_type": "sms", "count": 10, "percentage": 11.76},
            ],
        }

        result = await mfa_report_api.get_method_distribution(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.tenant_id == "tenant-123"
        assert result.total_mfa_users == 85
        assert len(result.distribution) == 3
        assert result.distribution[0].method_type == "microsoftAuthenticator"

    @pytest.mark.asyncio
    async def test_get_strength_distribution(self, mock_service):
        """Test getting MFA strength distribution."""
        mock_service.get_mfa_strength_distribution.return_value = {
            "tenant_id": "tenant-123",
            "distribution": [
                {"strength_level": "strong", "count": 15, "percentage": 15.0},
                {"strength_level": "moderate", "count": 60, "percentage": 60.0},
                {"strength_level": "weak", "count": 10, "percentage": 10.0},
                {"strength_level": "none", "count": 15, "percentage": 15.0},
            ],
            "strong_mfa_percentage": 15.0,
            "moderate_mfa_percentage": 60.0,
            "weak_mfa_percentage": 10.0,
            "no_mfa_percentage": 15.0,
        }

        result = await mfa_report_api.get_strength_distribution(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.tenant_id == "tenant-123"
        assert result.strong_mfa_percentage == 15.0
        assert result.moderate_mfa_percentage == 60.0
        assert result.weak_mfa_percentage == 10.0
        assert result.no_mfa_percentage == 15.0

    @pytest.mark.asyncio
    async def test_get_compliance_report(self, mock_service, sample_summary, sample_non_compliant_user):
        """Test getting full compliance report."""
        mock_service.get_enrollment_summary.return_value = sample_summary
        mock_service.get_users_without_mfa.return_value = {
            "items": [sample_non_compliant_user],
            "total": 1,
        }
        mock_service.get_admins_without_mfa.return_value = []
        mock_service.get_users.return_value = {
            "items": [],
            "total": 0,
        }

        result = await mfa_report_api.get_compliance_report(
            tenant_id="tenant-123",
            service=mock_service
        )

        assert result.tenant_id == "tenant-123"
        assert result.summary.tenant_id == "tenant-123"
        assert len(result.non_compliant_users) == 1
        assert len(result.admins_without_mfa) == 0
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_scan_mfa(self, mock_service):
        """Test triggering MFA scan."""
        mock_service.scan_tenant_mfa.return_value = {
            "success": True,
            "users_scanned": 100,
            "new_mfa_registrations": 5,
            "compliance_violations": 10,
            "critical_findings": 0,
            "message": "Scan completed successfully.",
        }

        from src.models.mfa_report import MFAScanRequest
        request = MFAScanRequest(
            tenant_id="tenant-123",
            full_scan=True,
            check_compliance=True,
        )

        result = await mfa_report_api.scan_mfa(
            request=request,
            service=mock_service
        )

        assert result.success is True
        assert result.users_scanned == 100
        assert result.new_mfa_registrations == 5

    @pytest.mark.asyncio
    async def test_scan_mfa_tenant_not_found(self, mock_service):
        """Test triggering MFA scan with non-existent tenant."""
        mock_service.scan_tenant_mfa.side_effect = ValueError("Tenant not found")

        from src.models.mfa_report import MFAScanRequest
        request = MFAScanRequest(
            tenant_id="nonexistent-tenant",
            full_scan=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await mfa_report_api.scan_mfa(
                request=request,
                service=mock_service
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_set_user_exemption_grant(self, mock_service):
        """Test granting MFA exemption."""
        user_id = str(uuid4())

        # Create mock user with exemption granted
        user = MagicMock()
        user.id = user_id
        user.compliance_exempt = True
        user.exemption_reason = "Service account"
        user.exemption_expires_at = None
        user.compliance_status = ComplianceStatus.EXEMPT

        mock_service.set_user_exemption.return_value = user

        from src.models.mfa_report import MFAExemptionRequest
        request = MFAExemptionRequest(
            exemption_reason="Service account",
        )

        result = await mfa_report_api.set_user_exemption(
            user_id=user_id,
            request=request,
            service=mock_service
        )

        assert result.success is True
        assert result.exemption_granted is True
        assert result.exemption_reason == "Service account"

    @pytest.mark.asyncio
    async def test_set_user_exemption_not_found(self, mock_service):
        """Test exemption for non-existent user."""
        mock_service.set_user_exemption.return_value = None

        from src.models.mfa_report import MFAExemptionRequest
        request = MFAExemptionRequest(
            exemption_reason="Test",
        )

        with pytest.raises(HTTPException) as exc_info:
            await mfa_report_api.set_user_exemption(
                user_id="nonexistent-id",
                request=request,
                service=mock_service
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_mfa_alerts(self, mock_service):
        """Test listing MFA alerts."""
        alert = MagicMock()
        alert.id = uuid4()
        alert.user_id = uuid4()
        alert.tenant_id = "tenant-123"
        alert.alert_type = "admin_no_mfa"
        alert.severity = "critical"
        alert.title = "Admin without MFA"
        alert.description = "Critical security finding"
        alert.is_resolved = False
        alert.resolved_at = None
        alert.resolved_by = None
        alert.created_at = datetime.utcnow()

        mock_service.get_alerts.return_value = {
            "items": [alert],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await mfa_report_api.list_mfa_alerts(
            tenant_id="tenant-123",
            resolved=False,
            service=mock_service
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["severity"] == "critical"
        assert result["items"][0]["is_resolved"] is False

    @pytest.mark.asyncio
    async def test_resolve_alert(self, mock_service):
        """Test resolving an MFA alert."""
        alert_id = str(uuid4())

        # Create mock resolved alert
        alert = MagicMock()
        alert.id = alert_id
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = "admin@example.com"

        mock_service.resolve_alert.return_value = alert

        from src.models.mfa_report import MFAResolveAlertRequest
        request = MFAResolveAlertRequest(
            resolved_by="admin@example.com",
        )

        result = await mfa_report_api.resolve_alert(
            alert_id=alert_id,
            request=request,
            service=mock_service
        )

        assert result.success is True
        assert result.is_resolved is True
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(self, mock_service):
        """Test resolving non-existent alert."""
        mock_service.resolve_alert.return_value = None

        from src.models.mfa_report import MFAResolveAlertRequest
        request = MFAResolveAlertRequest(
            resolved_by="admin@example.com",
        )

        with pytest.raises(HTTPException) as exc_info:
            await mfa_report_api.resolve_alert(
                alert_id="nonexistent-id",
                request=request,
                service=mock_service
            )

        assert exc_info.value.status_code == 404
