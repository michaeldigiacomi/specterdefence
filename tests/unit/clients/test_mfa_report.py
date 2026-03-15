"""Unit tests for MFA report client."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.mfa_report import MFAReportClient
from src.clients.ms_graph import MSGraphAPIError, MSGraphClient


class TestMFAReportClient:
    """Test cases for MFAReportClient."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock MS Graph client."""
        client = AsyncMock(spec=MSGraphClient)
        client.get_access_token = AsyncMock(return_value="test-token")
        client.timeout = 30.0
        return client

    @pytest.fixture
    def mfa_client(self, mock_graph_client):
        """Create an MFAReportClient instance."""
        return MFAReportClient(mock_graph_client)

    @pytest.fixture
    def sample_user(self):
        """Return a sample user from Graph API."""
        return {
            "id": "user-123",
            "displayName": "John Doe",
            "userPrincipalName": "john.doe@example.com",
            "accountEnabled": True,
            "userType": "Member",
            "signInActivity": {
                "lastSignInDateTime": "2024-01-15T10:30:00Z",
            },
            "createdDateTime": "2023-01-01T00:00:00Z",
        }

    @pytest.fixture
    def sample_mfa_methods(self):
        """Return sample MFA methods."""
        return [
            {
                "@odata.type": "#microsoft.graph.microsoftAuthenticatorAuthenticationMethod",
                "id": "auth-method-1",
                "displayName": "Microsoft Authenticator",
                "createdDateTime": "2024-01-10T10:00:00Z",
            },
            {
                "@odata.type": "#microsoft.graph.phoneAuthenticationMethod",
                "id": "auth-method-2",
                "phoneType": "mobile",
                "phoneNumber": "+1234567890",
            },
        ]

    @pytest.fixture
    def sample_admin_roles(self):
        """Return sample admin directory roles."""
        return [
            {
                "@odata.type": "#microsoft.graph.directoryRole",
                "id": "role-1",
                "roleTemplateId": "62e90394-69f5-4237-9190-012177145e10",  # Global Administrator
                "displayName": "Global Administrator",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_all_users_success(self, mfa_client, mock_graph_client):
        """Test successful retrieval of all users."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "user-1", "displayName": "User 1", "userPrincipalName": "user1@example.com"},
                {"id": "user-2", "displayName": "User 2", "userPrincipalName": "user2@example.com"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await mfa_client.get_all_users()

        assert len(result) == 2
        assert result[0]["displayName"] == "User 1"
        mock_graph_client.get_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_users_pagination(self, mfa_client, mock_graph_client):
        """Test user retrieval with pagination."""
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "value": [{"id": "user-1", "displayName": "User 1"}],
            "@odata.nextLink": "https://next.page",
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "value": [{"id": "user-2", "displayName": "User 2"}],
        }

        with patch("httpx.AsyncClient.get", side_effect=[mock_response1, mock_response2]):
            result = await mfa_client.get_all_users()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_users_error(self, mfa_client, mock_graph_client):
        """Test error handling for user retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises(MSGraphAPIError, match="Failed to fetch users"):
                await mfa_client.get_all_users()

    @pytest.mark.asyncio
    async def test_get_user_mfa_methods_success(
        self, mfa_client, mock_graph_client, sample_mfa_methods
    ):
        """Test successful retrieval of user MFA methods."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": sample_mfa_methods}

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await mfa_client.get_user_mfa_methods("user-123")

        assert len(result) == 2
        assert (
            result[0]["@odata.type"]
            == "#microsoft.graph.microsoftAuthenticatorAuthenticationMethod"
        )

    @pytest.mark.asyncio
    async def test_get_user_mfa_methods_not_found(self, mfa_client, mock_graph_client):
        """Test handling of 404 for MFA methods."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await mfa_client.get_user_mfa_methods("user-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_directory_roles_success(
        self, mfa_client, mock_graph_client, sample_admin_roles
    ):
        """Test successful retrieval of user directory roles."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                *sample_admin_roles,
                {
                    "@odata.type": "#microsoft.graph.group",
                    "id": "group-1",
                    "displayName": "Regular Group",
                },
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await mfa_client.get_user_directory_roles("user-123")

        assert len(result) == 1  # Only directory roles, not groups
        assert result[0]["displayName"] == "Global Administrator"

    @pytest.mark.asyncio
    async def test_get_user_app_role_assignments_success(self, mfa_client, mock_graph_client):
        """Test successful retrieval of app role assignments."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "assignment-1", "principalDisplayName": "App Role 1"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await mfa_client.get_user_app_role_assignments("user-123")

        assert len(result) == 1

    def test_analyze_mfa_methods_with_mfa(self, mfa_client, sample_mfa_methods):
        """Test MFA method analysis with registered methods."""
        result = mfa_client.analyze_mfa_methods(sample_mfa_methods)

        assert result["is_mfa_registered"] is True
        assert "microsoftAuthenticator" in result["mfa_methods"]
        assert "sms" in result["mfa_methods"]  # phone maps to sms
        assert result["primary_method"] == "microsoftAuthenticator"
        assert result["strength"] == "moderate"  # Authenticator is moderate

    def test_analyze_mfa_methods_strong_only(self, mfa_client):
        """Test MFA method analysis with only strong methods."""
        methods = [
            {"@odata.type": "#microsoft.graph.fido2AuthenticationMethod", "id": "fido2-1"},
        ]

        result = mfa_client.analyze_mfa_methods(methods)

        assert result["is_mfa_registered"] is True
        assert "fido2" in result["mfa_methods"]
        assert result["strength"] == "strong"
        assert result["primary_method"] == "fido2"

    def test_analyze_mfa_methods_weak_only(self, mfa_client):
        """Test MFA method analysis with only weak methods."""
        methods = [
            {
                "@odata.type": "#microsoft.graph.phoneAuthenticationMethod",
                "id": "phone-1",
                "phoneType": "mobile",
            },
            {"@odata.type": "#microsoft.graph.emailAuthenticationMethod", "id": "email-1"},
        ]

        result = mfa_client.analyze_mfa_methods(methods)

        assert result["is_mfa_registered"] is True
        assert result["strength"] == "weak"

    def test_analyze_mfa_methods_no_mfa(self, mfa_client):
        """Test MFA method analysis with no methods."""
        result = mfa_client.analyze_mfa_methods([])

        assert result["is_mfa_registered"] is False
        assert result["mfa_methods"] == []
        assert result["strength"] == "none"
        assert result["primary_method"] is None

    def test_analyze_mfa_methods_password_only(self, mfa_client):
        """Test MFA method analysis with only password (not MFA)."""
        methods = [
            {"@odata.type": "#microsoft.graph.passwordAuthenticationMethod", "id": "pwd-1"},
        ]

        result = mfa_client.analyze_mfa_methods(methods)

        # Password-only should not count as MFA registered
        assert result["is_mfa_registered"] is False

    def test_check_admin_status_with_admin_role(self, mfa_client, sample_admin_roles):
        """Test admin status check with admin role."""
        result = mfa_client.check_admin_status(sample_admin_roles)

        assert result["is_admin"] is True
        assert "Global Administrator" in result["admin_roles"]

    def test_check_admin_status_no_admin(self, mfa_client):
        """Test admin status check with no admin roles."""
        roles = [
            {
                "@odata.type": "#microsoft.graph.directoryRole",
                "id": "role-1",
                "roleTemplateId": "non-admin-template-id",
                "displayName": "Regular Role",
            },
        ]

        result = mfa_client.check_admin_status(roles)

        assert result["is_admin"] is False
        assert result["admin_roles"] == []

    def test_check_admin_status_empty_roles(self, mfa_client):
        """Test admin status check with empty roles."""
        result = mfa_client.check_admin_status([])

        assert result["is_admin"] is False
        assert result["admin_roles"] == []

    def test_parse_sign_in_activity_valid(self, mfa_client):
        """Test parsing valid sign-in activity."""
        user_data = {
            "signInActivity": {
                "lastSignInDateTime": "2024-01-15T10:30:00Z",
            }
        }

        result = mfa_client.parse_sign_in_activity(user_data)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_sign_in_activity_missing(self, mfa_client):
        """Test parsing missing sign-in activity."""
        user_data = {}

        result = mfa_client.parse_sign_in_activity(user_data)

        assert result is None

    def test_parse_sign_in_activity_invalid(self, mfa_client):
        """Test parsing invalid sign-in activity."""
        user_data = {
            "signInActivity": {
                "lastSignInDateTime": "invalid-date",
            }
        }

        result = mfa_client.parse_sign_in_activity(user_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_full_user_mfa_data(
        self, mfa_client, mock_graph_client, sample_user, sample_mfa_methods, sample_admin_roles
    ):
        """Test getting complete MFA data for a user."""
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {"value": sample_mfa_methods}

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"value": sample_admin_roles}

        with patch("httpx.AsyncClient.get", side_effect=[mock_response1, mock_response2]):
            result = await mfa_client.get_full_user_mfa_data("user-123", sample_user)

        assert result["user_id"] == "user-123"
        assert result["user_principal_name"] == "john.doe@example.com"
        assert result["is_mfa_registered"] is True
        assert result["is_admin"] is True
        assert "Global Administrator" in result["admin_roles"]

    @pytest.mark.asyncio
    async def test_scan_all_users_mfa(self, mfa_client, mock_graph_client):
        """Test scanning all users for MFA."""
        # Mock get_all_users
        users = [
            {
                "id": "user-1",
                "displayName": "User 1",
                "userPrincipalName": "user1@example.com",
                "accountEnabled": True,
            },
            {
                "id": "user-2",
                "displayName": "User 2",
                "userPrincipalName": "user2@example.com",
                "accountEnabled": True,
            },
        ]

        with patch.object(mfa_client, "get_all_users", return_value=users):
            with patch.object(
                mfa_client,
                "get_full_user_mfa_data",
                return_value={
                    "user_id": "user-1",
                    "is_mfa_registered": True,
                    "is_admin": False,
                },
            ):
                result = await mfa_client.scan_all_users_mfa()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_scan_all_users_mfa_with_progress(self, mfa_client, mock_graph_client):
        """Test scanning all users with progress callback."""
        users = [
            {"id": "user-1", "displayName": "User 1", "userPrincipalName": "user1@example.com"},
        ]

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        with patch.object(mfa_client, "get_all_users", return_value=users):
            with patch.object(
                mfa_client,
                "get_full_user_mfa_data",
                return_value={
                    "user_id": "user-1",
                    "is_mfa_registered": True,
                },
            ):
                await mfa_client.scan_all_users_mfa(progress_callback=progress_callback)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1)

    def test_admin_role_templates_defined(self, mfa_client):
        """Test that admin role templates are defined."""
        assert len(mfa_client.ADMIN_ROLE_TEMPLATES) > 0
        # Check for Global Administrator
        assert "62e90394-69f5-4237-9190-012177145e10" in mfa_client.ADMIN_ROLE_TEMPLATES
        # Check for Security Administrator
        assert "194ae4cb-b126-40b2-bd5b-6091b380977d" in mfa_client.ADMIN_ROLE_TEMPLATES

    def test_mfa_method_mapping(self, mfa_client):
        """Test MFA method type mapping."""
        assert (
            mfa_client.MFA_METHOD_MAPPING["#microsoft.graph.fido2AuthenticationMethod"] == "fido2"
        )
        assert (
            mfa_client.MFA_METHOD_MAPPING[
                "#microsoft.graph.microsoftAuthenticatorAuthenticationMethod"
            ]
            == "microsoftAuthenticator"
        )
        assert mfa_client.MFA_METHOD_MAPPING["#microsoft.graph.phoneAuthenticationMethod"] == "sms"
        assert (
            mfa_client.MFA_METHOD_MAPPING["#microsoft.graph.passwordAuthenticationMethod"]
            == "password"
        )
