"""Unit tests for Conditional Access policies API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

# Import endpoint functions with aliases to avoid pytest collection issues
import src.api.ca_policies as ca_policies_api
from src.models.ca_policies import (
    AlertSeverity,
    ChangeType,
    PolicyState,
)
from src.services.ca_policies import CAPoliciesService


class TestCAPoliciesAPI:
    """Test cases for CA policies API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock CA policies service."""
        service = AsyncMock(spec=CAPoliciesService)
        return service

    @pytest.fixture
    def sample_policy(self):
        """Return a sample CA policy."""
        policy = MagicMock()
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
        change = MagicMock()
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
        alert = MagicMock()
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

    @pytest.mark.asyncio
    async def test_list_ca_policies(self, mock_service, sample_policy):
        """Test listing CA policies."""
        mock_service.get_policies.return_value = {
            "items": [sample_policy],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.list_ca_policies(
            tenant_id="tenant-123", state=None, service=mock_service
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].display_name == "Require MFA for Admins"

    @pytest.mark.asyncio
    async def test_list_ca_policies_with_state_filter(self, mock_service, sample_policy):
        """Test listing CA policies with state filter."""
        mock_service.get_policies.return_value = {
            "items": [sample_policy],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.list_ca_policies(
            tenant_id="tenant-123", state="enabled", service=mock_service
        )

        assert result.total == 1
        mock_service.get_policies.assert_called_once()
        call_kwargs = mock_service.get_policies.call_args.kwargs
        assert call_kwargs["state"] == PolicyState.ENABLED

    @pytest.mark.asyncio
    async def test_list_ca_policies_invalid_state(self, mock_service):
        """Test listing CA policies with invalid state filter."""
        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.list_ca_policies(
                tenant_id="tenant-123", state="invalid", service=mock_service
            )

        assert exc_info.value.status_code == 400
        assert "Invalid state" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_ca_policy(self, mock_service, sample_policy):
        """Test getting a specific CA policy."""
        mock_service.get_policy_by_id.return_value = sample_policy

        result = await ca_policies_api.get_ca_policy(
            policy_id=str(sample_policy.id), service=mock_service
        )

        assert result.display_name == "Require MFA for Admins"
        assert result.is_mfa_required is True

    @pytest.mark.asyncio
    async def test_get_ca_policy_not_found(self, mock_service):
        """Test getting a non-existent CA policy."""
        mock_service.get_policy_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.get_ca_policy(policy_id="nonexistent-id", service=mock_service)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_policy_changes(self, mock_service, sample_policy, sample_change):
        """Test getting policy changes."""
        mock_service.get_policy_by_id.return_value = sample_policy
        mock_service.get_policy_changes.return_value = {
            "items": [sample_change],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.get_policy_changes(
            policy_id=str(sample_policy.id), service=mock_service
        )

        assert result.total == 1
        assert result.items[0].change_type == ChangeType.DISABLED

    @pytest.mark.asyncio
    async def test_get_tenant_ca_policies(self, mock_service, sample_policy):
        """Test getting tenant CA policies."""
        mock_service.get_policies.return_value = {
            "items": [sample_policy],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.get_tenant_ca_policies(
            tenant_id="tenant-123", service=mock_service
        )

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_disabled_policies(self, mock_service, sample_policy):
        """Test getting disabled policies."""
        sample_policy.state = PolicyState.DISABLED
        mock_service.get_disabled_policies.return_value = [sample_policy]

        result = await ca_policies_api.get_disabled_policies(
            tenant_id="tenant-123", service=mock_service
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_mfa_policies(self, mock_service, sample_policy):
        """Test getting MFA policies."""
        mock_service.get_mfa_policies.return_value = [sample_policy]

        result = await ca_policies_api.get_mfa_policies(
            tenant_id="tenant-123", service=mock_service
        )

        assert len(result) == 1
        assert result[0].is_mfa_required is True

    @pytest.mark.asyncio
    async def test_get_ca_policies_summary(self, mock_service):
        """Test getting CA policies summary."""
        mock_service.get_policies_summary.return_value = {
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
        }

        result = await ca_policies_api.get_ca_policies_summary(
            tenant_id="tenant-123", service=mock_service
        )

        assert result.total_policies == 10
        assert result.mfa_policies == 5
        assert result.baseline_violations == 1

    @pytest.mark.asyncio
    async def test_scan_ca_policies(self, mock_service):
        """Test triggering CA policy scan."""
        mock_service.scan_tenant_policies.return_value = {
            "policies_found": 5,
            "new_policies": 1,
            "updated_policies": 2,
            "changes_detected": 3,
            "alerts_triggered": 1,
            "baseline_violations": 0,
            "disabled_policies": 0,
            "mfa_policies": 3,
        }

        from src.models.ca_policies import CAPolicyScanRequest

        request = CAPolicyScanRequest(
            tenant_id="tenant-123",
            trigger_alerts=True,
            compare_baseline=True,
        )

        result = await ca_policies_api.scan_ca_policies(request=request, service=mock_service)

        assert result.success is True
        assert result.policies_found == 5

    @pytest.mark.asyncio
    async def test_scan_ca_policies_tenant_not_found(self, mock_service):
        """Test triggering CA policy scan with non-existent tenant."""
        mock_service.scan_tenant_policies.side_effect = ValueError("Tenant not found")

        from src.models.ca_policies import CAPolicyScanRequest

        request = CAPolicyScanRequest(
            tenant_id="nonexistent-tenant",
            trigger_alerts=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.scan_ca_policies(request=request, service=mock_service)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_policy_changes(self, mock_service, sample_change):
        """Test listing policy changes."""
        mock_service.get_policy_changes.return_value = {
            "items": [sample_change],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.list_policy_changes(
            tenant_id="tenant-123", service=mock_service
        )

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_policy_changes_with_type_filter(self, mock_service, sample_change):
        """Test listing policy changes with type filter."""
        mock_service.get_policy_changes.return_value = {
            "items": [sample_change],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.list_policy_changes(
            tenant_id="tenant-123", change_type="disabled", service=mock_service
        )

        assert result.total == 1
        mock_service.get_policy_changes.assert_called_once()
        call_kwargs = mock_service.get_policy_changes.call_args.kwargs
        assert call_kwargs["change_type"] == ChangeType.DISABLED

    @pytest.mark.asyncio
    async def test_list_policy_changes_invalid_type(self, mock_service):
        """Test listing policy changes with invalid type filter."""
        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.list_policy_changes(
                tenant_id="tenant-123", change_type="invalid", service=mock_service
            )

        assert exc_info.value.status_code == 400
        assert "Invalid change type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_ca_policy_alerts(self, mock_service, sample_alert):
        """Test listing CA policy alerts."""
        mock_service.get_alerts.return_value = {
            "items": [sample_alert],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.list_ca_policy_alerts(
            tenant_id="tenant-123", service=mock_service
        )

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_ca_policy_alerts_with_severity_filter(self, mock_service, sample_alert):
        """Test listing CA policy alerts with severity filter."""
        mock_service.get_alerts.return_value = {
            "items": [sample_alert],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await ca_policies_api.list_ca_policy_alerts(
            tenant_id="tenant-123", severity="HIGH", service=mock_service
        )

        assert result.total == 1
        mock_service.get_alerts.assert_called_once()
        call_kwargs = mock_service.get_alerts.call_args.kwargs
        assert call_kwargs["severity"] == AlertSeverity.HIGH

    @pytest.mark.asyncio
    async def test_list_ca_policy_alerts_invalid_severity(self, mock_service):
        """Test listing CA policy alerts with invalid severity filter."""
        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.list_ca_policy_alerts(
                tenant_id="tenant-123", severity="invalid", service=mock_service
            )

        assert exc_info.value.status_code == 400
        assert "Invalid severity" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, mock_service, sample_alert):
        """Test acknowledging an alert."""
        sample_alert.is_acknowledged = True
        sample_alert.acknowledged_by = "admin@example.com"
        mock_service.acknowledge_alert.return_value = sample_alert

        from src.models.ca_policies import AcknowledgeAlertRequest

        request = AcknowledgeAlertRequest(acknowledged_by="admin@example.com")

        result = await ca_policies_api.acknowledge_alert(
            alert_id=str(sample_alert.id), request=request, service=mock_service
        )

        assert result.success is True
        assert result.alert.is_acknowledged is True

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, mock_service):
        """Test acknowledging a non-existent alert."""
        mock_service.acknowledge_alert.return_value = None

        from src.models.ca_policies import AcknowledgeAlertRequest

        request = AcknowledgeAlertRequest(acknowledged_by="admin@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.acknowledge_alert(
                alert_id="nonexistent-id", request=request, service=mock_service
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_baseline_config(self, mock_service):
        """Test getting baseline configuration."""
        baseline = MagicMock()
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

        mock_service._get_baseline_config.return_value = baseline

        result = await ca_policies_api.get_baseline_config(
            tenant_id="tenant-123", service=mock_service
        )

        assert result.require_mfa_for_admins is True
        assert result.require_mfa_for_all_users is False

    @pytest.mark.asyncio
    async def test_get_baseline_config_not_found(self, mock_service):
        """Test getting non-existent baseline configuration."""
        mock_service._get_baseline_config.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await ca_policies_api.get_baseline_config(tenant_id="tenant-123", service=mock_service)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_set_baseline_config(self, mock_service):
        """Test setting baseline configuration."""
        baseline = MagicMock()
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

        mock_service.set_baseline_config.return_value = baseline

        from src.api.ca_policies import SetBaselineRequest

        request = SetBaselineRequest(
            require_mfa_for_admins=True,
            require_mfa_for_all_users=True,
            block_legacy_auth=True,
            require_compliant_or_hybrid_joined=True,
            block_high_risk_signins=True,
            block_unknown_locations=True,
            require_mfa_for_guests=True,
        )

        result = await ca_policies_api.set_baseline_config(
            tenant_id="tenant-123", request=request, service=mock_service
        )

        assert result.require_mfa_for_admins is True
        assert result.require_mfa_for_all_users is True

    @pytest.mark.asyncio
    async def test_set_baseline_config_partial(self, mock_service):
        """Test setting partial baseline configuration."""
        baseline = MagicMock()
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

        mock_service.set_baseline_config.return_value = baseline

        from src.api.ca_policies import SetBaselineRequest

        request = SetBaselineRequest(
            require_mfa_for_admins=False,
            block_legacy_auth=True,
        )

        result = await ca_policies_api.set_baseline_config(
            tenant_id="tenant-123", request=request, service=mock_service
        )

        assert result.require_mfa_for_admins is False
        assert result.block_legacy_auth is True
