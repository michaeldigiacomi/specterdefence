"""Unit tests for MS Graph client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.ms_graph import (
    MSGraphAPIError,
    MSGraphAuthError,
    MSGraphClient,
    validate_tenant_credentials,
)


class TestMSGraphClient:
    """Test cases for MSGraphClient."""

    @pytest.fixture
    def mock_msal_app(self):
        """Create a mock MSAL application."""
        with patch("src.clients.ms_graph.msal.ConfidentialClientApplication") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_msal_app):
        """Create a test client with mocked MSAL."""
        mock_app = MagicMock()
        mock_msal_app.return_value = mock_app

        return MSGraphClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, client, mock_msal_app):
        """Test successful token acquisition."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None  # No cached token
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-access-token",
            "expires_in": 3600,
        }

        token = await client.get_access_token()

        assert token == "test-access-token"
        mock_app.acquire_token_silent.assert_called_once()
        mock_app.acquire_token_for_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_from_cache(self, client, mock_msal_app):
        """Test getting token from cache."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = {
            "access_token": "cached-token",
            "expires_in": 3600,
        }

        token = await client.get_access_token()

        assert token == "cached-token"
        mock_app.acquire_token_for_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_access_token_failure(self, client, mock_msal_app):
        """Test token acquisition failure."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Client authentication failed",
        }

        with pytest.raises(MSGraphAuthError) as exc_info:
            await client.get_access_token()

        assert "Client authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, client):
        """Test successful credential validation."""
        with patch.object(client, "get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test-token"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "value": [
                        {
                            "displayName": "Test Organization",
                            "id": "test-tenant-id",
                            "verifiedDomains": [{"name": "test.com", "isDefault": True}],
                        }
                    ]
                }
                mock_get.return_value = mock_response

                result = await client.validate_credentials()

                assert result["valid"] is True
                assert result["display_name"] == "Test Organization"
                assert result["tenant_id"] == "test-tenant-id"
                assert len(result["verified_domains"]) == 1

    @pytest.mark.asyncio
    async def test_validate_credentials_unauthorized(self, client):
        """Test credential validation with 401 response."""
        with patch.object(client, "get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test-token"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_get.return_value = mock_response

                with pytest.raises(MSGraphAuthError) as exc_info:
                    await client.validate_credentials()

                assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_credentials_api_error(self, client):
        """Test credential validation with API error."""
        with patch.object(client, "get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test-token"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_get.return_value = mock_response

                with pytest.raises(MSGraphAPIError) as exc_info:
                    await client.validate_credentials()

                assert "API error: 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_credentials_empty_response(self, client):
        """Test credential validation with empty response."""
        with patch.object(client, "get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test-token"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"value": []}
                mock_get.return_value = mock_response

                result = await client.validate_credentials()

                assert result["valid"] is True
                assert result["display_name"] == ""
                assert result["tenant_id"] == ""

    @pytest.mark.asyncio
    async def test_get_tenant_info(self, client):
        """Test getting tenant information."""
        with patch.object(client, "get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test-token"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "value": [{"displayName": "Test Org", "id": "tenant-id", "verifiedDomains": []}]
                }
                mock_get.return_value = mock_response

                result = await client.get_tenant_info()

                assert result["displayName"] == "Test Org"
                assert result["id"] == "tenant-id"


class TestValidateTenantCredentials:
    """Test cases for validate_tenant_credentials function."""

    @pytest.mark.asyncio
    async def test_validate_tenant_credentials(self):
        """Test the convenience function for validating credentials."""
        with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.validate_credentials = AsyncMock(
                return_value={"valid": True, "display_name": "Test Org"}
            )
            mock_client_class.return_value = mock_client

            result = await validate_tenant_credentials(
                tenant_id="test-tenant", client_id="test-client", client_secret="test-secret"
            )

            assert result["valid"] is True
            assert result["display_name"] == "Test Org"
            mock_client_class.assert_called_once_with(
                "test-tenant", "test-client", "test-secret", timeout=30.0
            )
