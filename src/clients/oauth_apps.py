"""Microsoft Graph client for OAuth applications operations."""

import logging
from typing import Any

import httpx

from src.clients.ms_graph import MSGraphAPIError, MSGraphClient

logger = logging.getLogger(__name__)


class OAuthAppsClient:
    """Client for fetching and managing OAuth applications via Microsoft Graph API."""

    # High-risk permission patterns
    HIGH_RISK_PERMISSIONS = {
        # Mail access
        "Mail.Read": {"risk": "high", "category": "mail"},
        "Mail.ReadWrite": {"risk": "high", "category": "mail"},
        "Mail.Send": {"risk": "high", "category": "mail"},
        "Mail.Read.Shared": {"risk": "high", "category": "mail"},
        "Mail.ReadWrite.Shared": {"risk": "high", "category": "mail"},
        "MailboxSettings.Read": {"risk": "medium", "category": "mail"},
        "MailboxSettings.ReadWrite": {"risk": "high", "category": "mail"},
        "Exchange.ManageAsApp": {"risk": "critical", "category": "mail"},

        # User access
        "User.Read.All": {"risk": "high", "category": "user"},
        "User.ReadWrite.All": {"risk": "critical", "category": "user"},
        "User.Export.All": {"risk": "critical", "category": "user"},
        "Directory.Read.All": {"risk": "high", "category": "user"},
        "Directory.ReadWrite.All": {"risk": "critical", "category": "user"},

        # Group access
        "Group.Read.All": {"risk": "medium", "category": "group"},
        "Group.ReadWrite.All": {"risk": "high", "category": "group"},
        "GroupMember.Read.All": {"risk": "medium", "category": "group"},
        "GroupMember.ReadWrite.All": {"risk": "high", "category": "group"},

        # Files access
        "Files.Read.All": {"risk": "high", "category": "files"},
        "Files.ReadWrite.All": {"risk": "critical", "category": "files"},
        "Sites.Read.All": {"risk": "high", "category": "files"},
        "Sites.ReadWrite.All": {"risk": "critical", "category": "files"},
        "Sites.FullControl.All": {"risk": "critical", "category": "files"},

        # Calendar access
        "Calendars.Read": {"risk": "medium", "category": "calendar"},
        "Calendars.ReadWrite": {"risk": "high", "category": "calendar"},
        "Calendars.Read.Shared": {"risk": "medium", "category": "calendar"},

        # Admin/Role access
        "RoleManagement.Read.Directory": {"risk": "high", "category": "admin"},
        "RoleManagement.ReadWrite.Directory": {"risk": "critical", "category": "admin"},
        "AppRoleAssignment.ReadWrite.All": {"risk": "critical", "category": "admin"},
        "Application.ReadWrite.All": {"risk": "critical", "category": "admin"},
        "Policy.Read.All": {"risk": "medium", "category": "admin"},
        "Policy.ReadWrite.ConditionalAccess": {"risk": "critical", "category": "admin"},

        # Device access
        "Device.Read.All": {"risk": "medium", "category": "device"},
        "Device.ReadWrite.All": {"risk": "high", "category": "device"},
        "DeviceManagementManagedDevices.Read.All": {"risk": "high", "category": "device"},
        "DeviceManagementManagedDevices.ReadWrite.All": {"risk": "critical", "category": "device"},

        # Security/Reports
        "SecurityEvents.Read.All": {"risk": "high", "category": "security"},
        "SecurityEvents.ReadWrite.All": {"risk": "critical", "category": "security"},
        "AuditLog.Read.All": {"risk": "high", "category": "security"},
        "Reports.Read.All": {"risk": "medium", "category": "security"},
    }

    def __init__(self, graph_client: MSGraphClient) -> None:
        """Initialize with existing MS Graph client.

        Args:
            graph_client: Authenticated MSGraphClient instance
        """
        self.graph_client = graph_client

    async def get_oauth_apps(self) -> list[dict[str, Any]]:
        """Get all OAuth applications registered in the tenant.

        Returns:
            List of application objects
        """
        token = await self.graph_client.get_access_token()

        apps = []
        url = "https://graph.microsoft.com/v1.0/applications"
        params = {
            "$select": "id,appId,displayName,description,createdDateTime,publisherDomain,verifiedPublisher",
            "$top": "999",
        }

        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if url == "https://graph.microsoft.com/v1.0/applications" else None
                )

                if response.status_code != 200:
                    raise MSGraphAPIError(f"Failed to fetch applications: {response.status_code}")

                data = response.json()
                apps.extend(data.get("value", []))

                # Handle pagination
                url = data.get("@odata.nextLink")
                params = None

        return apps

    async def get_service_principals(self) -> list[dict[str, Any]]:
        """Get all service principals (enterprise apps) in the tenant.

        Returns:
            List of service principal objects
        """
        token = await self.graph_client.get_access_token()

        service_principals = []
        url = "https://graph.microsoft.com/v1.0/servicePrincipals"
        params = {
            "$select": "id,appId,displayName,description,createdDateTime,publisherName,verifiedPublisher,appRoles,oauth2PermissionScopes,signInAudience",
            "$top": "999",
        }

        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if url == "https://graph.microsoft.com/v1.0/servicePrincipals" else None
                )

                if response.status_code != 200:
                    raise MSGraphAPIError(f"Failed to fetch service principals: {response.status_code}")

                data = response.json()
                service_principals.extend(data.get("value", []))

                # Handle pagination
                url = data.get("@odata.nextLink")
                params = None

        return service_principals

    async def get_app_permissions(self, app_id: str) -> list[dict[str, Any]]:
        """Get permissions granted to an application.

        Args:
            app_id: The service principal ID

        Returns:
            List of permission grant objects
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_id}/appRoleAssignments"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 404:
                return []

            if response.status_code != 200:
                logger.warning(f"Failed to fetch permissions for {app_id}: {response.status_code}")
                return []

            data = response.json()
            return data.get("value", [])

    async def get_oauth_permission_grants(self, app_id: str) -> list[dict[str, Any]]:
        """Get OAuth2 permission grants for a service principal.

        Args:
            app_id: The service principal ID

        Returns:
            List of OAuth2 permission grant objects
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_id}/oauth2PermissionGrants"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 404:
                return []

            if response.status_code != 200:
                logger.warning(f"Failed to fetch OAuth grants for {app_id}: {response.status_code}")
                return []

            data = response.json()
            return data.get("value", [])

    async def get_user_consents(self) -> list[dict[str, Any]]:
        """Get all OAuth2 permission grants (user consents) in the tenant.

        Returns:
            List of OAuth2 permission grant objects with user info
        """
        token = await self.graph_client.get_access_token()

        consents = []
        url = "https://graph.microsoft.com/v1.0/oauth2PermissionGrants"
        params = {
            "$expand": "clientAppId,resourceAppId",
            "$top": "999",
        }

        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if url == "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" else None
                )

                if response.status_code != 200:
                    raise MSGraphAPIError(f"Failed to fetch OAuth grants: {response.status_code}")

                data = response.json()
                consents.extend(data.get("value", []))

                # Handle pagination
                url = data.get("@odata.nextLink")
                params = None

        return consents

    async def revoke_app_consent(self, grant_id: str) -> bool:
        """Revoke an OAuth2 permission grant.

        Args:
            grant_id: The ID of the OAuth2 permission grant to revoke

        Returns:
            True if successful
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/v1.0/oauth2PermissionGrants/{grant_id}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            return response.status_code == 204

    async def disable_service_principal(self, app_id: str) -> bool:
        """Disable a service principal (enterprise app).

        Args:
            app_id: The service principal ID

        Returns:
            True if successful
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_id}"

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"accountEnabled": False}
            )

            return response.status_code == 204

    async def delete_service_principal(self, app_id: str) -> bool:
        """Delete a service principal (enterprise app).

        Args:
            app_id: The service principal ID

        Returns:
            True if successful
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_id}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            return response.status_code == 204

    def analyze_permissions(self, permissions: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze permissions for risk assessment.

        Args:
            permissions: List of permission objects

        Returns:
            Analysis results with risk flags
        """
        analysis = {
            "total_permissions": len(permissions),
            "high_risk_permissions": [],
            "medium_risk_permissions": [],
            "risk_categories": set(),
            "has_mail_permissions": False,
            "has_user_read_all": False,
            "has_group_read_all": False,
            "has_files_read_all": False,
            "has_calendar_access": False,
            "has_admin_permissions": False,
            "risk_score": 0,
            "detection_reasons": [],
        }

        for perm in permissions:
            # Get permission value from various possible fields
            perm_value = perm.get("value") or perm.get("appRoleId") or perm.get("principalDisplayName", "")
            if not perm_value:
                continue

            # Check against high-risk permissions
            if perm_value in self.HIGH_RISK_PERMISSIONS:
                risk_info = self.HIGH_RISK_PERMISSIONS[perm_value]

                perm_analysis = {
                    "value": perm_value,
                    "risk": risk_info["risk"],
                    "category": risk_info["category"],
                }

                if risk_info["risk"] in ["high", "critical"]:
                    analysis["high_risk_permissions"].append(perm_analysis)
                elif risk_info["risk"] == "medium":
                    analysis["medium_risk_permissions"].append(perm_analysis)

                analysis["risk_categories"].add(risk_info["category"])

                # Add to detection reasons
                if risk_info["risk"] == "critical":
                    analysis["detection_reasons"].append(f"Critical permission: {perm_value}")
                elif risk_info["risk"] == "high":
                    analysis["detection_reasons"].append(f"High-risk permission: {perm_value}")

                # Update specific flags
                if risk_info["category"] == "mail":
                    analysis["has_mail_permissions"] = True
                if perm_value == "User.Read.All":
                    analysis["has_user_read_all"] = True
                if perm_value == "Group.Read.All":
                    analysis["has_group_read_all"] = True
                if perm_value == "Files.Read.All":
                    analysis["has_files_read_all"] = True
                if risk_info["category"] == "calendar":
                    analysis["has_calendar_access"] = True
                if risk_info["category"] == "admin":
                    analysis["has_admin_permissions"] = True

                # Add to risk score
                if risk_info["risk"] == "critical":
                    analysis["risk_score"] += 25
                elif risk_info["risk"] == "high":
                    analysis["risk_score"] += 15
                elif risk_info["risk"] == "medium":
                    analysis["risk_score"] += 5

        # Cap risk score at 100
        analysis["risk_score"] = min(analysis["risk_score"], 100)
        analysis["risk_categories"] = list(analysis["risk_categories"])

        return analysis

    def analyze_app(self, app: dict[str, Any], permissions_analysis: dict[str, Any]) -> dict[str, Any]:
        """Analyze an OAuth application for risk factors.

        Args:
            app: Application object from Graph API
            permissions_analysis: Results from analyze_permissions

        Returns:
            Analysis results with risk level and status
        """
        analysis = {
            "risk_level": "LOW",
            "status": "pending_review",
            "publisher_type": "unknown",
            "is_microsoft_publisher": False,
            "is_verified_publisher": False,
            "detection_reasons": permissions_analysis.get("detection_reasons", []).copy(),
        }

        # Analyze publisher
        verified_publisher = app.get("verifiedPublisher", {})
        publisher_name = app.get("publisherName", "")

        if verified_publisher and verified_publisher.get("verifiedPublisherId"):
            analysis["is_verified_publisher"] = True
            analysis["publisher_type"] = "verified"
        elif publisher_name and "microsoft" in publisher_name.lower():
            analysis["is_microsoft_publisher"] = True
            analysis["publisher_type"] = "microsoft"
        elif publisher_name:
            analysis["publisher_type"] = "unverified"
            analysis["detection_reasons"].append(f"Unverified publisher: {publisher_name}")
        else:
            analysis["detection_reasons"].append("Unknown publisher")

        # Calculate risk level
        risk_score = permissions_analysis.get("risk_score", 0)

        # Increase risk for unverified publishers with high-risk permissions
        if not analysis["is_microsoft_publisher"] and not analysis["is_verified_publisher"]:
            if permissions_analysis.get("has_mail_permissions"):
                risk_score += 20
                analysis["detection_reasons"].append("Mail access by unverified publisher")
            if permissions_analysis.get("has_user_read_all"):
                risk_score += 15
                analysis["detection_reasons"].append("User directory access by unverified publisher")

        # Determine risk level based on score
        if risk_score >= 60:
            analysis["risk_level"] = "CRITICAL"
            analysis["status"] = "malicious"
        elif risk_score >= 40:
            analysis["risk_level"] = "HIGH"
            analysis["status"] = "suspicious"
        elif risk_score >= 20:
            analysis["risk_level"] = "MEDIUM"
            analysis["status"] = "suspicious"
        else:
            analysis["risk_level"] = "LOW"
            analysis["status"] = "approved"

        analysis["risk_score"] = min(risk_score, 100)

        return analysis

    async def get_app_with_consents(self, app_id: str) -> dict[str, Any]:
        """Get detailed information about an app including consents.

        Args:
            app_id: The service principal app ID

        Returns:
            Dictionary with app details, permissions, and consents
        """
        token = await self.graph_client.get_access_token()

        # Get service principal details
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals(appId='{app_id}')"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code != 200:
                raise MSGraphAPIError(f"Failed to fetch app: {response.status_code}")

            app_data = response.json()
            sp_id = app_data.get("id")

            # Get permissions and consents
            permissions = await self.get_app_permissions(sp_id)
            consents = await self.get_oauth_permission_grants(sp_id)

            return {
                "app": app_data,
                "permissions": permissions,
                "consents": consents,
            }
