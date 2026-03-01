"""Microsoft Graph API client using MSAL."""

import httpx
from typing import Optional, Dict, Any
import msal

from src.config import settings
from src.services.encryption import encryption_service


class MSGraphClient:
    """Microsoft Graph API client."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        """Initialize MSAL client.
        
        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = f"{settings.MS_LOGIN_URL}/{tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        
        # Create MSAL confidential client
        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority,
        )

    async def get_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API.
        
        Returns:
            Access token string or None if authentication fails.
        """
        result = self.app.acquire_token_silent(self.scope, account=None)
        
        if not result:
            # No token in cache, fetch a new one
            result = self.app.acquire_token_for_client(scopes=self.scope)
        
        if "access_token" in result:
            return result["access_token"]
        
        # Authentication failed
        error_description = result.get("error_description", "Unknown error")
        raise MSGraphAuthError(f"Failed to get access token: {error_description}")

    async def validate_credentials(self) -> Dict[str, Any]:
        """Validate credentials by fetching tenant information.
        
        Returns:
            Dictionary containing tenant information.
            
        Raises:
            MSGraphAuthError: If credentials are invalid.
            MSGraphAPIError: If API call fails.
        """
        token = await self.get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.MS_GRAPH_API_URL}/organization",
                headers={"Authorization": f"Bearer {token}"}
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
                raise MSGraphAuthError("Invalid credentials or insufficient permissions")
            else:
                raise MSGraphAPIError(f"API error: {response.status_code} - {response.text}")

    async def get_tenant_info(self) -> Dict[str, Any]:
        """Get detailed tenant information.
        
        Returns:
            Dictionary containing tenant details.
        """
        token = await self.get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.MS_GRAPH_API_URL}/organization",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("value"):
                    return data["value"][0]
            
            response.raise_for_status()
            return {}


class MSGraphAuthError(Exception):
    """Raised when Microsoft Graph authentication fails."""
    pass


class MSGraphAPIError(Exception):
    """Raised when Microsoft Graph API call fails."""
    pass


async def validate_tenant_credentials(
    tenant_id: str,
    client_id: str,
    client_secret: str
) -> Dict[str, Any]:
    """Validate tenant credentials against Microsoft Graph.
    
    Args:
        tenant_id: Azure AD tenant ID
        client_id: Azure AD application (client) ID  
        client_secret: Azure AD client secret
        
    Returns:
        Dictionary with validation result and tenant info.
    """
    client = MSGraphClient(tenant_id, client_id, client_secret)
    return await client.validate_credentials()
