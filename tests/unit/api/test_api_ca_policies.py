"""Unit tests for Conditional Access policies API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.ca_policies import router
from src.models.ca_policies import (
    AlertSeverity,
    CABaselineConfigModel,
    CAPolicyAlertModel,
    CAPolicyChangeModel,
    CAPolicyModel,
    ChangeType,
    PolicyState,
)

# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/ca-policies")
client = TestClient(app)


class TestCAPoliciesAPI:
    """Test cases for CA policies API endpoints."""

    @pytest.fixture
    def sample_policy(self):
        """Return a sample CA policy."""
        policy = MagicMock(spec=CAPolicyModel)
        policy.id = uuid4()
        policy.tenant_id = "tenant-123"
        policy.policy_id = "ms-policy-123"
        policy.display_name = "Require MFA for Admins"
        policy.description = "Require MFA for all admin accounts"
        policy.state = PolicyState.ENABLED
        policy.grant_controls = ["mfa"]
        policy.is_mfa_required = True
        policy.applies_to_all_users = True
        policy.applies_to_all_apps = True
        policy.is_baseline_policy = True
        policy.baseline_compliant = True
        policy.security_score = 75
        policy.created_at = datetime.utcnow()
        policy.updated_at = datetime.utcnow()
        policy.last_scan_at = datetime.utcnow()
        return policy

    @pytest.fixture
    def sample_change(self):
        """Return a sample policy change."""
        change = MagicMock(spec=CAPolicyChangeModel)
        change.id = uuid4()
        change.policy_id = uuid4()
        change.tenant_id = "tenant-123"
        change.change_type = ChangeType.DISABLED
        change.changed_by = "admin@example.com"
        change.changed_by_email = "admin@example.com"
        change.changes_summary = ["Policy disabled"]
        change.security_impact = "high"
        change.mfa_removed = False
        change.detected_at = datetime.utcnow()
        return change

    @pytest.fixture
    def sample_alert(self):
        """Return a sample policy alert."""
        alert = MagicMock(spec=CAPolicyAlertModel)
        alert.id = uuid4()
        alert.policy_id = uuid4()
        alert.tenant_id = "tenant-123"
        alert.alert_type = ChangeType.DISABLED
        alert.severity = AlertSeverity.HIGH
        alert.title = "CA Policy Disabled: Require MFA for Admins"
        alert.description = "Policy has been disabled"
        alert.is_acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        alert.created_at = datetime.utcnow()
        return alert

    def test_list_ca_policies(self, sample_policy):
        """Test listing CA policies."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policies = AsyncMock(return_value={
                "items": [sample_policy],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["display_name"] == "Require MFA for Admins"

    def test_list_ca_policies_with_state_filter(self, sample_policy):
        """Test listing CA policies with state filter."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policies = AsyncMock(return_value={
                "items": [sample_policy],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/?state=enabled")

        assert response.status_code == 200
        mock_instance.get_policies.assert_called_once()
        call_kwargs = mock_instance.get_policies.call_args.kwargs
        assert call_kwargs["state"] == PolicyState.ENABLED

    def test_list_ca_policies_invalid_state(self):
        """Test listing CA policies with invalid state filter."""
        response = client.get("/api/v1/ca-policies/?state=invalid")

        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

    def test_get_ca_policy(self, sample_policy):
        """Test getting a specific CA policy."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policy_by_id = AsyncMock(return_value=sample_policy)
            mock_service.return_value = mock_instance

            response = client.get(f"/api/v1/ca-policies/{sample_policy.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Require MFA for Admins"
        assert data["is_mfa_required"] is True

    def test_get_ca_policy_not_found(self):
        """Test getting a non-existent CA policy."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policy_by_id = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/nonexistent-id")

        assert response.status_code == 404

    def test_get_policy_changes(self, sample_policy, sample_change):
        """Test getting policy changes."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policy_by_id = AsyncMock(return_value=sample_policy)
            mock_instance.get_policy_changes = AsyncMock(return_value={
                "items": [sample_change],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get(f"/api/v1/ca-policies/{sample_policy.id}/changes")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["change_type"] == "disabled"

    def test_get_tenant_ca_policies(self, sample_policy):
        """Test getting tenant CA policies."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policies = AsyncMock(return_value={
                "items": [sample_policy],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/tenants/tenant-123/policies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_disabled_policies(self, sample_policy):
        """Test getting disabled policies."""
        sample_policy.state = PolicyState.DISABLED

        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_disabled_policies = AsyncMock(return_value=[sample_policy])
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/tenants/tenant-123/disabled")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_mfa_policies(self, sample_policy):
        """Test getting MFA policies."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_mfa_policies = AsyncMock(return_value=[sample_policy])
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/tenants/tenant-123/mfa")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_mfa_required"] is True

    def test_get_ca_policies_summary(self):
        """Test getting CA policies summary."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policies_summary = AsyncMock(return_value={
                "total_policies": 10,
                "enabled": 8,
                "disabled": 1,
                "report_only": 1,
                "mfa_policies": 5,
                "baseline_policies": 3,
                "baseline_compliant": 2,
                "baseline_violations": 1,
                "recent_changes": 2,
                "high_severity_alerts": 1,
                "policies_covering_all_users": 4,
                "policies_covering_all_apps": 3,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/tenants/tenant-123/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_policies"] == 10
        assert data["mfa_policies"] == 5
        assert data["baseline_violations"] == 1

    def test_scan_ca_policies(self):
        """Test triggering CA policy scan."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.scan_tenant_policies = AsyncMock(return_value={
                "policies_found": 5,
                "new_policies": 1,
                "updated_policies": 2,
                "changes_detected": 3,
                "alerts_triggered": 1,
                "baseline_violations": 0,
                "disabled_policies": 0,
                "mfa_policies": 3,
            })
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/ca-policies/scan",
                json={
                    "tenant_id": "tenant-123",
                    "trigger_alerts": True,
                    "compare_baseline": True,
                }
            )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["policies_found"] == 5

    def test_scan_ca_policies_tenant_not_found(self):
        """Test triggering CA policy scan with non-existent tenant."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.scan_tenant_policies = AsyncMock(side_effect=ValueError("Tenant not found"))
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/ca-policies/scan",
                json={
                    "tenant_id": "nonexistent-tenant",
                    "trigger_alerts": True,
                }
            )

        assert response.status_code == 404

    def test_list_policy_changes(self, sample_change):
        """Test listing policy changes."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policy_changes = AsyncMock(return_value={
                "items": [sample_change],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/changes")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_policy_changes_with_type_filter(self, sample_change):
        """Test listing policy changes with type filter."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_policy_changes = AsyncMock(return_value={
                "items": [sample_change],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/changes?change_type=disabled")

        assert response.status_code == 200
        mock_instance.get_policy_changes.assert_called_once()
        call_kwargs = mock_instance.get_policy_changes.call_args.kwargs
        assert call_kwargs["change_type"] == ChangeType.DISABLED

    def test_list_policy_changes_invalid_type(self):
        """Test listing policy changes with invalid type filter."""
        response = client.get("/api/v1/ca-policies/changes?change_type=invalid")

        assert response.status_code == 400
        assert "Invalid change type" in response.json()["detail"]

    def test_list_ca_policy_alerts(self, sample_alert):
        """Test listing CA policy alerts."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_alerts = AsyncMock(return_value={
                "items": [sample_alert],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_ca_policy_alerts_with_severity_filter(self, sample_alert):
        """Test listing CA policy alerts with severity filter."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_alerts = AsyncMock(return_value={
                "items": [sample_alert],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/alerts?severity=HIGH")

        assert response.status_code == 200
        mock_instance.get_alerts.assert_called_once()
        call_kwargs = mock_instance.get_alerts.call_args.kwargs
        assert call_kwargs["severity"] == AlertSeverity.HIGH

    def test_list_ca_policy_alerts_invalid_severity(self):
        """Test listing CA policy alerts with invalid severity filter."""
        response = client.get("/api/v1/ca-policies/alerts?severity=invalid")

        assert response.status_code == 400
        assert "Invalid severity" in response.json()["detail"]

    def test_acknowledge_alert(self, sample_alert):
        """Test acknowledging an alert."""
        sample_alert.is_acknowledged = True
        sample_alert.acknowledged_by = "admin@example.com"

        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.acknowledge_alert = AsyncMock(return_value=sample_alert)
            mock_service.return_value = mock_instance

            response = client.post(
                f"/api/v1/ca-policies/alerts/{sample_alert.id}/acknowledge",
                json={"acknowledged_by": "admin@example.com"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["alert"]["is_acknowledged"] is True

    def test_acknowledge_alert_not_found(self):
        """Test acknowledging a non-existent alert."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.acknowledge_alert = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/ca-policies/alerts/nonexistent-id/acknowledge",
                json={"acknowledged_by": "admin@example.com"}
            )

        assert response.status_code == 404

    def test_get_baseline_config(self):
        """Test getting baseline configuration."""
        baseline = MagicMock(spec=CABaselineConfigModel)
        baseline.id = uuid4()
        baseline.tenant_id = "tenant-123"
        baseline.require_mfa_for_admins = True
        baseline.require_mfa_for_all_users = False
        baseline.block_legacy_auth = True
        baseline.require_compliant_or_hybrid_joined = False
        baseline.block_high_risk_signins = True
        baseline.block_unknown_locations = False
        baseline.require_mfa_for_guests = True
        baseline.custom_requirements = {}
        baseline.created_at = datetime.utcnow()
        baseline.updated_at = datetime.utcnow()
        baseline.created_by = "admin@example.com"

        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance._get_baseline_config = AsyncMock(return_value=baseline)
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/tenants/tenant-123/baseline")

        assert response.status_code == 200
        data = response.json()
        assert data["require_mfa_for_admins"] is True
        assert data["require_mfa_for_all_users"] is False

    def test_get_baseline_config_not_found(self):
        """Test getting non-existent baseline configuration."""
        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance._get_baseline_config = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/ca-policies/tenants/tenant-123/baseline")

        assert response.status_code == 404

    def test_set_baseline_config(self):
        """Test setting baseline configuration."""
        baseline = MagicMock(spec=CABaselineConfigModel)
        baseline.id = uuid4()
        baseline.tenant_id = "tenant-123"
        baseline.require_mfa_for_admins = True
        baseline.require_mfa_for_all_users = True
        baseline.block_legacy_auth = True
        baseline.require_compliant_or_hybrid_joined = True
        baseline.block_high_risk_signins = True
        baseline.block_unknown_locations = True
        baseline.require_mfa_for_guests = True
        baseline.custom_requirements = {}
        baseline.created_at = datetime.utcnow()
        baseline.updated_at = datetime.utcnow()
        baseline.created_by = "admin@example.com"

        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.set_baseline_config = AsyncMock(return_value=baseline)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/ca-policies/tenants/tenant-123/baseline",
                json={
                    "require_mfa_for_admins": True,
                    "require_mfa_for_all_users": True,
                    "block_legacy_auth": True,
                    "require_compliant_or_hybrid_joined": True,
                    "block_high_risk_signins": True,
                    "block_unknown_locations": True,
                    "require_mfa_for_guests": True,
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["require_mfa_for_admins"] is True
        assert data["require_mfa_for_all_users"] is True

    def test_set_baseline_config_partial(self):
        """Test setting partial baseline configuration."""
        baseline = MagicMock(spec=CABaselineConfigModel)
        baseline.id = uuid4()
        baseline.tenant_id = "tenant-123"
        baseline.require_mfa_for_admins = False
        baseline.require_mfa_for_all_users = False
        baseline.block_legacy_auth = True
        baseline.require_compliant_or_hybrid_joined = False
        baseline.block_high_risk_signins = True
        baseline.block_unknown_locations = False
        baseline.require_mfa_for_guests = True
        baseline.custom_requirements = {}
        baseline.created_at = datetime.utcnow()
        baseline.updated_at = datetime.utcnow()
        baseline.created_by = None

        with patch("src.api.ca_policies.get_ca_policies_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.set_baseline_config = AsyncMock(return_value=baseline)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/v1/ca-policies/tenants/tenant-123/baseline",
                json={
                    "require_mfa_for_admins": False,
                    "block_legacy_auth": True,
                }
            )

        assert response.status_code == 200
