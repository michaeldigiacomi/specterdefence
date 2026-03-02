"""Microsoft Graph client for Conditional Access policies."""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.clients.ms_graph import MSGraphAPIError, MSGraphClient

logger = logging.getLogger(__name__)


class CAPoliciesClient:
    """Client for fetching and managing Conditional Access policies via Microsoft Graph API."""

    # Risk levels mapping
    RISK_LEVELS = {
        "low": "low",
        "medium": "medium",
        "high": "high"
    }

    # MFA grant control values
    MFA_CONTROLS = ["mfa", "requireMFA", "RequireMFA"]

    # Device compliance controls
    DEVICE_CONTROLS = ["compliantDevice", "compliant", "domainJoinedDevice", "hybridJoinedDevice"]

    # VIP group patterns (common naming conventions)
    VIP_GROUP_PATTERNS = [
        "admin", "administrator", "vip", "executive", "c-level",
        "cfo", "ceo", "cio", "cto", "csuite", "leadership",
        "global administrator", "privileged"
    ]

    def __init__(self, graph_client: MSGraphClient) -> None:
        """Initialize with existing MS Graph client.
        
        Args:
            graph_client: Authenticated MSGraphClient instance
        """
        self.graph_client = graph_client

    async def get_policies(self) -> list[dict[str, Any]]:
        """Get all Conditional Access policies in the tenant.
        
        Returns:
            List of Conditional Access policy objects
        """
        token = await self.graph_client.get_access_token()

        policies = []
        url = "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies"
        params = {
            "$top": "999",
        }

        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if url == "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" else None
                )

                if response.status_code != 200:
                    raise MSGraphAPIError(
                        f"Failed to fetch CA policies: {response.status_code}",
                        status_code=response.status_code
                    )

                data = response.json()
                policies.extend(data.get("value", []))

                # Handle pagination
                url = data.get("@odata.nextLink")
                params = None

        logger.info(f"Retrieved {len(policies)} Conditional Access policies")
        return policies

    async def get_policy(self, policy_id: str) -> dict[str, Any] | None:
        """Get a specific Conditional Access policy.
        
        Args:
            policy_id: The Conditional Access policy ID
            
        Returns:
            Policy object or None if not found
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies/{policy_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                raise MSGraphAPIError(
                    f"Failed to fetch CA policy {policy_id}: {response.status_code}",
                    status_code=response.status_code
                )

            return response.json()

    async def get_named_locations(self) -> list[dict[str, Any]]:
        """Get all named locations (trusted locations) configured in the tenant.
        
        Returns:
            List of named location objects
        """
        token = await self.graph_client.get_access_token()

        locations = []
        url = "https://graph.microsoft.com/v1.0/identity/conditionalAccess/namedLocations"
        params = {
            "$top": "999",
        }

        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if url == "https://graph.microsoft.com/v1.0/identity/conditionalAccess/namedLocations" else None
                )

                if response.status_code != 200:
                    logger.warning(f"Failed to fetch named locations: {response.status_code}")
                    return []

                data = response.json()
                locations.extend(data.get("value", []))

                url = data.get("@odata.nextLink")
                params = None

        return locations

    def analyze_policy(self, policy: dict[str, Any]) -> dict[str, Any]:
        """Analyze a Conditional Access policy for security characteristics.
        
        Args:
            policy: Policy object from Graph API
            
        Returns:
            Analysis results with security flags
        """
        analysis = {
            # State
            "state": policy.get("state", "enabled"),
            "is_enabled": policy.get("state") == "enabled",
            "is_disabled": policy.get("state") == "disabled",
            "is_report_only": policy.get("state") == "reportOnly",

            # Grant controls
            "grant_controls": [],
            "grant_controls_operator": None,
            "is_mfa_required": False,
            "requires_compliant_device": False,
            "requires_hybrid_joined_device": False,

            # Session controls
            "has_session_controls": False,
            "sign_in_frequency": None,
            "sign_in_frequency_authentication_type": None,

            # Conditions - Users
            "applies_to_all_users": False,
            "includes_guests_or_external": False,
            "includes_vip_users": False,
            "excluded_users_count": 0,
            "excluded_groups_count": 0,

            # Conditions - Applications
            "applies_to_all_apps": False,
            "excluded_apps_count": 0,

            # Conditions - Risk
            "requires_high_risk_level": False,
            "requires_medium_risk_level": False,
            "requires_low_risk_level": False,
            "has_risk_conditions": False,

            # Conditions - Location
            "has_location_conditions": False,
            "trusted_locations_only": False,
            "excluded_locations_count": 0,

            # Conditions - Device
            "has_device_conditions": False,

            # Conditions - Platform
            "includes_mobile_platforms": False,
            "included_platforms": [],
            "excluded_platforms": [],

            # Security score calculation
            "security_score": 0,
            "security_features": [],
        }

        # Analyze grant controls
        grant_controls = policy.get("grantControls", {})
        if grant_controls:
            analysis["grant_controls"] = grant_controls.get("builtInControls", []) + \
                                         grant_controls.get("customAuthenticationFactors", [])
            analysis["grant_controls_operator"] = grant_controls.get("operator", "OR")

            # Check for MFA
            analysis["is_mfa_required"] = any(
                control.lower() in [c.lower() for c in self.MFA_CONTROLS]
                for control in analysis["grant_controls"]
            )

            # Check for device requirements
            analysis["requires_compliant_device"] = "compliantDevice" in analysis["grant_controls"] or \
                                                    "compliant" in analysis["grant_controls"]
            analysis["requires_hybrid_joined_device"] = "domainJoinedDevice" in analysis["grant_controls"] or \
                                                        "hybridJoinedDevice" in analysis["grant_controls"]

        # Analyze session controls
        session_controls = policy.get("sessionControls", {})
        if session_controls:
            analysis["has_session_controls"] = True
            sign_in_freq = session_controls.get("signInFrequency", {})
            if sign_in_freq:
                analysis["sign_in_frequency"] = sign_in_freq.get("value")
                analysis["sign_in_frequency_authentication_type"] = sign_in_freq.get("authenticationType", "primaryAndSecondaryAuthentication")

        # Analyze conditions - Users
        conditions = policy.get("conditions", {})
        users = conditions.get("users", {})

        if users:
            # Check if applies to all users
            include_users = users.get("includeUsers", [])
            include_groups = users.get("includeGroups", [])
            include_roles = users.get("includeRoles", [])

            analysis["applies_to_all_users"] = "All" in include_users or \
                                               "All" in include_groups

            # Check for guests/external
            include_guests = users.get("includeGuestsOrExternalUsers", {})
            if include_guests and include_guests.get("guestOrExternalUserTypes"):
                analysis["includes_guests_or_external"] = True

            # Check for VIP groups (by analyzing group names if available)
            for group in include_groups:
                if any(pattern in group.lower() for pattern in self.VIP_GROUP_PATTERNS):
                    analysis["includes_vip_users"] = True
                    break

            # Check excluded users/groups
            analysis["excluded_users_count"] = len(users.get("excludeUsers", []))
            analysis["excluded_groups_count"] = len(users.get("excludeGroups", []))

        # Analyze conditions - Applications
        applications = conditions.get("applications", {})
        if applications:
            include_apps = applications.get("includeApplications", [])
            analysis["applies_to_all_apps"] = "All" in include_apps
            analysis["excluded_apps_count"] = len(applications.get("excludeApplications", []))

        # Analyze conditions - Risk
        user_risk_levels = conditions.get("userRiskLevels", [])
        sign_in_risk_levels = conditions.get("signInRiskLevels", [])

        if user_risk_levels or sign_in_risk_levels:
            analysis["has_risk_conditions"] = True

            all_risk_levels = user_risk_levels + sign_in_risk_levels
            analysis["requires_high_risk_level"] = "high" in [r.lower() for r in all_risk_levels]
            analysis["requires_medium_risk_level"] = "medium" in [r.lower() for r in all_risk_levels]
            analysis["requires_low_risk_level"] = "low" in [r.lower() for r in all_risk_levels]

        # Analyze conditions - Locations
        locations = conditions.get("locations", {})
        if locations:
            analysis["has_location_conditions"] = True
            include_locations = locations.get("includeLocations", [])
            exclude_locations = locations.get("excludeLocations", [])

            analysis["trusted_locations_only"] = "AllTrusted" in include_locations
            analysis["excluded_locations_count"] = len(exclude_locations)

        # Analyze conditions - Platforms
        platforms = conditions.get("platforms", {})
        if platforms:
            analysis["included_platforms"] = platforms.get("includePlatforms", [])
            analysis["excluded_platforms"] = platforms.get("excludePlatforms", [])

            mobile_platforms = ["android", "iOS"]
            analysis["includes_mobile_platforms"] = any(
                p.lower() in mobile_platforms for p in analysis["included_platforms"]
            )

        # Analyze conditions - Devices
        devices = conditions.get("devices", {})
        if devices:
            analysis["has_device_conditions"] = True

        # Calculate security score
        analysis["security_score"] = self._calculate_security_score(analysis)

        return analysis

    def _calculate_security_score(self, analysis: dict[str, Any]) -> int:
        """Calculate a security score for the policy.
        
        Args:
            analysis: Policy analysis results
            
        Returns:
            Security score from 0-100
        """
        score = 0

        # Base score for enabled policies
        if analysis.get("is_enabled"):
            score += 20
        elif analysis.get("is_report_only"):
            score += 5

        # MFA requirement (important)
        if analysis.get("is_mfa_required"):
            score += 25

        # Device compliance (important)
        if analysis.get("requires_compliant_device"):
            score += 20
        if analysis.get("requires_hybrid_joined_device"):
            score += 15

        # Risk-based conditions
        if analysis.get("has_risk_conditions"):
            score += 10

        # Location-based conditions
        if analysis.get("has_location_conditions"):
            score += 5
        if analysis.get("trusted_locations_only"):
            score += 5

        # Session controls
        if analysis.get("has_session_controls"):
            score += 5

        # Broad coverage bonus
        if analysis.get("applies_to_all_users"):
            score += 5
        if analysis.get("applies_to_all_apps"):
            score += 5

        # Penalties
        if analysis.get("is_disabled"):
            score = 0  # Disabled policies get 0

        # Too many exclusions penalty
        if analysis.get("excluded_users_count", 0) > 5:
            score -= 5
        if analysis.get("excluded_groups_count", 0) > 5:
            score -= 5

        return max(0, min(100, score))

    def compare_policies(
        self,
        old_policy: dict[str, Any],
        new_policy: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare two policy states to detect changes.
        
        Args:
            old_policy: Previous policy state
            new_policy: New policy state
            
        Returns:
            Comparison results with changes detected
        """
        changes = {
            "has_changes": False,
            "change_types": [],
            "changes_summary": [],
            "security_impact": "none",
            "mfa_removed": False,
            "broadened_scope": False,
            "narrowed_scope": False,
            "state_changed": False,
            "old_state": old_policy.get("state"),
            "new_state": new_policy.get("state"),
            "detailed_changes": {}
        }

        # Check state change
        if old_policy.get("state") != new_policy.get("state"):
            changes["has_changes"] = True
            changes["state_changed"] = True
            changes["change_types"].append("state_change")
            changes["changes_summary"].append(
                f"State changed from {old_policy.get('state')} to {new_policy.get('state')}"
            )

            # Security impact of state change
            if old_policy.get("state") == "enabled" and new_policy.get("state") in ["disabled", "reportOnly"]:
                changes["security_impact"] = "high"
            elif old_policy.get("state") in ["disabled", "reportOnly"] and new_policy.get("state") == "enabled":
                changes["security_impact"] = "positive"

        # Analyze old and new states
        old_analysis = self.analyze_policy(old_policy)
        new_analysis = self.analyze_policy(new_policy)

        # Check MFA changes
        if old_analysis["is_mfa_required"] and not new_analysis["is_mfa_required"]:
            changes["has_changes"] = True
            changes["mfa_removed"] = True
            changes["change_types"].append("mfa_removed")
            changes["changes_summary"].append("MFA requirement removed")
            if changes["security_impact"] not in ["high", "critical"]:
                changes["security_impact"] = "high"

        # Check scope changes
        if not old_analysis["applies_to_all_users"] and new_analysis["applies_to_all_users"]:
            changes["has_changes"] = True
            changes["broadened_scope"] = True
            changes["change_types"].append("scope_broadened")
            changes["changes_summary"].append("Policy now applies to all users")

        if old_analysis["applies_to_all_users"] and not new_analysis["applies_to_all_users"]:
            changes["has_changes"] = True
            changes["narrowed_scope"] = True
            changes["change_types"].append("scope_narrowed")
            changes["changes_summary"].append("Policy scope reduced (no longer applies to all users)")

        if not old_analysis["applies_to_all_apps"] and new_analysis["applies_to_all_apps"]:
            changes["has_changes"] = True
            changes["broadened_scope"] = True
            changes["change_types"].append("scope_broadened")
            changes["changes_summary"].append("Policy now applies to all applications")

        # Check location condition changes
        if old_analysis["has_location_conditions"] and not new_analysis["has_location_conditions"]:
            changes["has_changes"] = True
            changes["change_types"].append("location_removed")
            changes["changes_summary"].append("Location-based conditions removed")
            if changes["security_impact"] == "none":
                changes["security_impact"] = "medium"

        # Check device compliance changes
        if old_analysis["requires_compliant_device"] and not new_analysis["requires_compliant_device"]:
            changes["has_changes"] = True
            changes["change_types"].append("compliance_removed")
            changes["changes_summary"].append("Device compliance requirement removed")
            if changes["security_impact"] not in ["high", "critical"]:
                changes["security_impact"] = "medium"

        # Check risk condition changes
        if old_analysis["has_risk_conditions"] and not new_analysis["has_risk_conditions"]:
            changes["has_changes"] = True
            changes["change_types"].append("risk_conditions_removed")
            changes["changes_summary"].append("Risk-based conditions removed")

        # Check grant controls changes
        old_grants = set(old_analysis["grant_controls"])
        new_grants = set(new_analysis["grant_controls"])

        added_grants = new_grants - old_grants
        removed_grants = old_grants - new_grants

        if added_grants:
            changes["has_changes"] = True
            changes["change_types"].append("grants_added")
            changes["changes_summary"].append(f"Added grant controls: {', '.join(added_grants)}")

        if removed_grants:
            changes["has_changes"] = True
            changes["change_types"].append("grants_removed")
            changes["changes_summary"].append(f"Removed grant controls: {', '.join(removed_grants)}")

        # Check session controls changes
        if old_analysis["sign_in_frequency"] != new_analysis["sign_in_frequency"]:
            changes["has_changes"] = True
            changes["change_types"].append("session_controls_changed")
            changes["changes_summary"].append(
                f"Sign-in frequency changed from {old_analysis['sign_in_frequency']} to {new_analysis['sign_in_frequency']}"
            )

        # Store detailed changes
        changes["detailed_changes"] = {
            "old_analysis": old_analysis,
            "new_analysis": new_analysis,
        }

        return changes

    async def get_policy_audit_logs(
        self,
        policy_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Get audit logs for a specific Conditional Access policy.
        
        Args:
            policy_id: The policy ID to get audit logs for
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of audit log entries
        """
        token = await self.graph_client.get_access_token()

        # Build filter for CA policy changes
        filter_parts = [
            "activityDisplayName eq 'Update conditional access policy'",
            "or activityDisplayName eq 'Add conditional access policy'",
            "or activityDisplayName eq 'Delete conditional access policy'"
        ]

        # Add target policy filter if available
        # Note: Graph API doesn't directly filter by policy ID in audit logs
        # We need to filter client-side

        params = {
            "$top": "500",
            "$orderBy": "activityDateTime desc",
        }

        if start_time:
            params["$filter"] = f"activityDateTime ge {start_time.isoformat()}"

        url = "https://graph.microsoft.com/v1.0/auditLogs/directoryAudits"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params
            )

            if response.status_code != 200:
                logger.warning(f"Failed to fetch audit logs: {response.status_code}")
                return []

            data = response.json()
            logs = data.get("value", [])

            # Filter for the specific policy
            policy_logs = []
            for log in logs:
                targets = log.get("targetResources", [])
                for target in targets:
                    if target.get("id") == policy_id:
                        policy_logs.append(log)
                        break

            return policy_logs

    def check_baseline_compliance(
        self,
        policy: dict[str, Any],
        baseline_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Check if a policy complies with security baseline.
        
        Args:
            policy: Policy object or analysis
            baseline_config: Baseline configuration
            
        Returns:
            Compliance check results
        """
        if isinstance(policy, dict) and "grant_controls" not in policy:
            # This is raw policy data, analyze it
            analysis = self.analyze_policy(policy)
        else:
            # Assume it's already an analysis
            analysis = policy

        compliance = {
            "is_compliant": True,
            "violations": [],
            "warnings": [],
            "recommendations": []
        }

        # Check if policy is enabled
        if analysis.get("is_disabled"):
            compliance["is_compliant"] = False
            compliance["violations"].append("Policy is disabled")

        # Check MFA requirements
        if baseline_config.get("require_mfa_for_admins") and analysis.get("includes_vip_users"):
            if not analysis.get("is_mfa_required"):
                compliance["warnings"].append("Policy affecting VIP users should require MFA")

        if baseline_config.get("require_mfa_for_all_users") and analysis.get("applies_to_all_users"):
            if not analysis.get("is_mfa_required"):
                compliance["is_compliant"] = False
                compliance["violations"].append("Policy applying to all users must require MFA")

        if baseline_config.get("require_mfa_for_guests") and analysis.get("includes_guests_or_external"):
            if not analysis.get("is_mfa_required"):
                compliance["is_compliant"] = False
                compliance["violations"].append("Policy including guests must require MFA")

        # Check legacy auth blocking
        if baseline_config.get("block_legacy_auth"):
            # This requires checking if there's a specific policy for legacy auth
            # For now, just add a recommendation
            compliance["recommendations"].append("Consider adding a policy to block legacy authentication")

        # Check device compliance
        if baseline_config.get("require_compliant_or_hybrid_joined"):
            if not analysis.get("requires_compliant_device") and not analysis.get("requires_hybrid_joined_device"):
                if analysis.get("applies_to_all_users") or analysis.get("applies_to_all_apps"):
                    compliance["warnings"].append("Broadly applied policy should require device compliance")

        # Check risk-based policies
        if baseline_config.get("block_high_risk_signins"):
            if not analysis.get("has_risk_conditions") and analysis.get("applies_to_all_users"):
                compliance["recommendations"].append("Consider adding risk-based conditions to block high-risk sign-ins")

        # Check location-based policies
        if baseline_config.get("block_unknown_locations"):
            if not analysis.get("has_location_conditions"):
                compliance["recommendations"].append("Consider adding location-based conditions to block unknown locations")

        return compliance
