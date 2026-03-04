"""Comprehensive unit tests for Office 365 Management Activity API client.

SPD-10: Unit Tests - Office365 API Client
Tests cover:
- MSAL integration and token acquisition
- Token caching and expiration handling
- Error handling (401, 403, 429, 500)
- Pagination handling
- Rate limiting and exponential backoff
- Content blob operations
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

# Mock encryption service before any imports
mock_encryption = MagicMock()
mock_encryption.encrypt.return_value = "encrypted-value"
mock_encryption.decrypt.return_value = "decrypted-secret"
sys.modules["src.services.encryption"] = mock_encryption

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

# Patch MSAL before importing
with patch("src.collector.o365_feed.msal.ConfidentialClientApplication"):
    from src.collector.o365_feed import (
        CONTENT_TYPES,
        O365ManagementAPIError,
        O365ManagementAuthError,
        O365ManagementClient,
        RateLimitError,
        map_content_type_to_log_type,
    )


# Cleanup: Remove the mock to avoid affecting other tests
def teardown_module():
    """Remove the mock to avoid affecting other tests."""
    if "src.services.encryption" in sys.modules:
        del sys.modules["src.services.encryption"]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_msal_app():
    """Create a mock MSAL ConfidentialClientApplication."""
    with patch("src.collector.o365_feed.msal.ConfidentialClientApplication") as mock_class:
        mock_app = Mock()
        mock_class.return_value = mock_app
        yield mock_app


@pytest.fixture
def o365_client(mock_msal_app):
    """Create a test O365ManagementClient instance."""
    client = O365ManagementClient(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        max_retries=3,
        base_delay=0.1,  # Short delay for tests
    )
    return client


@pytest.fixture
def mock_token_response():
    """Return a mock successful token response."""
    return {
        "access_token": "mock-management-token-12345",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@pytest.fixture
def mock_subscription_response():
    """Return a mock subscription response."""
    return {
        "contentType": "Audit.General",
        "status": "enabled",
        "webhook": None,
    }


@pytest.fixture
def mock_content_blobs_response():
    """Return a mock content blobs response."""
    return {
        "contentUri": [
            "https://blob1.office.net/audit/2026-03-01.json",
            "https://blob2.office.net/audit/2026-03-01.json",
        ],
        "nextPageUri": None,
    }


# =============================================================================
# Authentication Tests
# =============================================================================


class TestO365Authentication:
    """Test cases for MSAL integration and token acquisition."""

    def test_client_initialization(self, o365_client):
        """Test client initialization with correct parameters."""
        assert o365_client.tenant_id == "test-tenant-id"
        assert o365_client.client_id == "test-client-id"
        assert o365_client.client_secret == "test-client-secret"
        assert o365_client.max_retries == 3
        assert o365_client.base_delay == 0.1
        assert o365_client._access_token is None
        assert o365_client._token_expires_at is None

    def test_msal_app_initialization(self, mock_msal_app):
        """Test MSAL app is initialized with correct parameters."""
        client = O365ManagementClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
        )
        # MSAL app should have been created
        assert client.app is not None

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, o365_client, mock_msal_app, mock_token_response):
        """Test successful token acquisition from MSAL."""
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = mock_token_response

        token = await o365_client._get_access_token()

        assert token == "mock-management-token-12345"
        mock_msal_app.acquire_token_silent.assert_called_once_with(
            ["https://manage.office.com/.default"], account=None
        )
        mock_msal_app.acquire_token_for_client.assert_called_once_with(
            scopes=["https://manage.office.com/.default"]
        )

    @pytest.mark.asyncio
    async def test_get_access_token_from_cache(self, o365_client, mock_msal_app):
        """Test retrieving token from cache."""
        cached_token = {
            "access_token": "cached-token",
            "expires_in": 3600,
        }
        mock_msal_app.acquire_token_silent.return_value = cached_token

        token = await o365_client._get_access_token()

        assert token == "cached-token"
        mock_msal_app.acquire_token_silent.assert_called_once()
        mock_msal_app.acquire_token_for_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_access_token_cached_in_client(self, o365_client, mock_msal_app):
        """Test client-side token caching."""
        # Set cached token
        o365_client._access_token = "client-cached-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        token = await o365_client._get_access_token()

        assert token == "client-cached-token"
        mock_msal_app.acquire_token_silent.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_access_token_expired_refresh(
        self, o365_client, mock_msal_app, mock_token_response
    ):
        """Test automatic token refresh when token is near expiration."""
        # Set token that expires soon (less than 5 minutes buffer)
        o365_client._access_token = "expiring-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(minutes=3)

        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = mock_token_response

        token = await o365_client._get_access_token()

        assert token == "mock-management-token-12345"
        mock_msal_app.acquire_token_for_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_invalid_client_id(self, o365_client, mock_msal_app):
        """Test authentication failure with invalid client_id."""
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "AADSTS700016: Application not found",
            "error_codes": [700016],
        }

        with pytest.raises(O365ManagementAuthError) as exc_info:
            await o365_client._get_access_token()

        assert "Failed to get access token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_access_token_invalid_client_secret(self, o365_client, mock_msal_app):
        """Test authentication failure with invalid client_secret."""
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "AADSTS7000215: Invalid client secret",
            "error_codes": [7000215],
        }

        with pytest.raises(O365ManagementAuthError) as exc_info:
            await o365_client._get_access_token()

        assert "Invalid client secret" in str(exc_info.value)


# =============================================================================
# API Request Tests
# =============================================================================


class TestO365APIRequests:
    """Test cases for API request handling."""

    @pytest.mark.asyncio
    async def test_make_request_success(self, o365_client, mock_token_response):
        """Test successful API request."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await o365_client._make_request("GET", "test/endpoint")

            assert result == {"data": "test"}
            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_params(self, o365_client, mock_token_response):
        """Test API request with query parameters."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            await o365_client._make_request(
                "GET",
                "activity/feed/subscriptions/content",
                params={"contentType": "Audit.General", "startTime": "2026-03-01T00:00:00"},
            )

            call_args = mock_client.request.call_args
            assert call_args[1]["params"]["contentType"] == "Audit.General"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestO365ErrorHandling:
    """Test cases for HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_401_unauthorized(self, o365_client, mock_msal_app):
        """Test handling of HTTP 401 Unauthorized with token refresh."""
        o365_client._access_token = "old-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        auth_error_response = MagicMock()
        auth_error_response.status_code = 401
        auth_error_response.text = "Unauthorized"

        # Mock token acquisition to return new token
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = {
            "access_token": "new-token",
            "expires_in": 3600,
        }

        call_count = 0

        def track_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return auth_error_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=track_request)

            with pytest.raises(O365ManagementAuthError):
                await o365_client._make_request("GET", "test/endpoint")

            # Should be called twice (original + 1 retry)
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_http_403_forbidden(self, o365_client, mock_token_response):
        """Test handling of HTTP 403 Forbidden."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Access denied. Check permissions."

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            with pytest.raises(O365ManagementAuthError) as exc_info:
                await o365_client._make_request("GET", "test/endpoint")

            assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_429_rate_limited_with_retry_after(self, o365_client, mock_token_response):
        """Test handling of HTTP 429 with Retry-After header."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "2"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=[rate_limit_response, success_response])

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await o365_client._make_request("GET", "test/endpoint")

                assert result == {"data": "success"}
                mock_sleep.assert_called_once_with(2)  # Should use Retry-After value

    @pytest.mark.asyncio
    async def test_http_429_rate_limited_without_retry_after(
        self, o365_client, mock_token_response
    ):
        """Test handling of HTTP 429 without Retry-After header (exponential backoff)."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}  # No Retry-After

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=[rate_limit_response, success_response])

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await o365_client._make_request("GET", "test/endpoint")

                assert result == {"data": "success"}
                # Should use exponential backoff: base_delay * (2 ** 0) = 0.1
                mock_sleep.assert_called_once_with(0.1)

    @pytest.mark.asyncio
    async def test_http_429_rate_limited_exhausted(self, o365_client, mock_token_response):
        """Test rate limit exhaustion after max retries."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            # Always return rate limit
            mock_client.request = AsyncMock(return_value=rate_limit_response)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RateLimitError) as exc_info:
                    await o365_client._make_request("GET", "test/endpoint")

                assert "Rate limit exceeded after 3 retries" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_500_server_error(self, o365_client, mock_token_response):
        """Test handling of HTTP 500 Server Error."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.raise_for_status = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_response
            )

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            with pytest.raises(O365ManagementAPIError):
                await o365_client._make_request("GET", "test/endpoint")

    @pytest.mark.asyncio
    async def test_network_timeout(self, o365_client, mock_token_response):
        """Test handling of network timeout with retry."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(
                side_effect=[httpx.TimeoutException("Connection timed out"), success_response]
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await o365_client._make_request("GET", "test/endpoint")

                assert result == {"data": "success"}

    @pytest.mark.asyncio
    async def test_connection_error_with_retry(self, o365_client, mock_token_response):
        """Test handling of connection error with retry."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(
                side_effect=[httpx.ConnectError("Connection refused"), success_response]
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await o365_client._make_request("GET", "test/endpoint")

                assert result == {"data": "success"}

    @pytest.mark.asyncio
    async def test_connection_error_exhausted(self, o365_client, mock_token_response):
        """Test connection error after max retries exhausted."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(O365ManagementAPIError) as exc_info:
                    await o365_client._make_request("GET", "test/endpoint")

                assert "Request failed after 3 retries" in str(exc_info.value)


# =============================================================================
# Subscription Tests
# =============================================================================


class TestO365Subscriptions:
    """Test cases for subscription management."""

    @pytest.mark.asyncio
    async def test_start_subscription(self, o365_client):
        """Test starting a subscription."""
        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "enabled"}

            result = await o365_client.start_subscription("Audit.General")

            mock_request.assert_called_once_with(
                "POST", "activity/feed/subscriptions/start", {"contentType": "Audit.General"}
            )
            assert result == {"status": "enabled"}

    @pytest.mark.asyncio
    async def test_list_subscriptions(self, o365_client):
        """Test listing subscriptions."""
        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [
                {"contentType": "Audit.General", "status": "enabled"},
                {"contentType": "Audit.Exchange", "status": "enabled"},
            ]

            result = await o365_client.list_subscriptions()

            mock_request.assert_called_once_with("GET", "activity/feed/subscriptions/list")
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_subscriptions_empty(self, o365_client):
        """Test listing subscriptions when empty."""
        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = []

            result = await o365_client.list_subscriptions()

            assert result == []

    @pytest.mark.asyncio
    async def test_list_subscriptions_non_list(self, o365_client):
        """Test listing subscriptions when API returns non-list."""
        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "enabled"}  # Not a list

            result = await o365_client.list_subscriptions()

            assert result == []  # Should return empty list

    @pytest.mark.asyncio
    async def test_stop_subscription(self, o365_client):
        """Test stopping a subscription."""
        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "disabled"}

            await o365_client.stop_subscription("Audit.General")

            mock_request.assert_called_once_with(
                "POST", "activity/feed/subscriptions/stop", {"contentType": "Audit.General"}
            )


# =============================================================================
# Content Blob Tests
# =============================================================================


class TestO365ContentBlobs:
    """Test cases for content blob operations."""

    @pytest.mark.asyncio
    async def test_get_content_blobs_with_time_range(self, o365_client):
        """Test getting content blobs with time range."""
        start_time = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "contentUri": ["https://blob1.json"],
                "nextPageUri": None,
            }

            await o365_client.get_content_blobs(
                "Audit.General", start_time=start_time, end_time=end_time
            )

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "activity/feed/subscriptions/content"
            # Check params - might be passed as positional or keyword argument
            if len(call_args[0]) > 2:
                params_arg = call_args[0][2]
            else:
                params_arg = call_args.kwargs.get("params", {})
            assert params_arg["contentType"] == "Audit.General"
            assert "startTime" in params_arg
            assert "endTime" in params_arg

    @pytest.mark.asyncio
    async def test_get_content_blobs_pagination(self, o365_client, mock_token_response):
        """Test getting content blobs with pagination."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        next_page_uri = "https://manage.office.com/api/v1.0/next-page"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "contentUri": ["https://blob3.json"],
                "nextPageUri": None,
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            await o365_client.get_content_blobs("Audit.General", next_page_uri=next_page_uri)

            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args[0][0] == next_page_uri

    @pytest.mark.asyncio
    async def test_download_content(self, o365_client):
        """Test downloading content from blob URL."""
        events_data = [
            {"id": "event1", "type": "AuditEvent"},
            {"id": "event2", "type": "AuditEvent"},
        ]
        content = "\n".join([json.dumps(e) for e in events_data])

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = content
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await o365_client.download_content("https://blob.json")

            assert len(result) == 2
            assert result[0]["id"] == "event1"
            assert result[1]["id"] == "event2"

    @pytest.mark.asyncio
    async def test_download_content_empty(self, o365_client):
        """Test downloading empty content."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await o365_client.download_content("https://blob.json")

            assert result == []

    @pytest.mark.asyncio
    async def test_download_content_whitespace(self, o365_client):
        """Test downloading content with only whitespace."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "   \n\n   "
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await o365_client.download_content("https://blob.json")

            assert result == []


# =============================================================================
# Pagination Tests
# =============================================================================


class TestO365Pagination:
    """Test cases for pagination handling."""

    @pytest.mark.asyncio
    async def test_single_page_response(self, o365_client):
        """Test handling of single page response."""
        with patch.object(o365_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "contentUri": ["https://blob1.json"],
                "nextPageUri": None,  # No next page
            }

            result = await o365_client.get_content_blobs("Audit.General")

            assert result["nextPageUri"] is None
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_page_response(self, o365_client):
        """Test handling of multi-page response."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            mock_blobs.side_effect = [
                {"contentUri": ["https://blob1.json"], "nextPageUri": "https://next-page.json"},
                {"contentUri": ["https://blob2.json"], "nextPageUri": None},
            ]

            # Simulate pagination
            page1 = await o365_client.get_content_blobs("Audit.General")
            assert page1["nextPageUri"] is not None

            page2 = await o365_client.get_content_blobs(
                "Audit.General", next_page_uri=page1["nextPageUri"]
            )
            assert page2["nextPageUri"] is None

    @pytest.mark.asyncio
    async def test_next_link_following(self, o365_client, mock_token_response):
        """Test following next page URI."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        next_page_uri = "https://manage.office.com/api/v1.0/tenant/activity/feed/subscriptions/content?$skip=100"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"contentUri": [], "nextPageUri": None}
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            await o365_client.get_content_blobs("Audit.General", next_page_uri=next_page_uri)

            mock_client.get.assert_called_once_with(
                next_page_uri, headers={"Authorization": "Bearer test-token"}, timeout=60.0
            )


# =============================================================================
# Collect Logs Tests
# =============================================================================


class TestO365CollectLogs:
    """Test cases for log collection."""

    @pytest.mark.asyncio
    async def test_collect_logs_single_page(self, o365_client):
        """Test collecting logs from single page."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            with patch.object(
                o365_client, "download_content", new_callable=AsyncMock
            ) as mock_download:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    mock_blobs.return_value = {
                        "contentUri": ["https://blob1.json"],
                        "nextPageUri": None,
                    }
                    mock_download.return_value = [{"id": "event1"}]

                    batches = []
                    async for batch in o365_client.collect_logs("Audit.General"):
                        batches.append(batch)

                    assert len(batches) == 1
                    assert batches[0][0]["id"] == "event1"

    @pytest.mark.asyncio
    async def test_collect_logs_multi_page(self, o365_client):
        """Test collecting logs across multiple pages."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            with patch.object(
                o365_client, "download_content", new_callable=AsyncMock
            ) as mock_download:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    mock_blobs.side_effect = [
                        {
                            "contentUri": ["https://blob1.json"],
                            "nextPageUri": "https://next-page.json",
                        },
                        {"contentUri": ["https://blob2.json"], "nextPageUri": None},
                    ]
                    mock_download.side_effect = [
                        [{"id": "event1"}],
                        [{"id": "event2"}],
                    ]

                    batches = []
                    async for batch in o365_client.collect_logs("Audit.General"):
                        batches.append(batch)

                    assert len(batches) == 2

    @pytest.mark.asyncio
    async def test_collect_logs_empty_blobs(self, o365_client):
        """Test collecting logs when no blobs available."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            mock_blobs.return_value = {
                "contentUri": [],
                "nextPageUri": None,
            }

            batches = []
            async for batch in o365_client.collect_logs("Audit.General"):
                batches.append(batch)

            assert len(batches) == 0

    @pytest.mark.asyncio
    async def test_collect_logs_download_error(self, o365_client):
        """Test collecting logs with download error handling."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            with patch.object(
                o365_client, "download_content", new_callable=AsyncMock
            ) as mock_download:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    mock_blobs.return_value = {
                        "contentUri": ["https://blob1.json", "https://blob2.json"],
                        "nextPageUri": None,
                    }
                    mock_download.side_effect = [
                        [{"id": "event1"}],
                        Exception("Download failed"),
                    ]

                    batches = []
                    async for batch in o365_client.collect_logs("Audit.General"):
                        batches.append(batch)

                    # Should continue despite error
                    assert len(batches) == 1

    @pytest.mark.asyncio
    async def test_collect_logs_rate_limit(self, o365_client):
        """Test collecting logs with rate limit error."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            mock_blobs.side_effect = RateLimitError("Rate limited")

            with pytest.raises(RateLimitError):
                async for _ in o365_client.collect_logs("Audit.General"):
                    pass


# =============================================================================
# Ensure Subscriptions Tests
# =============================================================================


class TestO365EnsureSubscriptions:
    """Test cases for subscription management."""

    @pytest.mark.asyncio
    async def test_ensure_subscriptions_success(self, o365_client):
        """Test ensuring all subscriptions are active."""
        with patch.object(o365_client, "start_subscription", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = {"status": "enabled"}

            result = await o365_client.ensure_subscriptions()

            assert len(result) == len(CONTENT_TYPES)
            assert mock_start.call_count == len(CONTENT_TYPES)

    @pytest.mark.asyncio
    async def test_ensure_subscriptions_already_active(self, o365_client):
        """Test ensuring subscriptions when already active."""
        with patch.object(o365_client, "start_subscription", new_callable=AsyncMock) as mock_start:
            error = O365ManagementAPIError("subscription already enabled")
            mock_start.side_effect = error

            result = await o365_client.ensure_subscriptions()

            # Should still return content types since they're already subscribed
            assert len(result) == len(CONTENT_TYPES)

    @pytest.mark.asyncio
    async def test_ensure_subscriptions_partial_failure(self, o365_client):
        """Test ensuring subscriptions with some failures."""
        with patch.object(o365_client, "start_subscription", new_callable=AsyncMock) as mock_start:
            # First succeeds, second fails with different error
            def side_effect(content_type):
                if content_type == CONTENT_TYPES[0]:
                    return {"status": "enabled"}
                raise O365ManagementAPIError("Unknown error")

            mock_start.side_effect = side_effect

            result = await o365_client.ensure_subscriptions()

            # Should only include successfully subscribed
            assert CONTENT_TYPES[0] in result


# =============================================================================
# Content Type Mapping Tests
# =============================================================================


class TestContentTypeMapping:
    """Test cases for content type to log type mapping."""

    def test_signin_mapping(self):
        """Test Azure AD audit maps to signin."""
        assert map_content_type_to_log_type("Audit.AzureActiveDirectory") == "signin"

    def test_exchange_mapping(self):
        """Test Exchange audit maps to audit_general."""
        assert map_content_type_to_log_type("Audit.Exchange") == "audit_general"

    def test_sharepoint_mapping(self):
        """Test SharePoint audit maps to audit_general."""
        assert map_content_type_to_log_type("Audit.SharePoint") == "audit_general"

    def test_general_mapping(self):
        """Test General audit maps to audit_general."""
        assert map_content_type_to_log_type("Audit.General") == "audit_general"

    def test_dlp_mapping(self):
        """Test DLP audit maps to audit_general."""
        assert map_content_type_to_log_type("DLP.All") == "audit_general"

    def test_unknown_mapping(self):
        """Test unknown content type defaults to audit_general."""
        assert map_content_type_to_log_type("Unknown.Type") == "audit_general"
        assert map_content_type_to_log_type("") == "audit_general"
        assert map_content_type_to_log_type(None) == "audit_general"


# =============================================================================
# Rate Limiting and Backoff Tests
# =============================================================================


class TestO365RateLimiting:
    """Test cases for rate limiting and backoff."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self, o365_client, mock_token_response):
        """Test exponential backoff calculation."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}  # No Retry-After

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(
                side_effect=[
                    rate_limit_response,  # retry 0: delay = 0.1 * 2^0 = 0.1
                    rate_limit_response,  # retry 1: delay = 0.1 * 2^1 = 0.2
                    success_response,
                ]
            )

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await o365_client._make_request("GET", "test/endpoint")

                assert result == {"data": "success"}
                assert mock_sleep.call_count == 2
                # Check backoff values
                assert mock_sleep.call_args_list[0][0][0] == 0.1
                assert mock_sleep.call_args_list[1][0][0] == 0.2

    @pytest.mark.asyncio
    async def test_retry_after_header_parsing(self, o365_client, mock_token_response):
        """Test parsing of Retry-After header values."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "30"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=[rate_limit_response, success_response])

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await o365_client._make_request("GET", "test/endpoint")

                mock_sleep.assert_called_once_with(30)  # Use Retry-After value

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, o365_client, mock_token_response):
        """Test that max retries are properly enforced."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=rate_limit_response)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RateLimitError) as exc_info:
                    await o365_client._make_request("GET", "test/endpoint")

                assert "after 3 retries" in str(exc_info.value)
                assert mock_client.request.call_count == 4  # Original + 3 retries

    @pytest.mark.asyncio
    async def test_successful_retry_after_rate_limit(self, o365_client, mock_token_response):
        """Test successful request after rate limit recovery."""
        o365_client._access_token = "test-token"
        o365_client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "recovered"}
        success_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=[rate_limit_response, success_response])

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await o365_client._make_request("GET", "test/endpoint")

                assert result == {"data": "recovered"}


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


class TestO365EdgeCases:
    """Test edge cases and integration scenarios."""

    @pytest.mark.asyncio
    async def test_special_characters_in_secret(self, mock_msal_app):
        """Test handling of special characters in client secret."""
        client = O365ManagementClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="secret-with-!@#$%^&*()_+-=[]{}|;':\",./<>?",
        )
        assert client.client_secret == "secret-with-!@#$%^&*()_+-=[]{}|;':\",./<>?"

    @pytest.mark.asyncio
    async def test_very_long_content_uri_list(self, o365_client):
        """Test handling of very long content URI list."""
        with patch.object(o365_client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            with patch.object(
                o365_client, "download_content", new_callable=AsyncMock
            ) as mock_download:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    # Create many URIs
                    mock_blobs.return_value = {
                        "contentUri": [f"https://blob{i}.json" for i in range(100)],
                        "nextPageUri": None,
                    }
                    mock_download.return_value = [{"id": "event"}]

                    batches = []
                    async for batch in o365_client.collect_logs("Audit.General"):
                        batches.append(batch)

                    assert len(batches) == 100

    @pytest.mark.asyncio
    async def test_unicode_content_in_events(self, o365_client):
        """Test handling of unicode content in events."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Unicode content
            event = {"id": "event1", "user": "用户@例文.com", "message": "日本語テスト"}
            mock_response.text = json.dumps(event)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await o365_client.download_content("https://blob.json")

            assert len(result) == 1
            assert result[0]["user"] == "用户@例文.com"
