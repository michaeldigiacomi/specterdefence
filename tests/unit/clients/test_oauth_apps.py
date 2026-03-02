"""Unit tests for OAuth apps client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.ms_graph import MSGraphClient
from src.clients.oauth_apps import MSGraphAPIError, OAuthAppsClient


class TestOAuthAppsClient:
    """Test cases for OAuthAppsClient."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock MS Graph client."""
        client = AsyncMock(spec=MSGraphClient)
        client.get_access_token = AsyncMock(return_value="test-token")
        return client

    @pytest.fixture
    def oauth_client(self, mock_graph_client):
        """Create an OAuthAppsClient instance."""
        return OAuthAppsClient(mock_graph_client)

    @pytest.fixture
    def sample_service_principal(self):
        """Return a sample service principal."""
        return {
            "id": "sp-123",
            "appId": "app-123",
            "displayName": "Test App",
            "description": "A test application",
            "createdDateTime": "2024-01-15T10:30:00Z",
            "publisherName": "Test Publisher",
            "verifiedPublisher": {
                "verifiedPublisherId": "pub-123",
                "displayName": "Verified Publisher"
            },
        }

    @pytest.fixture
    def sample_permissions(self):
        """Return sample app permissions."""
        return [
            {"value": "Mail.Read", "appRoleId": "role-1"},
            {"value": "User.Read.All", "appRoleId": "role-2"},
            {"value": "Calendars.Read", "appRoleId": "role-3"},
        ]

    @pytest.mark.asyncio
    async def test_get_service_principals_success(self, oauth_client, mock_graph_client):
        """Test successful retrieval of service principals."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "sp-1", "appId": "app-1", "displayName": "App 1"},
                {"id": "sp-2", "appId": "app-2", "displayName": "App 2"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await oauth_client.get_service_principals()

        assert len(result) == 2
        assert result[0]["displayName"] == "App 1"
        mock_graph_client.get_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_service_principals_pagination(self, oauth_client, mock_graph_client):
        """Test service principal pagination."""
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "value": [{"id": "sp-1", "appId": "app-1", "displayName": "App 1"}],
            "@odata.nextLink": "https://next.page"
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "value": [{"id": "sp-2", "appId": "app-2", "displayName": "App 2"}],
        }

        with patch("httpx.AsyncClient.get", side_effect=[mock_response1, mock_response2]):
            result = await oauth_client.get_service_principals()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_service_principals_error(self, oauth_client, mock_graph_client):
        """Test error handling for service principals."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises(MSGraphAPIError, match="Failed to fetch service principals"):
                await oauth_client.get_service_principals()

    @pytest.mark.asyncio
    async def test_get_app_permissions_success(self, oauth_client, mock_graph_client):
        """Test successful retrieval of app permissions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"value": "Mail.Read", "appRoleId": "role-1"},
                {"value": "User.Read.All", "appRoleId": "role-2"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await oauth_client.get_app_permissions("sp-123")

        assert len(result) == 2
        assert result[0]["value"] == "Mail.Read"

    @pytest.mark.asyncio
    async def test_get_app_permissions_not_found(self, oauth_client, mock_graph_client):
        """Test handling of 404 for app permissions."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await oauth_client.get_app_permissions("sp-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_oauth_permission_grants_success(self, oauth_client, mock_graph_client):
        """Test successful retrieval of OAuth grants."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "grant-1", "scope": "Mail.Read", "consentType": "Principal"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await oauth_client.get_oauth_permission_grants("sp-123")

        assert len(result) == 1
        assert result[0]["scope"] == "Mail.Read"

    @pytest.mark.asyncio
    async def test_get_user_consents_success(self, oauth_client, mock_graph_client):
        """Test successful retrieval of user consents."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "consent-1", "scope": "Mail.Read", "principalId": "user-1"},
                {"id": "consent-2", "scope": "User.Read", "principalId": "user-2"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await oauth_client.get_user_consents()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_revoke_app_consent_success(self, oauth_client, mock_graph_client):
        """Test successful revocation of app consent."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch("httpx.AsyncClient.delete", return_value=mock_response):
            result = await oauth_client.revoke_app_consent("grant-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_app_consent_failure(self, oauth_client, mock_graph_client):
        """Test failed revocation of app consent."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("httpx.AsyncClient.delete", return_value=mock_response):
            result = await oauth_client.revoke_app_consent("grant-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_disable_service_principal_success(self, oauth_client, mock_graph_client):
        """Test successful disabling of service principal."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch("httpx.AsyncClient.patch", return_value=mock_response):
            result = await oauth_client.disable_service_principal("sp-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_service_principal_success(self, oauth_client, mock_graph_client):
        """Test successful deletion of service principal."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch("httpx.AsyncClient.delete", return_value=mock_response):
            result = await oauth_client.delete_service_principal("sp-123")

        assert result is True

    def test_analyze_permissions_high_risk(self, oauth_client, sample_permissions):
        """Test permission analysis with high-risk permissions."""
        result = oauth_client.analyze_permissions(sample_permissions)

        assert result["total_permissions"] == 3
        assert result["has_mail_permissions"] is True
        assert result["has_user_read_all"] is True
        assert result["has_calendar_access"] is True
        assert len(result["high_risk_permissions"]) == 2  # Mail.Read and User.Read.All
        assert result["risk_score"] > 0
        assert len(result["detection_reasons"]) > 0

    def test_analyze_permissions_no_risk(self, oauth_client):
        """Test permission analysis with no high-risk permissions."""
        permissions = [
            {"value": "User.Read", "appRoleId": "role-1"},
            {"value": "Profile.Read", "appRoleId": "role-2"},
        ]

        result = oauth_client.analyze_permissions(permissions)

        assert result["total_permissions"] == 2
        assert result["has_mail_permissions"] is False
        assert result["has_user_read_all"] is False
        assert len(result["high_risk_permissions"]) == 0
        assert result["risk_score"] == 0

    def test_analyze_permissions_critical_risk(self, oauth_client):
        """Test permission analysis with critical-risk permissions."""
        permissions = [
            {"value": "User.ReadWrite.All", "appRoleId": "role-1"},
            {"value": "Files.ReadWrite.All", "appRoleId": "role-2"},
        ]

        result = oauth_client.analyze_permissions(permissions)

        assert result["risk_score"] >= 50  # Critical permissions add 25 each
        assert "admin" in result["risk_categories"] or "files" in result["risk_categories"]

    def test_analyze_app_microsoft_publisher(self, oauth_client, sample_service_principal):
        """Test app analysis with Microsoft publisher."""
        app = sample_service_principal.copy()
        app["publisherName"] = "Microsoft Corporation"
        app["verifiedPublisher"] = {}

        perm_analysis = {
            "total_permissions": 2,
            "high_risk_permissions": [],
            "risk_score": 0,
            "has_mail_permissions": False,
            "detection_reasons": [],
        }

        result = oauth_client.analyze_app(app, perm_analysis)

        assert result["is_microsoft_publisher"] is True
        assert result["publisher_type"] == "microsoft"
        assert result["risk_level"] == "LOW"
        assert result["status"] == "approved"

    def test_analyze_app_unverified_publisher_high_risk(self, oauth_client, sample_service_principal):
        """Test app analysis with unverified publisher and high-risk permissions."""
        app = sample_service_principal.copy()
        app["publisherName"] = "Unknown Publisher"
        app["verifiedPublisher"] = {}

        perm_analysis = {
            "total_permissions": 3,
            "high_risk_permissions": [{"value": "Mail.Read", "risk": "high", "category": "mail"}],
            "risk_score": 25,  # Higher base score to trigger HIGH risk
            "has_mail_permissions": True,
            "detection_reasons": ["High-risk permission: Mail.Read"],
        }

        result = oauth_client.analyze_app(app, perm_analysis)

        assert result["is_microsoft_publisher"] is False
        assert result["is_verified_publisher"] is False
        assert result["publisher_type"] == "unverified"
        assert result["risk_level"] in ["HIGH", "CRITICAL"]
        assert result["status"] in ["suspicious", "malicious"]
        assert any("unverified publisher" in reason.lower() for reason in result["detection_reasons"])

    def test_analyze_app_verified_publisher(self, oauth_client, sample_service_principal):
        """Test app analysis with verified publisher."""
        app = sample_service_principal.copy()
        app["publisherName"] = "Some Vendor"

        perm_analysis = {
            "total_permissions": 2,
            "high_risk_permissions": [],
            "risk_score": 0,
            "has_mail_permissions": False,
            "detection_reasons": [],
        }

        result = oauth_client.analyze_app(app, perm_analysis)

        assert result["is_verified_publisher"] is True
        assert result["publisher_type"] == "verified"

    def test_analyze_app_unknown_publisher(self, oauth_client):
        """Test app analysis with unknown publisher."""
        app = {
            "id": "sp-123",
            "appId": "app-123",
            "displayName": "Unknown App",
            "publisherName": None,
            "verifiedPublisher": {},
        }

        perm_analysis = {
            "total_permissions": 1,
            "high_risk_permissions": [],
            "risk_score": 0,
            "has_mail_permissions": False,
            "detection_reasons": [],
        }

        result = oauth_client.analyze_app(app, perm_analysis)

        assert result["publisher_type"] == "unknown"
        assert any("unknown publisher" in reason.lower() for reason in result["detection_reasons"])

    @pytest.mark.asyncio
    async def test_get_app_with_consents_success(self, oauth_client, mock_graph_client):
        """Test successful retrieval of app with consents."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "sp-123",
            "appId": "app-123",
            "displayName": "Test App",
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with patch.object(oauth_client, "get_app_permissions", return_value=[{"value": "Mail.Read"}]):
                with patch.object(oauth_client, "get_oauth_permission_grants", return_value=[{"scope": "Mail.Read"}]):
                    result = await oauth_client.get_app_with_consents("app-123")

        assert "app" in result
        assert "permissions" in result
        assert "consents" in result
        assert result["app"]["displayName"] == "Test App"

    @pytest.mark.asyncio
    async def test_get_app_with_consents_error(self, oauth_client, mock_graph_client):
        """Test error handling for get_app_with_consents."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises(MSGraphAPIError, match="Failed to fetch app"):
                await oauth_client.get_app_with_consents("app-123")

    def test_high_risk_permissions_list_comprehensive(self, oauth_client):
        """Test that HIGH_RISK_PERMISSIONS contains expected permissions."""
        expected_permissions = [
            "Mail.Read",
            "Mail.ReadWrite",
            "User.Read.All",
            "User.ReadWrite.All",
            "Files.Read.All",
            "Files.ReadWrite.All",
            "Group.Read.All",
            "Group.ReadWrite.All",
        ]

        for perm in expected_permissions:
            assert perm in oauth_client.HIGH_RISK_PERMISSIONS, f"Missing permission: {perm}"

    def test_high_risk_permissions_categories(self, oauth_client):
        """Test that HIGH_RISK_PERMISSIONS has correct categories."""
        assert oauth_client.HIGH_RISK_PERMISSIONS["Mail.Read"]["category"] == "mail"
        assert oauth_client.HIGH_RISK_PERMISSIONS["User.Read.All"]["category"] == "user"
        assert oauth_client.HIGH_RISK_PERMISSIONS["Files.Read.All"]["category"] == "files"
        assert oauth_client.HIGH_RISK_PERMISSIONS["Group.Read.All"]["category"] == "group"
        assert oauth_client.HIGH_RISK_PERMISSIONS["RoleManagement.Read.Directory"]["category"] == "admin"
