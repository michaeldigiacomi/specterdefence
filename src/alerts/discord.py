"""Discord webhook client for sending alerts."""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.models.alerts import (
    EVENT_TYPE_NAMES,
    SEVERITY_COLORS,
    SEVERITY_EMOJIS,
    EventType,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class DiscordWebhookError(Exception):
    """Exception raised when Discord webhook fails."""

    pass


class DiscordWebhookClient:
    """Client for sending alerts to Discord via webhooks."""

    def __init__(self, webhook_url: str, timeout: float = 30.0):
        """Initialize Discord webhook client.

        Args:
            webhook_url: The Discord webhook URL
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_alert(
        self,
        title: str,
        description: str,
        severity: SeverityLevel,
        event_type: EventType,
        user_email: str | None = None,
        metadata: dict[str, Any] | None = None,
        fields: list[dict[str, Any]] | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        """Send an alert to Discord.

        Args:
            title: Alert title
            description: Alert description
            severity: Severity level
            event_type: Type of event
            user_email: User email (optional)
            metadata: Additional metadata (optional)
            fields: Additional Discord embed fields (optional)
            timestamp: Alert timestamp (optional, defaults to now)

        Returns:
            True if sent successfully, False otherwise

        Raises:
            DiscordWebhookError: If the webhook request fails
        """
        embed = self._build_embed(
            title=title,
            description=description,
            severity=severity,
            event_type=event_type,
            user_email=user_email,
            metadata=metadata,
            fields=fields,
            timestamp=timestamp or datetime.utcnow(),
        )

        payload = {"embeds": [embed]}

        try:
            client = await self._get_client()
            response = await client.post(
                self.webhook_url, json=payload, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            logger.info(f"Discord alert sent successfully: {title}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Discord webhook HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise DiscordWebhookError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            logger.error(f"Discord webhook request error: {e}")
            raise DiscordWebhookError(f"Request failed: {e}") from e
        except Exception as e:
            logger.error(f"Discord webhook unexpected error: {e}")
            raise DiscordWebhookError(f"Unexpected error: {e}") from e

    def _build_embed(
        self,
        title: str,
        description: str,
        severity: SeverityLevel,
        event_type: EventType,
        user_email: str | None,
        metadata: dict[str, Any] | None,
        fields: list[dict[str, Any]] | None,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Build a Discord embed for an alert.

        Args:
            title: Alert title
            description: Alert description
            severity: Severity level
            event_type: Type of event
            user_email: User email
            metadata: Additional metadata
            fields: Additional fields
            timestamp: Alert timestamp

        Returns:
            Discord embed dictionary
        """
        event_name = EVENT_TYPE_NAMES.get(event_type, event_type.value)
        emoji = SEVERITY_EMOJIS.get(severity, "⚠️")
        color = SEVERITY_COLORS.get(severity, 15158332)

        embed: dict[str, Any] = {
            "title": f"{emoji} {title}",
            "description": description,
            "color": color,
            "timestamp": timestamp.isoformat() + "Z",
            "footer": {"text": f"SpecterDefence • {event_name}"},
        }

        # Build fields list
        embed_fields = []

        # Add user field if present
        if user_email:
            embed_fields.append({"name": "👤 User", "value": user_email, "inline": True})

        # Add severity field
        embed_fields.append({"name": "⚡ Severity", "value": severity.value, "inline": True})

        # Add metadata fields based on event type
        if metadata:
            metadata_fields = self._build_metadata_fields(event_type, metadata)
            embed_fields.extend(metadata_fields)

        # Add custom fields
        if fields:
            embed_fields.extend(fields)

        if embed_fields:
            embed["fields"] = embed_fields

        return embed

    def _build_metadata_fields(
        self, event_type: EventType, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Build embed fields based on event metadata.

        Args:
            event_type: Type of event
            metadata: Event metadata

        Returns:
            List of Discord embed fields
        """
        fields = []

        if event_type == EventType.IMPOSSIBLE_TRAVEL:
            # Add distance and time info
            distance = metadata.get("distance_km")
            time_diff = metadata.get("time_diff_minutes")
            min_travel = metadata.get("min_travel_time_minutes")

            if distance:
                fields.append({"name": "📏 Distance", "value": f"{distance:.0f} km", "inline": True})

            if time_diff and min_travel:
                fields.append(
                    {
                        "name": "⏱️ Time",
                        "value": f"{time_diff:.0f} min (need {min_travel:.0f})",
                        "inline": True,
                    }
                )

            # Add location info
            prev_loc = metadata.get("previous_location", {})
            curr_loc = metadata.get("current_location", {})

            prev_str = self._format_location(prev_loc)
            curr_str = self._format_location(curr_loc)

            fields.append(
                {"name": "🌍 Locations", "value": f"{prev_str} → {curr_str}", "inline": False}
            )

            # Add risk score if present
            risk_score = metadata.get("risk_score")
            if risk_score is not None:
                fields.append(
                    {"name": "🎯 Risk Score", "value": f"{risk_score}/100", "inline": True}
                )

        elif event_type == EventType.NEW_COUNTRY:
            country = metadata.get("country_code")
            known = metadata.get("known_countries", [])

            if country:
                fields.append({"name": "🏳️ New Country", "value": country, "inline": True})

            if known:
                known_str = ", ".join(known[:5])  # Limit to first 5
                if len(known) > 5:
                    known_str += f" (+{len(known) - 5} more)"
                fields.append(
                    {"name": "📋 Known Countries", "value": known_str or "None", "inline": True}
                )

            is_first = metadata.get("is_first_login", False)
            if is_first:
                fields.append(
                    {
                        "name": "🆕 First Login",
                        "value": "This is the user's first login",
                        "inline": False,
                    }
                )

        elif event_type == EventType.BRUTE_FORCE or event_type == EventType.MULTIPLE_FAILURES:
            recent_failures = metadata.get("recent_failures", 0)
            if recent_failures:
                fields.append(
                    {
                        "name": "❌ Failed Attempts (24h)",
                        "value": str(recent_failures),
                        "inline": True,
                    }
                )

            failure_reason = metadata.get("failure_reason")
            if failure_reason:
                fields.append({"name": "📝 Failure Reason", "value": failure_reason, "inline": True})

        elif event_type == EventType.ADMIN_ACTION:
            action = metadata.get("action")
            target = metadata.get("target")

            if action:
                fields.append({"name": "⚙️ Action", "value": action, "inline": True})

            if target:
                fields.append({"name": "🎯 Target", "value": target, "inline": True})

        elif event_type == EventType.NEW_IP:
            ip = metadata.get("ip_address")
            known_count = metadata.get("known_ips_count", 0)

            if ip:
                fields.append({"name": "🌐 IP Address", "value": f"`{ip}`", "inline": True})

            fields.append({"name": "📊 Known IPs", "value": str(known_count), "inline": True})

        # Add IP address if present and not already added
        ip = metadata.get("ip_address")
        if ip and not any(f.get("name") == "🌐 IP Address" for f in fields):
            fields.append({"name": "🌐 IP Address", "value": f"`{ip}`", "inline": True})

        return fields

    @staticmethod
    def _format_location(location: dict[str, Any]) -> str:
        """Format a location dictionary as a string.

        Args:
            location: Location dictionary with city, country, etc.

        Returns:
            Formatted location string
        """
        city = location.get("city")
        country = location.get("country")

        if city and country:
            return f"{city}, {country}"
        elif city:
            return city
        elif country:
            return country
        else:
            return "Unknown"

    async def test_webhook(self) -> bool:
        """Test the webhook by sending a test message.

        Returns:
            True if webhook is working, False otherwise
        """
        try:
            await self.send_alert(
                title="Webhook Test",
                description="This is a test alert from SpecterDefence. Your webhook is configured correctly! 🎉",
                severity=SeverityLevel.LOW,
                event_type=EventType.ADMIN_ACTION,
                metadata={"action": "webhook_test"},
            )
            return True
        except DiscordWebhookError:
            return False
