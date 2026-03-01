"""Microsoft Graph API client for MFA enrollment data."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from src.clients.ms_graph import MSGraphClient, MSGraphAPIError

logger = logging.getLogger(__name__)


class MFAReportClient:
    """Client for retrieving MFA enrollment data from Microsoft Graph."""
    
    # Admin role template IDs that indicate admin privileges
    ADMIN_ROLE_TEMPLATES = [
        "62e90394-69f5-4237-9190-012177145e10",  # Global Administrator
        "194ae4cb-b126-40b2-bd5b-6091b380977d",  # Security Administrator
        "f28a1f50-f6e7-4571-818b-6a12f2af6b6c",  # SharePoint Administrator
        "29232cdf-9323-42fd-ade2-1d097af3e4de",  # Exchange Administrator
        "b1be1c3e-b65d-4f19-8427-f6fa0d97feb9",  # Conditional Access Administrator
        "729827e3-9c14-49f7-bb1b-9608f156bbb8",  # Helpdesk Administrator
        "966707d0-3269-4727-9be2-8c3a10f19b9d",  # User Administrator
        "7be44c8a-adaf-4e2a-84d6-ab2649e08a13",  # Privileged Authentication Administrator
        "e8611ab8-c189-46e8-94e1-60213ab1f814",  # Privileged Role Administrator
        "05823b0b-0bb6-4f33-9e73-3e9b9c41386e",  # Application Administrator
        "9b895d92-2cd3-44c7-9d02-a6ac2d5ea5d3",  # Cloud Application Administrator
        "5d6b6bb7-de71-4623-b4af-96380a352509",  # Device Administrator
        "8ac3fc64-6eca-42ea-9e69-59f4c7b60eb2",  # Hybrid Identity Administrator
        "7698a772-787b-4ac8-901f-60d6b08affd2",  # Cloud Device Administrator
        "3edaf663-341e-4475-9f94-5c398ef6c070",  # Global Reader
        "fdd7a751-b60b-444a-984c-02652fe8fa1c",  # Groups Administrator
        "fe930be7-5e62-47db-91af-98c3a49a38b1",  # User Experience Success Manager
        "c4e39bd9-1100-46d3-8c65-fb160da0071f",  # Authentication Administrator
        "9c6df0f2-1e7c-4dc3-b195-66dfbd24aa8f",  # Password Administrator
        "f2ef992c-3afb-46b9-b7cf-a126ee74c451",  # Security Reader
        "3a2c62db-5318-420d-8d74-23affee5d9d5",  # Intune Administrator
    ]
    
    # MFA method mapping from Graph API to internal types
    MFA_METHOD_MAPPING = {
        "#microsoft.graph.fido2AuthenticationMethod": "fido2",
        "#microsoft.graph.microsoftAuthenticatorAuthenticationMethod": "microsoftAuthenticator",
        "#microsoft.graph.softwareOathAuthenticationMethod": "authenticatorApp",
        "#microsoft.graph.phoneAuthenticationMethod": "sms",
        "#microsoft.graph.emailAuthenticationMethod": "email",
        "#microsoft.graph.passwordAuthenticationMethod": "password",
        "#microsoft.graph.windowsHelloForBusinessAuthenticationMethod": "helloForBusiness",
        "#microsoft.graph.hardwareOathAuthenticationMethod": "hardwareToken",
    }
    
    def __init__(self, graph_client: MSGraphClient) -> None:
        """Initialize MFA report client.
        
        Args:
            graph_client: Initialized MSGraphClient instance
        """
        self.graph_client = graph_client
        self.timeout = graph_client.timeout
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from the tenant.
        
        Returns:
            List of user dictionaries from Microsoft Graph
        """
        token = await self.graph_client.get_access_token()
        users = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Get users with relevant fields
            url = (
                "https://graph.microsoft.com/v1.0/users"
                "?$select=id,displayName,userPrincipalName,accountEnabled,userType,"
                "signInActivity,createdDateTime"
                "&$top=999"
            )
            
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code != 200:
                    raise MSGraphAPIError(
                        f"Failed to fetch users: {response.status_code} - {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                users.extend(data.get("value", []))
                
                # Handle pagination
                url = data.get("@odata.nextLink")
        
        logger.info(f"Retrieved {len(users)} users from tenant")
        return users
    
    async def get_user_mfa_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """Get MFA methods registered for a specific user.
        
        Args:
            user_id: Microsoft Graph user ID
            
        Returns:
            List of MFA methods registered for the user
        """
        token = await self.graph_client.get_access_token()
        methods = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Query all authentication methods
            url = f"https://graph.microsoft.com/beta/users/{user_id}/authentication/methods"
            
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                methods = data.get("value", [])
            elif response.status_code == 404:
                # User not found or no methods
                logger.debug(f"No MFA methods found for user {user_id}")
                return []
            else:
                logger.warning(f"Failed to get MFA methods for user {user_id}: {response.status_code}")
                return []
        
        return methods
    
    async def get_user_directory_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get directory roles assigned to a user.
        
        Args:
            user_id: Microsoft Graph user ID
            
        Returns:
            List of directory roles assigned to the user
        """
        token = await self.graph_client.get_access_token()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/memberOf"
            
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Filter for directory roles only
                roles = [
                    item for item in data.get("value", [])
                    if item.get("@odata.type") == "#microsoft.graph.directoryRole"
                ]
                return roles
            elif response.status_code == 404:
                return []
            else:
                logger.warning(f"Failed to get directory roles for user {user_id}: {response.status_code}")
                return []
    
    async def get_user_app_role_assignments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get app role assignments for a user (indicates admin roles).
        
        Args:
            user_id: Microsoft Graph user ID
            
        Returns:
            List of app role assignments
        """
        token = await self.graph_client.get_access_token()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments"
            
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("value", [])
            else:
                logger.warning(f"Failed to get app roles for user {user_id}: {response.status_code}")
                return []
    
    def analyze_mfa_methods(self, methods: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze MFA methods to determine registration status and strength.
        
        Args:
            methods: List of MFA methods from Graph API
            
        Returns:
            Analysis results including:
            - is_mfa_registered: bool
            - mfa_methods: list of method types
            - primary_method: primary MFA method
            - strength: MFAStrengthLevel
        """
        result = {
            "is_mfa_registered": False,
            "mfa_methods": [],
            "primary_method": None,
            "strength": "none",
        }
        
        if not methods:
            return result
        
        method_types = []
        has_strong = False
        has_moderate = False
        has_weak = False
        
        for method in methods:
            method_type = method.get("@odata.type", "")
            mapped_type = self.MFA_METHOD_MAPPING.get(method_type, "unknown")
            
            # Skip password-only entries
            if mapped_type == "password":
                continue
            
            method_types.append(mapped_type)
            
            # Determine strength
            if mapped_type in ["fido2", "hardwareToken", "helloForBusiness"]:
                has_strong = True
            elif mapped_type in ["microsoftAuthenticator", "authenticatorApp"]:
                has_moderate = True
            elif mapped_type in ["sms", "voice", "email"]:
                has_weak = True
        
        # Determine overall strength (best available)
        if has_strong:
            result["strength"] = "strong"
        elif has_moderate:
            result["strength"] = "moderate"
        elif has_weak:
            result["strength"] = "weak"
        
        result["is_mfa_registered"] = len(method_types) > 0
        result["mfa_methods"] = method_types
        
        # Set primary method (prefer strongest)
        if "fido2" in method_types:
            result["primary_method"] = "fido2"
        elif "microsoftAuthenticator" in method_types:
            result["primary_method"] = "microsoftAuthenticator"
        elif "authenticatorApp" in method_types:
            result["primary_method"] = "authenticatorApp"
        elif method_types:
            result["primary_method"] = method_types[0]
        
        return result
    
    def check_admin_status(self, directory_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if user has admin privileges based on directory roles.
        
        Args:
            directory_roles: List of directory roles from Graph API
            
        Returns:
            Admin status including:
            - is_admin: bool
            - admin_roles: list of admin role names
        """
        result = {
            "is_admin": False,
            "admin_roles": [],
        }
        
        for role in directory_roles:
            role_template_id = role.get("roleTemplateId", "")
            role_name = role.get("displayName", "")
            
            if role_template_id in self.ADMIN_ROLE_TEMPLATES:
                result["is_admin"] = True
                result["admin_roles"].append(role_name)
        
        return result
    
    def parse_sign_in_activity(self, user_data: Dict[str, Any]) -> Optional[datetime]:
        """Parse sign-in activity from user data.
        
        Args:
            user_data: User data from Graph API
            
        Returns:
            Last sign-in datetime or None
        """
        sign_in_activity = user_data.get("signInActivity", {})
        last_sign_in = sign_in_activity.get("lastSignInDateTime")
        
        if last_sign_in:
            try:
                return datetime.fromisoformat(last_sign_in.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.debug(f"Failed to parse sign-in datetime: {last_sign_in}")
        
        return None
    
    async def get_full_user_mfa_data(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete MFA data for a user.
        
        Args:
            user_id: Microsoft Graph user ID
            user_data: User data from Graph API
            
        Returns:
            Complete MFA analysis for the user
        """
        # Get MFA methods
        mfa_methods = await self.get_user_mfa_methods(user_id)
        mfa_analysis = self.analyze_mfa_methods(mfa_methods)
        
        # Get admin roles
        directory_roles = await self.get_user_directory_roles(user_id)
        admin_analysis = self.check_admin_status(directory_roles)
        
        # Parse sign-in activity
        last_sign_in = self.parse_sign_in_activity(user_data)
        
        return {
            "user_id": user_id,
            "user_principal_name": user_data.get("userPrincipalName"),
            "display_name": user_data.get("displayName"),
            "account_enabled": user_data.get("accountEnabled", True),
            "user_type": user_data.get("userType", "Member"),
            "sign_in_activity": last_sign_in,
            **mfa_analysis,
            **admin_analysis,
            "raw_mfa_methods": mfa_methods,
            "raw_user_data": user_data,
        }
    
    async def scan_all_users_mfa(self, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Scan all users and their MFA status.
        
        Args:
            progress_callback: Optional callback function(progress, total)
            
        Returns:
            List of user MFA data
        """
        # Get all users
        users = await self.get_all_users()
        results = []
        
        total = len(users)
        for i, user in enumerate(users):
            try:
                user_id = user.get("id")
                if not user_id:
                    continue
                
                mfa_data = await self.get_full_user_mfa_data(user_id, user)
                results.append(mfa_data)
                
                # Report progress
                if progress_callback:
                    progress_callback(i + 1, total)
                    
            except Exception as e:
                logger.error(f"Error processing user {user.get('userPrincipalName')}: {e}")
                continue
        
        logger.info(f"Completed MFA scan for {len(results)} users")
        return results
