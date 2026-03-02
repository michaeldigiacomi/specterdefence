"""Unit tests for MFA report API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.mfa_report import router
from src.models.mfa_report import (
    ComplianceStatus,
    MFAComplianceAlertModel,
    MFAStrengthLevel,
    MFAUserModel,
)

# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/mfa-report")
client = TestClient(app)


class TestMFAReportAPI:
    """Test cases for MFA report API endpoints."""

    @pytest.fixture
    def sample_user(self):
        """Return a sample MFA user."""
        user = MagicMock(spec=MFAUserModel)
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
        return user

    @pytest.fixture
    def sample_admin_user(self):
        """Return a sample admin MFA user."""
        user = MagicMock(spec=MFAUserModel)
        user.id = uuid4()
        user.tenant_id = "tenant-123"
        user.user_id = "ms-admin-123"
        user.user_principal_name = "admin@example.com"
        user.display_name = "Admin User"
        user.is_mfa_registered = True
        user.mfa_methods = ["fido2"]
        user.primary_mfa_method = "fido2"
        user.mfa_strength = MFAStrengthLevel.STRONG
        user.is_admin = True
        user.admin_roles = ["Global Administrator"]
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
        user = MagicMock(spec=MFAUserModel)
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

    def test_get_mfa_summary(self, sample_summary):
        """Test getting MFA enrollment summary."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_enrollment_summary = AsyncMock(return_value=sample_summary)
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert data["total_users"] == 100
        assert data["mfa_coverage_percentage"] == 85.0
        assert data["meets_admin_requirement"] is True
        assert data["meets_user_target"] is False

    def test_list_mfa_users(self, sample_user):
        """Test listing MFA users."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_users = AsyncMock(return_value={
                "items": [sample_user],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/users?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["user_principal_name"] == "john.doe@example.com"
        assert data["items"][0]["is_mfa_registered"] is True

    def test_list_mfa_users_with_filters(self, sample_user):
        """Test listing MFA users with filters."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_users = AsyncMock(return_value={
                "items": [sample_user],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get(
                "/api/v1/mfa-report/users?tenant_id=tenant-123&is_mfa_registered=true&is_admin=false"
            )

        assert response.status_code == 200
        mock_instance.get_users.assert_called_once()
        call_kwargs = mock_instance.get_users.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant-123"
        assert call_kwargs["is_mfa_registered"] is True
        assert call_kwargs["is_admin"] is False

    def test_list_mfa_users_invalid_strength(self):
        """Test listing MFA users with invalid strength filter."""
        response = client.get(
            "/api/v1/mfa-report/users?tenant_id=tenant-123&mfa_strength=invalid"
        )

        assert response.status_code == 400
        assert "Invalid MFA strength" in response.json()["detail"]

    def test_get_users_without_mfa(self, sample_non_compliant_user):
        """Test getting users without MFA."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_users_without_mfa = AsyncMock(return_value={
                "items": [sample_non_compliant_user],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/users-without-mfa?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["is_mfa_registered"] is False
        assert data["critical_count"] == 0  # Not an admin

    def test_get_users_without_mfa_with_admin(self, sample_non_compliant_user):
        """Test getting users without MFA including admin."""
        sample_non_compliant_user.is_admin = True

        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_users_without_mfa = AsyncMock(return_value={
                "items": [sample_non_compliant_user],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/users-without-mfa?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["critical_count"] == 1  # Admin without MFA

    def test_get_admins_without_mfa_empty(self):
        """Test getting admins without MFA when none exist."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_admins_without_mfa = AsyncMock(return_value=[])
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/admins-without-mfa?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert "All admins have MFA" in data["message"]

    def test_get_admins_without_mfa_with_findings(self):
        """Test getting admins without MFA when findings exist."""
        admin_user = MagicMock(spec=MFAUserModel)
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

        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_admins_without_mfa = AsyncMock(return_value=[admin_user])
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/admins-without-mfa?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "CRITICAL" in data["message"]
        assert "Immediate action required" in data["message"]

    def test_get_mfa_trends(self):
        """Test getting MFA enrollment trends."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_enrollment_trends = AsyncMock(return_value={
                "tenant_id": "tenant-123",
                "trends": [
                    {
                        "date": datetime.utcnow() - timedelta(days=7),
                        "total_users": 100,
                        "mfa_registered_users": 80,
                        "mfa_coverage_percentage": 80.0,
                        "admin_mfa_coverage_percentage": 90.0,
                    },
                    {
                        "date": datetime.utcnow(),
                        "total_users": 100,
                        "mfa_registered_users": 85,
                        "mfa_coverage_percentage": 85.0,
                        "admin_mfa_coverage_percentage": 100.0,
                    },
                ],
                "period_days": 30,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/trends?tenant_id=tenant-123&days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert len(data["trends"]) == 2
        assert data["period_days"] == 30

    def test_get_method_distribution(self):
        """Test getting MFA method distribution."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_mfa_method_distribution = AsyncMock(return_value={
                "tenant_id": "tenant-123",
                "total_mfa_users": 85,
                "distribution": [
                    {"method_type": "microsoftAuthenticator", "count": 60, "percentage": 70.59},
                    {"method_type": "fido2", "count": 15, "percentage": 17.65},
                    {"method_type": "sms", "count": 10, "percentage": 11.76},
                ],
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/method-distribution?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert data["total_mfa_users"] == 85
        assert len(data["distribution"]) == 3
        assert data["distribution"][0]["method_type"] == "microsoftAuthenticator"

    def test_get_strength_distribution(self):
        """Test getting MFA strength distribution."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_mfa_strength_distribution = AsyncMock(return_value={
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
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/strength-distribution?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert data["strong_mfa_percentage"] == 15.0
        assert data["moderate_mfa_percentage"] == 60.0
        assert data["weak_mfa_percentage"] == 10.0
        assert data["no_mfa_percentage"] == 15.0

    def test_get_compliance_report(self, sample_summary):
        """Test getting full compliance report."""
        non_compliant_user = MagicMock(spec=MFAUserModel)
        non_compliant_user.id = uuid4()
        non_compliant_user.user_principal_name = "user@example.com"
        non_compliant_user.is_mfa_registered = False
        non_compliant_user.is_admin = False
        non_compliant_user.mfa_strength = MFAStrengthLevel.NONE
        non_compliant_user.compliance_status = ComplianceStatus.NON_COMPLIANT
        non_compliant_user.compliance_exempt = False
        non_compliant_user.exemption_reason = None
        non_compliant_user.first_mfa_registration = None
        non_compliant_user.last_mfa_update = None
        non_compliant_user.account_enabled = True
        non_compliant_user.user_type = "Member"
        non_compliant_user.created_at = datetime.utcnow()
        non_compliant_user.updated_at = datetime.utcnow()
        non_compliant_user.needs_attention = True

        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_enrollment_summary = AsyncMock(return_value=sample_summary)
            mock_instance.get_users_without_mfa = AsyncMock(return_value={
                "items": [non_compliant_user],
                "total": 1,
            })
            mock_instance.get_admins_without_mfa = AsyncMock(return_value=[])
            mock_instance.get_users = AsyncMock(return_value={
                "items": [],
                "total": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/compliance-report?tenant_id=tenant-123")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert "summary" in data
        assert "non_compliant_users" in data
        assert "admins_without_mfa" in data
        assert "recommendations" in data

    def test_scan_mfa(self):
        """Test triggering MFA scan."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.scan_tenant_mfa = AsyncMock(return_value={
                "success": True,
                "users_scanned": 100,
                "new_mfa_registrations": 5,
                "compliance_violations": 10,
                "critical_findings": 0,
                "message": "Scan completed successfully.",
            })
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/mfa-report/scan",
                json={
                    "tenant_id": "tenant-123",
                    "full_scan": True,
                    "check_compliance": True,
                }
            )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["users_scanned"] == 100
        assert data["new_mfa_registrations"] == 5

    def test_scan_mfa_tenant_not_found(self):
        """Test triggering MFA scan with non-existent tenant."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.scan_tenant_mfa = AsyncMock(side_effect=ValueError("Tenant not found"))
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/mfa-report/scan",
                json={
                    "tenant_id": "nonexistent-tenant",
                    "full_scan": True,
                }
            )

        assert response.status_code == 404

    def test_set_user_exemption_grant(self):
        """Test granting MFA exemption."""
        user_id = str(uuid4())

        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()

            # Create mock user with exemption granted
            user = MagicMock(spec=MFAUserModel)
            user.id = user_id
            user.compliance_exempt = True
            user.exemption_reason = "Service account"
            user.exemption_expires_at = None
            user.compliance_status = ComplianceStatus.EXEMPT

            mock_instance.set_user_exemption = AsyncMock(return_value=user)
            mock_service.return_value = mock_instance

            response = client.post(
                f"/api/v1/mfa-report/users/{user_id}/exemption",
                json={
                    "exemption_reason": "Service account",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["exemption_granted"] is True
        assert data["exemption_reason"] == "Service account"

    def test_set_user_exemption_not_found(self):
        """Test exemption for non-existent user."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.set_user_exemption = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/mfa-report/users/nonexistent-id/exemption",
                json={"exemption_reason": "Test"},
            )

        assert response.status_code == 404

    def test_list_mfa_alerts(self):
        """Test listing MFA alerts."""
        alert = MagicMock(spec=MFAComplianceAlertModel)
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

        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_alerts = AsyncMock(return_value={
                "items": [alert],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/mfa-report/alerts?tenant_id=tenant-123&resolved=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["severity"] == "critical"
        assert data["items"][0]["is_resolved"] is False

    def test_resolve_alert(self):
        """Test resolving an MFA alert."""
        alert_id = str(uuid4())

        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()

            # Create mock resolved alert
            alert = MagicMock(spec=MFAComplianceAlertModel)
            alert.id = alert_id
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = "admin@example.com"

            mock_instance.resolve_alert = AsyncMock(return_value=alert)
            mock_service.return_value = mock_instance

            response = client.post(
                f"/api/v1/mfa-report/alerts/{alert_id}/resolve",
                json={"resolved_by": "admin@example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_resolved"] is True
        assert data["resolved_at"] is not None

    def test_resolve_alert_not_found(self):
        """Test resolving non-existent alert."""
        with patch("src.api.mfa_report.get_mfa_report_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.resolve_alert = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/mfa-report/alerts/nonexistent-id/resolve",
                json={"resolved_by": "admin@example.com"},
            )

        assert response.status_code == 404
