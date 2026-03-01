"""Office 365 API client for Microsoft Graph interactions."""

import httpx
from typing import Optional, Dict, Any

class O365Client:
    """Client for Microsoft Graph API interactions."""
    
    BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.client = httpx.AsyncClient(base_url=self.BASE_URL)
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to Microsoft Graph."""
        response = await self.client.get(
            endpoint,
            params=params,
            headers=await self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
