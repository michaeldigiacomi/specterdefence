"""Unit tests for Conditional Access policies client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.ca_policies import CAPoliciesClient, MSGraphAPIError
from src.clients.ms_graph import MSGraphClient


class TestCAPoliciesClient:
    """Test cases for CAPoliciesClient."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock MS Graph client."""
        client = AsyncMock(spec=MSGraphClient)
        client.get_access_token = AsyncMock(return_value="test-token")
        return client

    @pytest.fixture
    def ca_client(self, mock_graph_client):
        """Create a CAPoliciesClient instance."""
        return CAPoliciesClient(mock_graph_client)

    @pytest.fixture
    def sample_policy(self):
        """Return a sample Conditional Access policy."""
        return {
            "id": "policy-123",
            "displayName": "Require MFA for Admins",
            "description": "Require MFA for all admin accounts",
            "state": "enabled",
            "createdDateTime": "2024-01-15T10:30:00Z",
            "modifiedDateTime": "2024-01-20T14:45:00Z",
            "conditions": {
                "users": {
                    "includeUsers": ["All"],
                    "excludeUsers": [],
                    "includeGroups": [],
                    "excludeGroups": [],
                },
                "applications": {
                    "includeApplications": ["All"],
                },
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }

    @pytest.fixture
    def sample_disabled_policy(self):
        """Return a sample disabled Conditional Access policy."""
        return {
            "id": "policy-456",
            "displayName": "Block Legacy Auth",
            "state": "disabled",
            "conditions": {
                "users": {
                    "includeUsers": ["All"],
                },
                "applications": {
                    "includeApplications": ["All"],
                },
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["block"],
            },
        }

    @pytest.mark.asyncio
    async def test_get_policies_success(self, ca_client, mock_graph_client):
        """Test successful retrieval of CA policies."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "policy-1", "displayName": "Policy 1", "state": "enabled"},
                {"id": "policy-2", "displayName": "Policy 2", "state": "disabled"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ca_client.get_policies()

        assert len(result) == 2
        assert result[0]["displayName"] == "Policy 1"
        mock_graph_client.get_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_policies_pagination(self, ca_client, mock_graph_client):
        """Test CA policies pagination."""
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "value": [{"id": "policy-1", "displayName": "Policy 1", "state": "enabled"}],
            "@odata.nextLink": "https://next.page"
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "value": [{"id": "policy-2", "displayName": "Policy 2", "state": "enabled"}],
        }

        with patch("httpx.AsyncClient.get", side_effect=[mock_response1, mock_response2]):
            result = await ca_client.get_policies()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_policies_error(self, ca_client, mock_graph_client):
        """Test error handling for CA policies."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises(MSGraphAPIError, match="Failed to fetch CA policies"):
                await ca_client.get_policies()

    @pytest.mark.asyncio
    async def test_get_policy_success(self, ca_client, mock_graph_client):
        """Test successful retrieval of a specific policy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "policy-123",
            "displayName": "Test Policy",
            "state": "enabled",
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ca_client.get_policy("policy-123")

        assert result is not None
        assert result["displayName"] == "Test Policy"

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self, ca_client, mock_graph_client):
        """Test handling of 404 for a specific policy."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ca_client.get_policy("nonexistent-policy")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_named_locations_success(self, ca_client, mock_graph_client):
        """Test successful retrieval of named locations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "loc-1", "displayName": "Trusted Office", "isTrusted": True},
                {"id": "loc-2", "displayName": "Home Office", "isTrusted": False},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ca_client.get_named_locations()

        assert len(result) == 2
        assert result[0]["displayName"] == "Trusted Office"

    def test_analyze_policy_mfa_required(self, ca_client, sample_policy):
        """Test policy analysis with MFA requirement."""
        result = ca_client.analyze_policy(sample_policy)

        assert result["state"] == "enabled"
        assert result["is_enabled"] is True
        assert result["is_mfa_required"] is True
        assert result["applies_to_all_users"] is True
        assert result["applies_to_all_apps"] is True
        assert result["grant_controls"] == ["mfa"]

    def test_analyze_policy_disabled(self, ca_client, sample_disabled_policy):
        """Test policy analysis with disabled policy."""
        result = ca_client.analyze_policy(sample_disabled_policy)

        assert result["state"] == "disabled"
        assert result["is_disabled"] is True
        assert result["is_enabled"] is False
        assert result["is_mfa_required"] is False

    def test_analyze_policy_with_location_conditions(self, ca_client):
        """Test policy analysis with location conditions."""
        policy = {
            "id": "policy-loc",
            "displayName": "Location Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "locations": {
                    "includeLocations": ["AllTrusted"],
                    "excludeLocations": ["MfaTrustedIps"],
                },
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }

        result = ca_client.analyze_policy(policy)

        assert result["has_location_conditions"] is True
        assert result["trusted_locations_only"] is True
        assert result["excluded_locations_count"] == 1

    def test_analyze_policy_with_risk_conditions(self, ca_client):
        """Test policy analysis with risk conditions."""
        policy = {
            "id": "policy-risk",
            "displayName": "Risk Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "userRiskLevels": ["high", "medium"],
                "signInRiskLevels": ["high"],
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa", "block"]},
        }

        result = ca_client.analyze_policy(policy)

        assert result["has_risk_conditions"] is True
        assert result["requires_high_risk_level"] is True
        assert result["requires_medium_risk_level"] is True
        assert result["requires_low_risk_level"] is False

    def test_analyze_policy_with_device_requirements(self, ca_client):
        """Test policy analysis with device compliance requirements."""
        policy = {
            "id": "policy-device",
            "displayName": "Device Compliance Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "devices": {"deviceFilter": {"mode": "include", "rule": "device.isCompliant -eq true"}},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["compliantDevice"]},
        }

        result = ca_client.analyze_policy(policy)

        assert result["requires_compliant_device"] is True
        assert result["has_device_conditions"] is True

    def test_analyze_policy_with_guests(self, ca_client):
        """Test policy analysis with guest user inclusion."""
        policy = {
            "id": "policy-guests",
            "displayName": "Guest MFA Policy",
            "state": "enabled",
            "conditions": {
                "users": {
                    "includeGuestsOrExternalUsers": {
                        "guestOrExternalUserTypes": "internalGuest,b2bCollaborationGuest",
                        "externalTenants": {"@odata.type": "microsoft.graph.conditionalAccessAllExternalTenants"},
                    },
                },
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }

        result = ca_client.analyze_policy(policy)

        assert result["includes_guests_or_external"] is True

    def test_analyze_policy_with_session_controls(self, ca_client):
        """Test policy analysis with session controls."""
        policy = {
            "id": "policy-session",
            "displayName": "Session Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
            "sessionControls": {
                "signInFrequency": {
                    "value": 4,
                    "period": "hours",
                    "authenticationType": "primaryAndSecondaryAuthentication",
                },
            },
        }

        result = ca_client.analyze_policy(policy)

        assert result["has_session_controls"] is True
        assert result["sign_in_frequency"] == 4
        assert result["sign_in_frequency_authentication_type"] == "primaryAndSecondaryAuthentication"

    def test_analyze_policy_with_platforms(self, ca_client):
        """Test policy analysis with platform conditions."""
        policy = {
            "id": "policy-platform",
            "displayName": "Mobile Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "platforms": {
                    "includePlatforms": ["android", "iOS"],
                },
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }

        result = ca_client.analyze_policy(policy)

        assert result["includes_mobile_platforms"] is True
        assert "android" in result["included_platforms"]
        assert "iOS" in result["included_platforms"]

    def test_calculate_security_score_enabled_with_mfa(self, ca_client):
        """Test security score calculation for enabled MFA policy."""
        analysis = {
            "is_enabled": True,
            "is_disabled": False,
            "is_mfa_required": True,
            "requires_compliant_device": False,
            "requires_hybrid_joined_device": False,
            "has_risk_conditions": False,
            "has_location_conditions": False,
            "trusted_locations_only": False,
            "has_session_controls": False,
            "applies_to_all_users": True,
            "applies_to_all_apps": True,
            "excluded_users_count": 0,
            "excluded_groups_count": 0,
        }

        score = ca_client._calculate_security_score(analysis)

        assert score > 0
        assert score <= 100

    def test_calculate_security_score_disabled_policy(self, ca_client):
        """Test security score calculation for disabled policy."""
        analysis = {
            "is_enabled": False,
            "is_disabled": True,
            "is_report_only": False,
        }

        score = ca_client._calculate_security_score(analysis)

        assert score == 0

    def test_compare_policies_state_change(self, ca_client):
        """Test policy comparison with state change."""
        old_policy = {"state": "enabled", "grant_controls": [], "is_mfa_required": False}
        new_policy = {"state": "disabled", "grant_controls": [], "is_mfa_required": False}

        result = ca_client.compare_policies(old_policy, new_policy)

        assert result["has_changes"] is True
        assert result["state_changed"] is True
        assert result["security_impact"] == "high"
        assert any("State changed" in change for change in result["changes_summary"])

    def test_compare_policies_mfa_removed(self, ca_client):
        """Test policy comparison with MFA removal."""
        old_policy = {
            "id": "policy-1",
            "displayName": "MFA Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }
        new_policy = {
            "id": "policy-1",
            "displayName": "MFA Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": [],
            },
        }

        result = ca_client.compare_policies(old_policy, new_policy)

        assert result["has_changes"] is True
        assert result["mfa_removed"] is True
        assert result["security_impact"] == "high"

    def test_compare_policies_scope_broadened(self, ca_client):
        """Test policy comparison with broadened scope."""
        old_policy = {
            "id": "policy-1",
            "displayName": "Scope Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["user-1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }
        new_policy = {
            "id": "policy-1",
            "displayName": "Scope Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }

        result = ca_client.compare_policies(old_policy, new_policy)

        assert result["has_changes"] is True
        assert result["broadened_scope"] is True

    def test_compare_policies_location_removed(self, ca_client):
        """Test policy comparison with location conditions removed."""
        old_policy = {
            "id": "policy-1",
            "displayName": "Location Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "locations": {
                    "includeLocations": ["AllTrusted"],
                },
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }
        new_policy = {
            "id": "policy-1",
            "displayName": "Location Policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }

        result = ca_client.compare_policies(old_policy, new_policy)

        assert result["has_changes"] is True
        assert any("Location" in change for change in result["changes_summary"])

    def test_compare_policies_no_changes(self, ca_client):
        """Test policy comparison with no changes."""
        policy = {"state": "enabled", "grant_controls": ["mfa"], "is_mfa_required": True}

        result = ca_client.compare_policies(policy, policy)

        assert result["has_changes"] is False

    def test_check_baseline_compliance_mfa_for_admins(self, ca_client, sample_policy):
        """Test baseline compliance check for MFA on admin policies."""
        baseline_config = {"require_mfa_for_admins": True}

        # Policy with VIP users but no MFA
        policy_with_vip = sample_policy.copy()
        policy_with_vip["conditions"]["users"]["includeGroups"] = ["admins-group"]

        analysis = ca_client.analyze_policy(policy_with_vip)
        analysis["includes_vip_users"] = True
        analysis["is_mfa_required"] = False

        result = ca_client.check_baseline_compliance(analysis, baseline_config)

        assert len(result["warnings"]) > 0
        assert any("VIP" in warning for warning in result["warnings"])

    def test_check_baseline_compliance_disabled_policy(self, ca_client, sample_disabled_policy):
        """Test baseline compliance check for disabled policy."""
        baseline_config = {"require_mfa_for_admins": True}

        analysis = ca_client.analyze_policy(sample_disabled_policy)

        result = ca_client.check_baseline_compliance(analysis, baseline_config)

        assert result["is_compliant"] is False
        assert any("disabled" in violation.lower() for violation in result["violations"])

    def test_vip_group_patterns(self, ca_client):
        """Test VIP group pattern detection."""
        vip_patterns = [
            "admins",
            "administrators",
            "vip-users",
            "executives",
            "c-level",
            "global administrators",
        ]

        for pattern in vip_patterns:
            assert any(
                pattern.lower() in p or p in pattern.lower()
                for p in ca_client.VIP_GROUP_PATTERNS
            ), f"Pattern {pattern} should be detected as VIP"

    @pytest.mark.asyncio
    async def test_get_policy_audit_logs_success(self, ca_client, mock_graph_client):
        """Test successful retrieval of policy audit logs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "audit-1",
                    "activityDisplayName": "Update conditional access policy",
                    "targetResources": [{"id": "policy-123", "displayName": "Test Policy"}],
                },
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ca_client.get_policy_audit_logs("policy-123")

        assert len(result) == 1
        assert result[0]["id"] == "audit-1"

    @pytest.mark.asyncio
    async def test_get_policy_audit_logs_filtered(self, ca_client, mock_graph_client):
        """Test audit logs filtering by policy ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "audit-1",
                    "activityDisplayName": "Update conditional access policy",
                    "targetResources": [{"id": "policy-123", "displayName": "Policy 1"}],
                },
                {
                    "id": "audit-2",
                    "activityDisplayName": "Update conditional access policy",
                    "targetResources": [{"id": "policy-456", "displayName": "Policy 2"}],
                },
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await ca_client.get_policy_audit_logs("policy-123")

        assert len(result) == 1
        assert result[0]["id"] == "audit-1"
