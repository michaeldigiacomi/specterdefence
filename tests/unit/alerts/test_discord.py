"""Unit tests for Discord webhook client."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.alerts.discord import DiscordWebhookClient, DiscordWebhookError
from src.models.alerts import SEVERITY_COLORS, EventType, SeverityLevel


class TestDiscordWebhookClient:
    """Test cases for DiscordWebhookClient."""

    @pytest.fixture
    def webhook_url(self):
        """Test webhook URL."""
        return "https://discord.com/api/webhooks/123456/test_token"

    @pytest.fixture
    def client(self, webhook_url):
        """Create a Discord webhook client."""
        return DiscordWebhookClient(webhook_url)

    @pytest.mark.asyncio
    async def test_init(self, client, webhook_url):
        """Test client initialization."""
        assert client.webhook_url == webhook_url
        assert client.timeout == 30.0
        assert client._client is None

    @pytest.mark.asyncio
    async def test_send_alert_success(self, client, webhook_url):
        """Test successful alert sending."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.send_alert(
                title="Test Alert",
                description="Test description",
                severity=SeverityLevel.HIGH,
                event_type=EventType.IMPOSSIBLE_TRAVEL,
                user_email="user@example.com",
            )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify payload structure
        call_args = mock_client.post.call_args
        assert call_args[0][0] == webhook_url
        assert "embeds" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_send_alert_http_error(self, client):
        """Test alert sending with HTTP error."""
        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_client):
            with pytest.raises(DiscordWebhookError) as exc_info:
                await client.send_alert(
                    title="Test Alert",
                    description="Test description",
                    severity=SeverityLevel.HIGH,
                    event_type=EventType.IMPOSSIBLE_TRAVEL,
                )

        assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_alert_request_error(self, client):
        """Test alert sending with request error."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

        with patch.object(client, '_get_client', return_value=mock_client):
            with pytest.raises(DiscordWebhookError) as exc_info:
                await client.send_alert(
                    title="Test Alert",
                    description="Test description",
                    severity=SeverityLevel.HIGH,
                    event_type=EventType.IMPOSSIBLE_TRAVEL,
                )

        assert "Request failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_embed_impossible_travel(self, client):
        """Test embed building for impossible travel."""
        metadata = {
            "distance_km": 10000.5,
            "time_diff_minutes": 30,
            "min_travel_time_minutes": 666,
            "previous_location": {
                "city": "New York",
                "country": "US",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
            "current_location": {
                "city": "Tokyo",
                "country": "JP",
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
            "risk_score": 95,
        }

        embed = client._build_embed(
            title="Impossible Travel Detected",
            description="User traveled too fast",
            severity=SeverityLevel.CRITICAL,
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        assert embed["title"] == "🔥 Impossible Travel Detected"
        assert embed["description"] == "User traveled too fast"
        assert embed["color"] == SEVERITY_COLORS[SeverityLevel.CRITICAL]
        assert "fields" in embed

        # Check fields
        field_names = [f["name"] for f in embed["fields"]]
        assert "👤 User" in field_names
        assert "⚡ Severity" in field_names
        assert "📏 Distance" in field_names
        assert "⏱️ Time" in field_names
        assert "🌍 Locations" in field_names
        assert "🎯 Risk Score" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_new_country(self, client):
        """Test embed building for new country."""
        metadata = {
            "country_code": "FR",
            "known_countries": ["US", "UK", "DE"],
            "is_first_login": False,
        }

        embed = client._build_embed(
            title="New Country Login",
            description="User logged in from new country",
            severity=SeverityLevel.MEDIUM,
            event_type=EventType.NEW_COUNTRY,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "🏳️ New Country" in field_names
        assert "📋 Known Countries" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_brute_force(self, client):
        """Test embed building for brute force."""
        metadata = {
            "recent_failures": 5,
            "failure_reason": "Invalid password",
            "ip_address": "192.168.1.1",
        }

        embed = client._build_embed(
            title="Multiple Failed Logins",
            description="Too many failed attempts",
            severity=SeverityLevel.HIGH,
            event_type=EventType.MULTIPLE_FAILURES,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "❌ Failed Attempts (24h)" in field_names
        assert "📝 Failure Reason" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_without_user(self, client):
        """Test embed building without user email."""
        embed = client._build_embed(
            title="Test Alert",
            description="Test description",
            severity=SeverityLevel.LOW,
            event_type=EventType.ADMIN_ACTION,
            user_email=None,
            metadata={},
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        # Should not have user field
        field_names = [f["name"] for f in embed["fields"]]
        assert "👤 User" not in field_names
        assert "⚡ Severity" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_with_custom_fields(self, client):
        """Test embed building with custom fields."""
        custom_fields = [
            {"name": "Custom Field", "value": "Custom Value", "inline": True}
        ]

        embed = client._build_embed(
            title="Test Alert",
            description="Test description",
            severity=SeverityLevel.MEDIUM,
            event_type=EventType.ADMIN_ACTION,
            user_email="user@example.com",
            metadata={"action": "delete_user"},
            fields=custom_fields,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "Custom Field" in field_names

    @pytest.mark.asyncio
    async def test_format_location(self, client):
        """Test location formatting."""
        # City and country
        assert client._format_location({
            "city": "New York",
            "country": "US"
        }) == "New York, US"

        # Only city
        assert client._format_location({
            "city": "Paris",
        }) == "Paris"

        # Only country
        assert client._format_location({
            "country": "DE"
        }) == "DE"

        # Empty
        assert client._format_location({}) == "Unknown"

    @pytest.mark.asyncio
    async def test_test_webhook_success(self, client):
        """Test webhook test with success."""
        with patch.object(client, 'send_alert', return_value=True):
            result = await client.test_webhook()

        assert result is True

    @pytest.mark.asyncio
    async def test_test_webhook_failure(self, client):
        """Test webhook test with failure."""
        with patch.object(client, 'send_alert', side_effect=DiscordWebhookError("Failed")):
            result = await client.test_webhook()

        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test closing the client."""
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_send_alert_unexpected_error(self, client):
        """Test alert sending with unexpected error."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

        with patch.object(client, '_get_client', return_value=mock_client):
            with pytest.raises(DiscordWebhookError) as exc_info:
                await client.send_alert(
                    title="Test Alert",
                    description="Test description",
                    severity=SeverityLevel.HIGH,
                    event_type=EventType.IMPOSSIBLE_TRAVEL,
                )

        assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_client_creates_new(self, client):
        """Test that _get_client creates a new client when none exists."""
        assert client._client is None

        result = await client._get_client()

        assert result is not None
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_close_no_client(self, client):
        """Test closing when no client exists."""
        # Should not raise
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_build_embed_new_ip(self, client):
        """Test embed building for new IP."""
        metadata = {
            "ip_address": "192.168.1.1",
            "known_ips_count": 5,
        }

        embed = client._build_embed(
            title="New IP Address",
            description="User logged in from new IP",
            severity=SeverityLevel.LOW,
            event_type=EventType.NEW_IP,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "🌐 IP Address" in field_names
        assert "📊 Known IPs" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_admin_action(self, client):
        """Test embed building for admin action."""
        metadata = {
            "action": "delete_user",
            "target": "user@example.com",
            "ip_address": "10.0.0.1",
        }

        embed = client._build_embed(
            title="Admin Action",
            description="Admin action detected",
            severity=SeverityLevel.MEDIUM,
            event_type=EventType.ADMIN_ACTION,
            user_email="admin@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "⚙️ Action" in field_names
        assert "🎯 Target" in field_names
        assert "🌐 IP Address" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_new_country_first_login(self, client):
        """Test embed building for new country with first login."""
        metadata = {
            "country_code": "FR",
            "known_countries": [],
            "is_first_login": True,
            "ip_address": "192.168.1.1",
        }

        embed = client._build_embed(
            title="New Country Login",
            description="User logged in from new country",
            severity=SeverityLevel.MEDIUM,
            event_type=EventType.NEW_COUNTRY,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "🏳️ New Country" in field_names
        assert "🆕 First Login" in field_names

    @pytest.mark.asyncio
    async def test_build_embed_impossible_travel_partial_metadata(self, client):
        """Test embed building for impossible travel with partial metadata."""
        # Missing some fields like risk_score, distance_km
        metadata = {
            "previous_location": {
                "city": "New York",
                "country": "US",
            },
            "current_location": {
                "city": "Tokyo",
                "country": "JP",
            },
        }

        embed = client._build_embed(
            title="Impossible Travel Detected",
            description="User traveled too fast",
            severity=SeverityLevel.CRITICAL,
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        field_names = [f["name"] for f in embed["fields"]]
        assert "🌍 Locations" in field_names
        # Risk score should not be present
        assert "🎯 Risk Score" not in field_names

    @pytest.mark.asyncio
    async def test_build_embed_ip_already_added(self, client):
        """Test embed building when IP is already in metadata fields."""
        # For NEW_IP event, IP is already added - shouldn't duplicate
        metadata = {
            "ip_address": "192.168.1.1",
            "known_ips_count": 3,
        }

        embed = client._build_embed(
            title="New IP",
            description="New IP detected",
            severity=SeverityLevel.LOW,
            event_type=EventType.NEW_IP,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        # Count IP field occurrences
        ip_fields = [f for f in embed["fields"] if "IP Address" in f["name"]]
        assert len(ip_fields) == 1  # Should only appear once

    @pytest.mark.asyncio
    async def test_build_embed_suspicious_location(self, client):
        """Test embed building for suspicious location with IP."""
        # SUSPICIOUS_LOCATION isn't specifically handled but should still work
        metadata = {
            "ip_address": "10.0.0.1",
        }

        embed = client._build_embed(
            title="Suspicious Location",
            description="Suspicious location detected",
            severity=SeverityLevel.HIGH,
            event_type=EventType.SUSPICIOUS_LOCATION,
            user_email="user@example.com",
            metadata=metadata,
            fields=None,
            timestamp=datetime(2026, 3, 1, 2, 14, 0),
        )

        # Should still include IP address
        field_names = [f["name"] for f in embed["fields"]]
        assert "🌐 IP Address" in field_names
