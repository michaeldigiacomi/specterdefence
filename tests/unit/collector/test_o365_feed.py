"""Unit tests for O365 Management Activity API client."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx

# Need to patch MSAL before importing
with patch("src.collector.o365_feed.msal.ConfidentialClientApplication"):
    from src.collector.o365_feed import (
        O365ManagementClient,
        O365ManagementAuthError,
        O365ManagementAPIError,
        RateLimitError,
        map_content_type_to_log_type,
        MANAGEMENT_API_BASE,
        CONTENT_TYPES,
    )


@pytest.fixture
def mock_msal_app():
    """Create a mock MSAL application."""
    with patch("src.collector.o365_feed.msal.ConfidentialClientApplication") as mock_class:
        mock_app = Mock()
        mock_class.return_value = mock_app
        yield mock_app


class TestO365ManagementClient:
    """Test suite for O365ManagementClient."""

    @pytest.fixture
    def client(self, mock_msal_app):
        """Create a test client."""
        return O365ManagementClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
            max_retries=2,
            base_delay=0.1,
        )

    @pytest.fixture
    def mock_token_response(self):
        """Mock successful token response."""
        return {
            "access_token": "test-token-123",
            "expires_in": 3600,
        }

    def test_init(self, client):
        """Test client initialization."""
        assert client.tenant_id == "test-tenant-id"
        assert client.client_id == "test-client-id"
        assert client.max_retries == 2
        assert client._access_token is None

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, client, mock_msal_app, mock_token_response):
        """Test successful token acquisition."""
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = mock_token_response
        
        token = await client._get_access_token()
        assert token == "test-token-123"
        assert client._access_token == "test-token-123"

    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, client, mock_msal_app):
        """Test token caching."""
        client._access_token = "cached-token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        token = await client._get_access_token()
        assert token == "cached-token"
        mock_msal_app.acquire_token_silent.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_access_token_failure(self, client, mock_msal_app):
        """Test token acquisition failure."""
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = {"error_description": "Invalid credentials"}
        
        with pytest.raises(O365ManagementAuthError):
            await client._get_access_token()

    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_token_response):
        """Test successful API request."""
        client._access_token = "test-token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)
            
            result = await client._make_request("GET", "test/endpoint")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_make_request_rate_limit_with_retry_after(self, client):
        """Test rate limit handling with Retry-After header."""
        client._access_token = "test-token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        success_response.raise_for_status = Mock()
        
        responses = [rate_limit_response, success_response]
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=responses)
            
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._make_request("GET", "test/endpoint")
                assert result == {"data": "success"}

    @pytest.mark.asyncio
    async def test_make_request_rate_limit_exhausted(self, client):
        """Test rate limit exhaustion after max retries."""
        client._access_token = "test-token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=rate_limit_response)
            
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RateLimitError):
                    await client._make_request("GET", "test/endpoint")

    @pytest.mark.asyncio
    async def test_make_request_401_retry(self, client, mock_msal_app):
        """Test 401 retry with fresh token."""
        client._access_token = "old-token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        auth_error_response = Mock()
        auth_error_response.status_code = 401
        auth_error_response.text = "Unauthorized"
        
        # Mock token acquisition to return a valid token after 401
        mock_msal_app.acquire_token_silent.return_value = None
        mock_msal_app.acquire_token_for_client.return_value = {"access_token": "new-token", "expires_in": 3600}
        
        call_count = 0
        def track_token_during_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call should have old token
                assert client._access_token == "old-token"
            return auth_error_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=track_token_during_request)
            
            with pytest.raises(O365ManagementAuthError):
                await client._make_request("GET", "test/endpoint")
            
            # Should be called twice (original + 1 retry)
            assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_start_subscription(self, client):
        """Test starting a subscription."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "enabled"}
            
            result = await client.start_subscription("Audit.General")
            
            mock_request.assert_called_once_with(
                "POST",
                "activity/feed/subscriptions/start",
                {"contentType": "Audit.General"}
            )
            assert result == {"status": "enabled"}

    @pytest.mark.asyncio
    async def test_list_subscriptions(self, client):
        """Test listing subscriptions."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [
                {"contentType": "Audit.General", "status": "enabled"}
            ]
            
            result = await client.list_subscriptions()
            
            mock_request.assert_called_once_with("GET", "activity/feed/subscriptions/list")
            assert len(result) == 1
            assert result[0]["contentType"] == "Audit.General"

    @pytest.mark.asyncio
    async def test_get_content_blobs(self, client):
        """Test getting content blobs."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "contentUri": ["https://blob1.json", "https://blob2.json"],
                "nextPageUri": None
            }
            
            result = await client.get_content_blobs(
                "Audit.General",
                start_time=start_time,
                end_time=end_time
            )
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "activity/feed/subscriptions/content"
            # Check params - they might be passed as positional or keyword arg
            params_arg = call_args.kwargs.get("params") or (call_args[0][2] if len(call_args[0]) > 2 else None)
            if params_arg is None:
                # Might be passed as second positional arg
                params_arg = call_args[1] if len(call_args) > 1 else {}
            assert params_arg["contentType"] == "Audit.General"
            assert "startTime" in params_arg
            assert "endTime" in params_arg

    @pytest.mark.asyncio
    async def test_get_content_blobs_with_next_page(self, client):
        """Test getting content blobs with pagination."""
        next_page_uri = "https://manage.office.com/api/v1.0/next-page"
        
        # Mock _get_access_token
        client._access_token = "test-token"
        client._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"contentUri": ["https://blob3.json"], "nextPageUri": None}
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await client.get_content_blobs(
                "Audit.General",
                next_page_uri=next_page_uri
            )
            
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args[0][0] == next_page_uri

    @pytest.mark.asyncio
    async def test_download_content(self, client):
        """Test downloading content from blob URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"id": "event1", "type": "test"}) + "\n" + json.dumps({"id": "event2", "type": "test"})
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await client.download_content("https://blob.json")
            
            assert len(result) == 2
            assert result[0]["id"] == "event1"
            assert result[1]["id"] == "event2"

    @pytest.mark.asyncio
    async def test_download_content_empty(self, client):
        """Test downloading empty content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await client.download_content("https://blob.json")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_collect_logs(self, client):
        """Test log collection with pagination."""
        # Mock get_content_blobs responses
        blob_responses = [
            {
                "contentUri": ["https://blob1.json"],
                "nextPageUri": "https://next-page.json"
            },
            {
                "contentUri": ["https://blob2.json"],
                "nextPageUri": None
            }
        ]
        
        with patch.object(client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            with patch.object(client, "download_content", new_callable=AsyncMock) as mock_download:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    mock_blobs.side_effect = blob_responses
                    mock_download.side_effect = [
                        [{"id": "event1"}],
                        [{"id": "event2"}]
                    ]
                    
                    batches = []
                    async for batch in client.collect_logs("Audit.General"):
                        batches.append(batch)
                    
                    assert len(batches) == 2
                    assert batches[0][0]["id"] == "event1"
                    assert batches[1][0]["id"] == "event2"

    @pytest.mark.asyncio
    async def test_collect_logs_rate_limit(self, client):
        """Test log collection with rate limit."""
        with patch.object(client, "get_content_blobs", new_callable=AsyncMock) as mock_blobs:
            mock_blobs.side_effect = RateLimitError("Rate limited")
            
            with pytest.raises(RateLimitError):
                async for _ in client.collect_logs("Audit.General"):
                    pass

    @pytest.mark.asyncio
    async def test_ensure_subscriptions(self, client):
        """Test ensuring subscriptions are active."""
        with patch.object(client, "start_subscription", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = {"status": "enabled"}
            
            result = await client.ensure_subscriptions()
            
            assert len(result) == len(CONTENT_TYPES)
            assert mock_start.call_count == len(CONTENT_TYPES)

    @pytest.mark.asyncio
    async def test_ensure_subscriptions_already_active(self, client):
        """Test ensuring subscriptions when already active."""
        with patch.object(client, "start_subscription", new_callable=AsyncMock) as mock_start:
            # Simulate "already enabled" error
            error = O365ManagementAPIError("subscription already enabled")
            mock_start.side_effect = error
            
            # Should handle this gracefully
            result = await client.ensure_subscriptions()
            
            # Should still return the content types since they're already subscribed
            assert len(result) == len(CONTENT_TYPES)


class TestMapContentTypeToLogType:
    """Test content type mapping."""

    def test_signin_mapping(self):
        """Test Azure AD audit maps to signin."""
        assert map_content_type_to_log_type("Audit.AzureActiveDirectory") == "signin"

    def test_general_mappings(self):
        """Test various content types map to audit_general."""
        assert map_content_type_to_log_type("Audit.Exchange") == "audit_general"
        assert map_content_type_to_log_type("Audit.SharePoint") == "audit_general"
        assert map_content_type_to_log_type("Audit.General") == "audit_general"
        assert map_content_type_to_log_type("DLP.All") == "audit_general"

    def test_unknown_mapping(self):
        """Test unknown content type defaults to audit_general."""
        assert map_content_type_to_log_type("Unknown.Type") == "audit_general"
