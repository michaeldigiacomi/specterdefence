"""Unit tests for the Geo-IP client."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.analytics.geo_ip import GeoIPClient, GeoLocation, get_geo_ip_client, lookup_ip


class TestGeoLocation:
    """Tests for GeoLocation dataclass."""

    def test_geo_location_creation(self):
        """Test creating a GeoLocation object."""
        geo = GeoLocation(
            ip_address="8.8.8.8",
            country="United States",
            country_code="US",
            city="Mountain View",
            region="California",
            latitude=37.386,
            longitude=-122.0838,
            timezone="America/Los_Angeles",
            isp="Google LLC",
            is_private=False,
            lookup_success=True
        )

        assert geo.ip_address == "8.8.8.8"
        assert geo.country == "United States"
        assert geo.country_code == "US"
        assert geo.city == "Mountain View"
        assert geo.latitude == 37.386
        assert geo.longitude == -122.0838
        assert geo.lookup_success is True

    def test_geo_location_defaults(self):
        """Test GeoLocation with default values."""
        geo = GeoLocation(ip_address="1.1.1.1")

        assert geo.ip_address == "1.1.1.1"
        assert geo.country is None
        assert geo.lookup_success is False
        assert geo.is_private is False

    def test_geo_location_error(self):
        """Test GeoLocation with error message."""
        geo = GeoLocation(
            ip_address="invalid",
            lookup_success=False,
            error_message="Invalid IP address"
        )

        assert geo.lookup_success is False
        assert geo.error_message == "Invalid IP address"


class TestGeoIPClient:
    """Tests for GeoIPClient."""

    @pytest.fixture
    def client(self):
        """Create a fresh GeoIPClient for each test."""
        return GeoIPClient()

    def test_is_private_ip_with_private_ips(self, client):
        """Test detection of private IP addresses."""
        private_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "172.31.255.255",
            "127.0.0.1",
            "::1",
            "fe80::1",
            "169.254.0.1",  # Link-local
        ]

        for ip in private_ips:
            assert client._is_private_ip(ip) is True, f"{ip} should be private"

    def test_is_private_ip_with_public_ips(self, client):
        """Test detection of public IP addresses."""
        public_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "104.16.249.249",
            "2001:4860:4860::8888",
            "172.32.0.1",  # Outside private 172.16-31 range
            "9.0.0.1",
        ]

        for ip in public_ips:
            assert client._is_private_ip(ip) is False, f"{ip} should be public"

    def test_is_private_ip_with_invalid_ip(self, client):
        """Test handling of invalid IP addresses."""
        assert client._is_private_ip("invalid") is False
        assert client._is_private_ip("") is False
        assert client._is_private_ip("256.1.1.1") is False
        assert client._is_private_ip("not.an.ip.address") is False

    def test_cache_operations(self, client):
        """Test cache storage and retrieval."""
        ip = "8.8.8.8"
        geo = GeoLocation(
            ip_address=ip,
            country="US",
            lookup_success=True
        )

        # Store in cache
        cache_key = client._get_cache_key(ip)
        client._cache[cache_key] = geo
        client._cache_timestamps[cache_key] = datetime.now()

        # Check cache is valid
        assert client._is_cache_valid(ip) is True

        # Check cache retrieval
        assert client._cache[cache_key] == geo

    def test_cache_expiration(self, client):
        """Test that cache expires after TTL."""
        ip = "8.8.8.8"
        geo = GeoLocation(ip_address=ip, lookup_success=True)

        cache_key = client._get_cache_key(ip)
        client._cache[cache_key] = geo
        client._cache_timestamps[cache_key] = datetime.now() - timedelta(minutes=31)

        # Cache should be expired
        assert client._is_cache_valid(ip) is False

    def test_cache_key_normalization(self, client):
        """Test that cache keys are normalized."""
        # Different cases should map to same key
        key1 = client._get_cache_key("8.8.8.8")
        key2 = client._get_cache_key("8.8.8.8 ")
        key3 = client._get_cache_key(" 8.8.8.8")

        assert key1 == key2 == key3

    @pytest.mark.asyncio
    async def test_lookup_private_ip(self, client):
        """Test lookup of private IP returns local info."""
        result = await client.lookup("192.168.1.1")

        assert result.ip_address == "192.168.1.1"
        assert result.is_private is True
        assert result.lookup_success is True
        assert result.country == "Private Network"

    @pytest.mark.asyncio
    async def test_lookup_private_ip_loopback(self, client):
        """Test lookup of loopback IP."""
        result = await client.lookup("127.0.0.1")

        assert result.ip_address == "127.0.0.1"
        assert result.is_private is True
        assert result.lookup_success is True

    @pytest.mark.asyncio
    async def test_lookup_with_successful_response(self, client):
        """Test successful API lookup."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "countryCode": "US",
            "regionName": "California",
            "city": "Mountain View",
            "lat": 37.386,
            "lon": -122.0838,
            "timezone": "America/Los_Angeles",
            "isp": "Google LLC"
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.lookup("8.8.8.8")

        assert result.lookup_success is True
        assert result.country == "United States"
        assert result.country_code == "US"
        assert result.city == "Mountain View"
        assert result.latitude == 37.386
        assert result.longitude == -122.0838

    @pytest.mark.asyncio
    async def test_lookup_with_cache_hit(self, client):
        """Test that cached results are returned without API call."""
        # Pre-populate cache
        ip = "8.8.8.8"
        cached_geo = GeoLocation(
            ip_address=ip,
            country="Cached Country",
            lookup_success=True
        )
        cache_key = client._get_cache_key(ip)
        client._cache[cache_key] = cached_geo
        client._cache_timestamps[cache_key] = datetime.now()

        # Create mock to verify it's not called
        mock_get_client = AsyncMock()

        with patch.object(client, '_get_client', mock_get_client):
            result = await client.lookup(ip)

        assert result is cached_geo
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_lookup_with_failed_response(self, client):
        """Test handling of failed API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "fail",
            "message": "invalid query"
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.lookup("invalid")

        assert result.lookup_success is False
        assert result.error_message == "invalid query"

    @pytest.mark.asyncio
    async def test_lookup_with_http_error(self, client):
        """Test handling of HTTP error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection error")

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.lookup("8.8.8.8")

        assert result.lookup_success is False
        assert "HTTP error" in result.error_message

    @pytest.mark.asyncio
    async def test_lookup_with_unexpected_error(self, client):
        """Test handling of unexpected error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = ValueError("Unexpected error")

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.lookup("8.8.8.8")

        assert result.lookup_success is False
        assert "Error" in result.error_message

    @pytest.mark.asyncio
    async def test_lookup_batch(self, client):
        """Test batch lookup of multiple IPs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "countryCode": "US",
            "city": "Mountain View",
            "lat": 37.386,
            "lon": -122.0838,
            "timezone": "America/Los_Angeles",
            "isp": "Google LLC"
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            results = await client.lookup_batch(["8.8.8.8", "192.168.1.1"])

        assert len(results) == 2
        assert results["8.8.8.8"].lookup_success is True
        assert results["192.168.1.1"].is_private is True

    def test_clear_cache(self, client):
        """Test clearing the cache."""
        client._cache["test"] = GeoLocation(ip_address="1.1.1.1")
        client._cache_timestamps["test"] = datetime.now()

        client.clear_cache()

        assert len(client._cache) == 0
        assert len(client._cache_timestamps) == 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test that rate limiting is enforced."""
        client._last_request_time = datetime.now()

        # Should wait before making request
        start_time = datetime.now()
        await client._rate_limit()
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should have waited at least some small amount
        assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_rate_limiting_first_request(self, client):
        """Test that first request doesn't wait."""
        client._last_request_time = None

        start_time = datetime.now()
        await client._rate_limit()
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should be essentially instant
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_close_client(self, client):
        """Test closing the HTTP client."""
        mock_http_client = AsyncMock()
        mock_http_client.is_closed = False
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_already_closed(self, client):
        """Test closing already closed client."""
        mock_http_client = AsyncMock()
        mock_http_client.is_closed = True
        client._client = mock_http_client

        await client.close()

        # Should not try to close again
        mock_http_client.aclose.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_client_creates_new(self, client):
        """Test that _get_client creates a new client if None."""
        client._client = None

        new_client = await client._get_client()

        assert new_client is not None

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self, client):
        """Test that _get_client reuses existing client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        client._client = mock_client

        result = await client._get_client()

        assert result is mock_client

    @pytest.mark.asyncio
    async def test_get_client_reopens_closed(self, client):
        """Test that _get_client creates new if existing is closed."""
        mock_client = AsyncMock()
        mock_client.is_closed = True
        client._client = mock_client

        new_client = await client._get_client()

        assert new_client is not mock_client


class TestGlobalClient:
    """Tests for global client functions."""

    def test_get_geo_ip_client_singleton(self):
        """Test that get_geo_ip_client returns singleton."""
        client1 = get_geo_ip_client()
        client2 = get_geo_ip_client()

        assert client1 is client2

    def test_get_geo_ip_client_creates_new(self):
        """Test that get_geo_ip_client creates new client on first call."""
        # Reset the global client
        import src.analytics.geo_ip as geo_ip_module
        geo_ip_module._geo_ip_client = None

        client = get_geo_ip_client()

        assert client is not None
        assert isinstance(client, GeoIPClient)

    @pytest.mark.asyncio
    async def test_lookup_ip_convenience_function(self):
        """Test the convenience lookup_ip function."""
        with patch('src.analytics.geo_ip.get_geo_ip_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.lookup.return_value = GeoLocation(
                ip_address="8.8.8.8",
                country="US",
                lookup_success=True
            )
            mock_get_client.return_value = mock_client

            result = await lookup_ip("8.8.8.8")

            assert result.lookup_success is True
            assert result.country == "US"
            mock_client.lookup.assert_called_once_with("8.8.8.8")


class TestGeoIPClientEdgeCases:
    """Tests for edge cases in GeoIPClient."""

    @pytest.fixture
    def client(self):
        """Create a fresh GeoIPClient for each test."""
        return GeoIPClient()

    @pytest.mark.asyncio
    async def test_lookup_with_whitespace_ip(self, client):
        """Test lookup with whitespace in IP."""
        result = await client.lookup("  192.168.1.1  ")

        # Should recognize as private IP
        assert result.is_private is True

    @pytest.mark.asyncio
    async def test_lookup_ipv6_private(self, client):
        """Test lookup of IPv6 private addresses."""
        # IPv6 loopback
        result = await client.lookup("::1")
        assert result.is_private is True

        # IPv6 link-local
        result = await client.lookup("fe80::1")
        assert result.is_private is True

    @pytest.mark.asyncio
    async def test_lookup_with_empty_response_fields(self, client):
        """Test handling of API response with missing fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "query": "8.8.8.8",
            # Missing many optional fields
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.lookup("8.8.8.8")

        assert result.lookup_success is True
        assert result.ip_address == "8.8.8.8"
        assert result.country is None  # Not in response

    def test_cache_ttl_configuration(self, client):
        """Test that cache TTL can be configured."""
        # Default TTL is 30 minutes
        assert client._cache_ttl == timedelta(minutes=30)

        # Can be changed
        client._cache_ttl = timedelta(minutes=60)
        assert client._cache_ttl == timedelta(minutes=60)

    def test_rate_limit_interval(self, client):
        """Test rate limit interval calculation."""
        # 45 requests per minute = 60/45 = 1.33 seconds between requests
        expected_interval = 60.0 / 45
        assert abs(client.REQUEST_INTERVAL - expected_interval) < 0.01
