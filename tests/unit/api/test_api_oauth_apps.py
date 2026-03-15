"""Unit tests for OAuth apps API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.oauth_apps import (
    AcknowledgeAlertRequest,
    RevokeAppRequest,
    ScanRequest,
    acknowledge_alert,
    get_app_permissions,
    get_high_risk_apps,
    get_oauth_app,
    get_oauth_apps_summary,
    get_suspicious_apps,
    get_tenant_oauth_apps,
    list_oauth_app_alerts,
    list_oauth_apps,
    revoke_oauth_app,
    scan_oauth_apps,
)
from src.models.oauth_apps import (
    AppStatus,
    OAuthAppAlertModel,
    OAuthAppConsentModel,
    OAuthAppModel,
    OAuthAppPermissionModel,
    PublisherType,
    RiskLevel,
)


class TestOAuthAppsEndpoints:
    """Test cases for OAuth apps API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock OAuth apps service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def sample_app(self):
        """Return a sample OAuth app."""
        app = MagicMock(spec=OAuthAppModel)
        app.id = uuid4()
        app.tenant_id = str(uuid4())
        app.app_id = "app-123"
        app.display_name = "Test App"
        app.description = "A test application"
        app.publisher_name = "Test Publisher"
        app.publisher_id = None
        app.publisher_type = PublisherType.UNVERIFIED
        app.is_microsoft_publisher = False
        app.is_verified_publisher = False
        app.risk_level = RiskLevel.HIGH
        app.status = AppStatus.SUSPICIOUS
        app.risk_score = 35
        app.permission_count = 2
        app.high_risk_permissions = ["Mail.Read"]
        app.has_mail_permissions = True
        app.has_user_read_all = True
        app.has_group_read_all = False
        app.has_files_read_all = False
        app.has_calendar_access = False
        app.has_admin_consent = False
        app.consent_count = 1
        app.admin_consented = False
        app.is_new_app = True
        app.detection_reasons = ["High-risk permission: Mail.Read"]
        app.app_created_at = datetime.utcnow()
        app.first_seen_at = datetime.utcnow()
        app.last_scan_at = datetime.utcnow()
        app.created_at = datetime.utcnow()
        app.updated_at = datetime.utcnow()
        return app

    @pytest.fixture
    def sample_permission(self):
        """Return a sample permission."""
        perm = MagicMock(spec=OAuthAppPermissionModel)
        perm.id = uuid4()
        perm.permission_id = "perm-1"
        perm.permission_type = "Application"
        perm.permission_value = "Mail.Read"
        perm.display_name = "Read user mail"
        perm.description = "Allows reading user emails"
        perm.is_high_risk = True
        perm.risk_category = "mail"
        perm.is_admin_consent_required = True
        perm.consent_state = "Consented"
        perm.created_at = datetime.utcnow()
        perm.updated_at = datetime.utcnow()
        return perm

    @pytest.fixture
    def sample_consent(self):
        """Return a sample consent."""
        consent = MagicMock(spec=OAuthAppConsentModel)
        consent.id = uuid4()
        consent.user_id = "user-1"
        consent.user_email = "user@example.com"
        consent.user_display_name = "Test User"
        consent.consent_type = "Principal"
        consent.scope = "Mail.Read"
        consent.consent_state = "Consented"
        consent.consented_at = datetime.utcnow()
        consent.expires_at = None
        consent.created_at = datetime.utcnow()
        consent.updated_at = datetime.utcnow()
        return consent

    @pytest.fixture
    def sample_alert(self):
        """Return a sample OAuth app alert."""
        alert = MagicMock(spec=OAuthAppAlertModel)
        alert.id = uuid4()
        alert.app_id = uuid4()
        alert.tenant_id = str(uuid4())
        alert.alert_type = "oauth_high_risk_permissions"
        alert.severity = RiskLevel.HIGH
        alert.title = "Suspicious OAuth App Detected"
        alert.description = "Has access to user mailboxes"
        alert.is_acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        alert.created_at = datetime.utcnow()
        return alert

    @pytest.mark.asyncio
    async def test_list_oauth_apps_success(self, mock_service, sample_app):
        """Test successful listing of OAuth apps."""
        mock_service.get_apps.return_value = {
            "items": [sample_app],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await list_oauth_apps(
            tenant_id=None,
            status=None,
            risk_level=None,
            publisher_type=None,
            limit=100,
            offset=0,
            service=mock_service,
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].display_name == "Test App"
        mock_service.get_apps.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_oauth_apps_with_filters(self, mock_service, sample_app):
        """Test listing OAuth apps with filters."""
        mock_service.get_apps.return_value = {
            "items": [sample_app],
            "total": 1,
            "limit": 50,
            "offset": 10,
        }

        result = await list_oauth_apps(
            tenant_id="tenant-123",
            status="suspicious",
            risk_level="HIGH",
            publisher_type="unverified",
            limit=50,
            offset=10,
            service=mock_service,
        )

        assert result.limit == 50
        assert result.offset == 10
        mock_service.get_apps.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_oauth_apps_invalid_status(self, mock_service):
        """Test listing with invalid status filter."""
        with pytest.raises(HTTPException) as exc_info:
            await list_oauth_apps(
                tenant_id=None,
                status="invalid_status",
                risk_level=None,
                publisher_type=None,
                limit=100,
                offset=0,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid status" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_oauth_apps_invalid_risk_level(self, mock_service):
        """Test listing with invalid risk level filter."""
        with pytest.raises(HTTPException) as exc_info:
            await list_oauth_apps(
                tenant_id=None,
                status=None,
                risk_level="invalid",
                publisher_type=None,
                limit=100,
                offset=0,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid risk level" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_oauth_app_success(self, mock_service, sample_app):
        """Test getting a specific OAuth app."""
        mock_service.get_app_by_id.return_value = sample_app

        result = await get_oauth_app(
            app_id=str(sample_app.id),
            service=mock_service,
        )

        assert result.display_name == "Test App"
        assert result.id == str(sample_app.id)

    @pytest.mark.asyncio
    async def test_get_oauth_app_not_found(self, mock_service):
        """Test getting a non-existent OAuth app."""
        mock_service.get_app_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_oauth_app(
                app_id="non-existent",
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_app_permissions_success(
        self, mock_service, sample_app, sample_permission, sample_consent
    ):
        """Test getting app permissions."""
        mock_service.get_app_by_id.return_value = sample_app
        mock_service.get_app_permissions_detail.return_value = [sample_permission]
        mock_service.get_app_consents.return_value = [sample_consent]

        result = await get_app_permissions(
            app_id=str(sample_app.id),
            service=mock_service,
        )

        assert result.app.display_name == "Test App"
        assert len(result.permissions) == 1
        assert len(result.consents) == 1
        assert result.permissions[0].permission_value == "Mail.Read"

    @pytest.mark.asyncio
    async def test_get_app_permissions_not_found(self, mock_service):
        """Test getting permissions for non-existent app."""
        mock_service.get_app_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_app_permissions(
                app_id="non-existent",
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_oauth_app_success(self, mock_service):
        """Test successful OAuth app revocation."""
        mock_service.revoke_app.return_value = {
            "success": True,
            "message": "App disabled successfully",
        }

        request = RevokeAppRequest(revoke_type="disable")

        result = await revoke_oauth_app(
            app_id="app-123",
            request=request,
            service=mock_service,
        )

        assert result.success is True
        assert "disabled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_revoke_oauth_app_failure(self, mock_service):
        """Test failed OAuth app revocation."""
        mock_service.revoke_app.return_value = {"success": False, "error": "App not found"}

        request = RevokeAppRequest(revoke_type="disable")

        with pytest.raises(HTTPException) as exc_info:
            await revoke_oauth_app(
                app_id="app-123",
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_tenant_oauth_apps_success(self, mock_service, sample_app):
        """Test getting tenant OAuth apps."""
        mock_service.get_apps.return_value = {
            "items": [sample_app],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await get_tenant_oauth_apps(
            tenant_id="tenant-123",
            status=None,
            risk_level=None,
            limit=100,
            offset=0,
            service=mock_service,
        )

        assert result.total == 1
        mock_service.get_apps.assert_called_once_with(
            tenant_id="tenant-123", status=None, risk_level=None, limit=100, offset=0
        )

    @pytest.mark.asyncio
    async def test_get_suspicious_apps_success(self, mock_service, sample_app):
        """Test getting suspicious apps."""
        mock_service.get_suspicious_apps.return_value = [sample_app]

        result = await get_suspicious_apps(
            tenant_id="tenant-123",
            limit=100,
            service=mock_service,
        )

        assert len(result) == 1
        assert result[0].display_name == "Test App"

    @pytest.mark.asyncio
    async def test_get_high_risk_apps_success(self, mock_service, sample_app):
        """Test getting high-risk apps."""
        mock_service.get_high_risk_apps.return_value = [sample_app]

        result = await get_high_risk_apps(
            tenant_id="tenant-123",
            limit=100,
            service=mock_service,
        )

        assert len(result) == 1
        assert result[0].risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_get_oauth_apps_summary_success(self, mock_service):
        """Test getting OAuth apps summary."""
        mock_service.get_apps_summary.return_value = {
            "total_apps": 10,
            "by_risk_level": {"LOW": 5, "MEDIUM": 3, "HIGH": 2, "CRITICAL": 0},
            "by_status": {
                "approved": 5,
                "suspicious": 3,
                "malicious": 2,
                "revoked": 0,
                "pending_review": 0,
            },
            "mail_access_apps": 2,
            "unverified_publisher_apps": 3,
            "total_alerts": 5,
            "unacknowledged_alerts": 2,
        }

        result = await get_oauth_apps_summary(
            tenant_id="tenant-123",
            service=mock_service,
        )

        assert result.total_apps == 10
        assert result.mail_access_apps == 2
        assert result.unverified_publisher_apps == 3
        assert result.total_alerts == 5

    @pytest.mark.asyncio
    async def test_scan_oauth_apps_success(self, mock_service):
        """Test successful OAuth app scan."""
        mock_service.scan_tenant_oauth_apps.return_value = {
            "total_apps": 10,
            "new_apps": 5,
            "updated_apps": 3,
            "suspicious_apps": 2,
            "malicious_apps": 0,
            "alerts_triggered": 2,
        }

        request = ScanRequest(tenant_id="tenant-123", trigger_alerts=True)

        result = await scan_oauth_apps(
            request=request,
            service=mock_service,
        )

        assert result.success is True
        assert result.results["total_apps"] == 10
        assert result.results["suspicious_apps"] == 2

    @pytest.mark.asyncio
    async def test_scan_oauth_apps_missing_tenant(self, mock_service):
        """Test scan without tenant ID."""
        request = ScanRequest(tenant_id=None, trigger_alerts=True)

        with pytest.raises(HTTPException) as exc_info:
            await scan_oauth_apps(
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400
        assert "tenant_id is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_scan_oauth_apps_tenant_not_found(self, mock_service):
        """Test scan with non-existent tenant."""
        mock_service.scan_tenant_oauth_apps.side_effect = ValueError(
            "Tenant not-found-id not found"
        )

        request = ScanRequest(tenant_id="not-found-id", trigger_alerts=True)

        with pytest.raises(HTTPException) as exc_info:
            await scan_oauth_apps(
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_scan_oauth_apps_error(self, mock_service):
        """Test scan with unexpected error."""
        mock_service.scan_tenant_oauth_apps.side_effect = Exception("Database error")

        request = ScanRequest(tenant_id="tenant-123", trigger_alerts=True)

        with pytest.raises(HTTPException) as exc_info:
            await scan_oauth_apps(
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 500
        assert "Scan failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_oauth_app_alerts_success(self, mock_service, sample_alert):
        """Test listing OAuth app alerts."""
        mock_service.get_alerts.return_value = {
            "items": [sample_alert],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await list_oauth_app_alerts(
            tenant_id="tenant-123",
            acknowledged=False,
            severity=None,
            limit=100,
            offset=0,
            service=mock_service,
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].title == "Suspicious OAuth App Detected"

    @pytest.mark.asyncio
    async def test_list_oauth_app_alerts_invalid_severity(self, mock_service):
        """Test listing alerts with invalid severity."""
        with pytest.raises(HTTPException) as exc_info:
            await list_oauth_app_alerts(
                tenant_id=None,
                acknowledged=None,
                severity="INVALID",
                limit=100,
                offset=0,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, mock_service, sample_alert):
        """Test successfully acknowledging an alert."""
        sample_alert.is_acknowledged = True
        sample_alert.acknowledged_by = "admin@example.com"
        mock_service.acknowledge_alert.return_value = sample_alert

        request = AcknowledgeAlertRequest(acknowledged_by="admin@example.com")

        result = await acknowledge_alert(
            alert_id=str(sample_alert.id),
            request=request,
            service=mock_service,
        )

        assert result.success is True
        assert result.alert.is_acknowledged is True
        assert result.alert.acknowledged_by == "admin@example.com"

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, mock_service):
        """Test acknowledging a non-existent alert."""
        mock_service.acknowledge_alert.return_value = None

        request = AcknowledgeAlertRequest(acknowledged_by="admin@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await acknowledge_alert(
                alert_id="non-existent",
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 404
