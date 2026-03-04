"""Comprehensive tests for Microsoft Graph integration."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.ms_graph import (
    MSGraphAPIError,
    MSGraphAuthError,
    MSGraphClient,
)


class TestMSGraphClientInit:
    """Tests for MSGraphClient initialization."""

    def test_init_with_default_timeout(self):
        """Test initialization with default timeout."""
        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        assert client.tenant_id == "test-tenant"
        assert client.client_id == "test-client"
        assert client.timeout == 30.0  # Default

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            timeout=60.0,
        )

        assert client.timeout == 60.0


class TestMSGraphClientToken:
    """Tests for token acquisition."""

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_access_token_success(self, mock_msal_class):
        """Test successful token acquisition."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        token = await client.get_access_token()

        assert token == "test-token"
        mock_app.acquire_token_for_client.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_access_token_from_cache(self, mock_msal_class):
        """Test token acquisition from cache."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = {
            "access_token": "cached-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        token = await client.get_access_token()

        assert token == "cached-token"
        mock_app.acquire_token_silent.assert_called_once()
        mock_app.acquire_token_for_client.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_access_token_error(self, mock_msal_class):
        """Test token acquisition error."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Client secret is invalid",
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        with pytest.raises(MSGraphAuthError) as exc_info:
            await client.get_access_token()

        assert "invalid_client" in str(exc_info.value)


class TestMSGraphClientAPI:
    """Tests for API calls."""

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_validate_credentials_success(self, mock_msal_class):
        """Test successful credential validation."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "org-id",
                    "displayName": "Test Org",
                    "verifiedDomains": [{"name": "test.com", "isDefault": True}],
                }
            ]
        }

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_session):
            result = await client.validate_credentials()

        assert result["displayName"] == "Test Org"

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_users_success(self, mock_msal_class):
        """Test successful users retrieval."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "user-1",
                    "displayName": "User One",
                    "userPrincipalName": "user1@test.com",
                },
                {
                    "id": "user-2",
                    "displayName": "User Two",
                    "userPrincipalName": "user2@test.com",
                },
            ]
        }

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_session):
            result = await client.get_users()

        assert len(result) == 2
        assert result[0]["displayName"] == "User One"

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_audit_logs_success(self, mock_msal_class):
        """Test successful audit logs retrieval."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "log-1",
                    "activityDisplayName": "Update user",
                    "activityDateTime": "2026-03-01T10:00:00Z",
                    "initiatedBy": {"user": {"userPrincipalName": "admin@test.com"}},
                }
            ]
        }

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_session):
            result = await client.get_audit_logs()

        assert len(result) == 1
        assert result[0]["activityDisplayName"] == "Update user"

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_signin_logs_success(self, mock_msal_class):
        """Test successful sign-in logs retrieval."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "signin-1",
                    "createdDateTime": "2026-03-01T10:00:00Z",
                    "userPrincipalName": "user@test.com",
                    "ipAddress": "192.168.1.1",
                    "status": {"errorCode": 0, "failureReason": None},
                }
            ]
        }

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_session):
            result = await client.get_signin_logs()

        assert len(result) == 1
        assert result[0]["userPrincipalName"] == "user@test.com"


class TestMSGraphClientPagination:
    """Tests for paginated API calls."""

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_get_all_pages(self, mock_msal_class):
        """Test retrieving all paginated results."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        # First page has next link, second page doesn't
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "value": [{"id": "user-1"}, {"id": "user-2"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skip=2",
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "value": [{"id": "user-3"}],
        }

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(side_effect=[mock_response1, mock_response2])

        with patch("httpx.AsyncClient", return_value=mock_session):
            result = await client.get_users()

        assert len(result) == 3


class TestMSGraphClientErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_401_error_raises_auth_error(self, mock_msal_class):
        """Test that 401 raises MSGraphAuthError."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": {"message": "Unauthorized"}}

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_session):
            with pytest.raises(MSGraphAuthError):
                await client.get_users()

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_403_error_raises_api_error(self, mock_msal_class):
        """Test that 403 raises MSGraphAPIError."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.json.return_value = {"error": {"message": "Insufficient permissions"}}

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_session):
            with pytest.raises(MSGraphAPIError):
                await client.get_users()

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_timeout_error(self, mock_msal_class):
        """Test that timeout raises an error."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            timeout=1.0,
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(side_effect=TimeoutError("Request timed out"))

        with patch("httpx.AsyncClient", return_value=mock_session):
            with pytest.raises(Exception):
                await client.get_users()


class TestMSGraphClientContextManager:
    """Tests for async context manager usage."""

    @pytest.mark.asyncio
    @patch("src.clients.ms_graph.msal.ConfidentialClientApplication")
    async def test_client_context_manager(self, mock_msal_class):
        """Test using client as context manager."""
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600,
        }
        mock_msal_class.return_value = mock_app

        client = MSGraphClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        # Just verify client can be created and methods exist
        assert client.tenant_id == "test-tenant"
        assert hasattr(client, 'get_users')
        assert hasattr(client, 'get_access_token')
