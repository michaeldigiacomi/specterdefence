"""Microsoft Graph API client using MSAL."""

import asyncio
from datetime import UTC
from typing import Any

import httpx
import msal

from src.config import settings


class MSGraphClient:
    """Microsoft Graph API client."""

    def __init__(
        self, tenant_id: str, client_id: str, client_secret: str, timeout: float = 30.0
    ) -> None:
        """Initialize MSAL client.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            timeout: Request timeout in seconds
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.authority = f"{settings.MS_LOGIN_URL}/{tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]

        # Create MSAL confidential client
        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority,
        )

    async def get_access_token(self) -> str | None:
        """Get access token for Microsoft Graph API.

        Returns:
            Access token string or None if authentication fails.

        Raises:
            MSGraphAuthError: If authentication fails.
        """
        try:
            result = self.app.acquire_token_silent(self.scope, account=None)

            if not result:
                # No token in cache, fetch a new one
                result = self.app.acquire_token_for_client(scopes=self.scope)

            if "access_token" in result:
                return result["access_token"]

            # Authentication failed
            error_description = result.get("error_description", "Unknown error")
            error_code = result.get("error", "unknown_error")
            raise MSGraphAuthError(
                f"Failed to get access token: {error_description}", error_code=error_code
            )
        except MSGraphAuthError:
            # Re-raise MSGraphAuthError as-is
            raise
        except Exception as e:
            # Handle throttling or other MSAL errors
            error_msg = str(e).lower()
            if "throttle" in error_msg or "429" in error_msg:
                raise MSGraphAuthError(
                    "Authentication request throttled. Please try again later.",
                    error_code="throttled",
                ) from e
            raise MSGraphAuthError(
                f"Authentication error: {str(e)}", error_code="auth_error"
            ) from e

    async def validate_credentials(self) -> dict[str, Any]:
        """Validate credentials by fetching tenant information.

        Returns:
            Dictionary containing tenant information.

        Raises:
            MSGraphAuthError: If credentials are invalid.
            MSGraphAPIError: If API call fails.
        """
        token = await self.get_access_token()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{settings.MS_GRAPH_API_URL}/organization",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("value"):
                    org = data["value"][0]
                    return {
                        "valid": True,
                        "display_name": org.get("displayName", ""),
                        "tenant_id": org.get("id", ""),
                        "verified_domains": org.get("verifiedDomains", []),
                    }
                return {"valid": True, "display_name": "", "tenant_id": ""}
            elif response.status_code == 401:
                raise MSGraphAuthError(
                    "Invalid credentials or insufficient permissions", error_code="unauthorized"
                )
            else:
                raise MSGraphAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

    async def check_permissions(self, required_permissions: list[str]) -> dict[str, Any]:
        """Check if the app has required permissions.

        Args:
            required_permissions: List of required permission names (e.g., ["AuditLog.Read.All"])

        Returns:
            Dictionary with permission check results:
            {
                "has_permissions": bool,
                "granted_permissions": List[str],
                "missing_permissions": List[str],
                "details": Dict[str, Any]
            }

        Raises:
            MSGraphAuthError: If authentication fails.
            MSGraphAPIError: If API call fails.
        """
        token = await self.get_access_token()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Get the service principal's OAuth2 permissions
            await client.get(
                f"{settings.MS_GRAPH_API_URL}/me", headers={"Authorization": f"Bearer {token}"}
            )

            # For app-only tokens, try to check audit log access directly
            # This is the most reliable way to verify AuditLog.Read.All permission
            permission_results = {}

            for permission in required_permissions:
                if permission == "AuditLog.Read.All":
                    # Try to access audit logs - this will fail if permission is not granted
                    audit_response = await client.get(
                        f"{settings.MS_GRAPH_API_URL}/auditLogs/directoryAudits",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"$top": 1},
                    )

                    if audit_response.status_code == 200:
                        permission_results[permission] = {
                            "granted": True,
                            "test_endpoint": "/auditLogs/directoryAudits",
                            "test_result": "success",
                        }
                    elif audit_response.status_code == 403:
                        permission_results[permission] = {
                            "granted": False,
                            "test_endpoint": "/auditLogs/directoryAudits",
                            "test_result": "forbidden",
                            "error": "Permission not granted or admin consent required",
                        }
                    else:
                        permission_results[permission] = {
                            "granted": False,
                            "test_endpoint": "/auditLogs/directoryAudits",
                            "test_result": "error",
                            "error": f"HTTP {audit_response.status_code}",
                        }
                else:
                    # For other permissions, we'd need to implement specific tests
                    permission_results[permission] = {
                        "granted": "unknown",
                        "test_endpoint": None,
                        "test_result": "not_implemented",
                    }

            granted = [
                perm for perm, result in permission_results.items() if result.get("granted") is True
            ]
            missing = [
                perm
                for perm, result in permission_results.items()
                if result.get("granted") is False
            ]

            return {
                "has_permissions": len(missing) == 0,
                "granted_permissions": granted,
                "missing_permissions": missing,
                "details": permission_results,
            }

    async def health_check(self, required_permissions: list[str] | None = None) -> dict[str, Any]:
        """Perform a comprehensive health check on the tenant connection.

        Args:
            required_permissions: Optional list of permissions to verify

        Returns:
            Dictionary with health check results:
            {
                "status": "healthy" | "unhealthy" | "error" | "timeout",
                "connectivity": {"success": bool, "latency_ms": float, "error": str},
                "authentication": {"success": bool, "error": str},
                "permissions": {"success": bool, "granted": List, "missing": List},
                "tenant_info": Dict[str, Any],
                "timestamp": str
            }
        """
        import time
        from datetime import datetime

        result = {
            "status": "unknown",
            "connectivity": {"success": False, "latency_ms": 0, "error": None},
            "authentication": {"success": False, "error": None},
            "permissions": {"success": False, "granted": [], "missing": []},
            "tenant_info": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            # Test connectivity and authentication
            start_time = time.time()

            try:
                await asyncio.wait_for(self.get_access_token(), timeout=self.timeout)
                result["authentication"]["success"] = True
            except TimeoutError:
                result["status"] = "timeout"
                result["authentication"][
                    "error"
                ] = f"Authentication timed out after {self.timeout}s"
                return result
            except MSGraphAuthError as e:
                result["status"] = "error"
                result["authentication"]["error"] = str(e)
                result["authentication"]["error_code"] = getattr(e, "error_code", "unknown")
                return result

            latency_ms = (time.time() - start_time) * 1000
            result["connectivity"]["success"] = True
            result["connectivity"]["latency_ms"] = round(latency_ms, 2)

            # Get tenant info
            try:
                tenant_info = await asyncio.wait_for(self.get_tenant_info(), timeout=self.timeout)
                result["tenant_info"] = {
                    "display_name": tenant_info.get("displayName"),
                    "tenant_id": tenant_info.get("id"),
                    "verified_domains": [
                        d.get("name")
                        for d in tenant_info.get("verifiedDomains", [])
                        if d.get("isVerified")
                    ],
                }
            except TimeoutError:
                result["connectivity"][
                    "error"
                ] = f"Tenant info request timed out after {self.timeout}s"
            except Exception as e:
                result["connectivity"]["error"] = str(e)

            # Check permissions if specified
            if required_permissions:
                try:
                    perm_check = await asyncio.wait_for(
                        self.check_permissions(required_permissions), timeout=self.timeout
                    )
                    result["permissions"]["success"] = perm_check["has_permissions"]
                    result["permissions"]["granted"] = perm_check["granted_permissions"]
                    result["permissions"]["missing"] = perm_check["missing_permissions"]
                    result["permissions"]["details"] = perm_check["details"]
                except TimeoutError:
                    result["permissions"][
                        "error"
                    ] = f"Permission check timed out after {self.timeout}s"
                except Exception as e:
                    result["permissions"]["error"] = str(e)
            else:
                result["permissions"]["success"] = True  # No permissions to check

            # Determine overall status
            if result["authentication"]["success"] and result["permissions"]["success"]:
                result["status"] = "healthy"
            else:
                result["status"] = "unhealthy"

        except TimeoutError:
            result["status"] = "timeout"
            result["connectivity"]["error"] = f"Health check timed out after {self.timeout}s"
        except Exception as e:
            result["status"] = "error"
            result["connectivity"]["error"] = str(e)

        return result

    async def get_tenant_info(self) -> dict[str, Any]:
        """Get detailed tenant information.

        Returns:
            Dictionary containing tenant details.
        """
        token = await self.get_access_token()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{settings.MS_GRAPH_API_URL}/organization",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("value"):
                    return data["value"][0]

            response.raise_for_status()
            return {}


class MSGraphAuthError(Exception):
    """Raised when Microsoft Graph authentication fails."""

    def __init__(self, message: str, error_code: str = "unknown"):
        super().__init__(message)
        self.error_code = error_code


class MSGraphAPIError(Exception):
    """Raised when Microsoft Graph API call fails."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


async def validate_tenant_credentials(
    tenant_id: str, client_id: str, client_secret: str, timeout: float = 30.0
) -> dict[str, Any]:
    """Validate tenant credentials against Microsoft Graph.

    Args:
        tenant_id: Azure AD tenant ID
        client_id: Azure AD application (client) ID
        client_secret: Azure AD client secret
        timeout: Request timeout in seconds

    Returns:
        Dictionary with validation result and tenant info.
    """
    client = MSGraphClient(tenant_id, client_id, client_secret, timeout=timeout)
    return await client.validate_credentials()
