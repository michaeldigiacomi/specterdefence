"""Unit tests for alert models."""

from datetime import UTC, datetime
from uuid import uuid4

from src.models.alerts import (
    EVENT_TYPE_NAMES,
    SEVERITY_COLORS,
    SEVERITY_EMOJIS,
    AlertHistoryModel,
    AlertRuleModel,
    AlertWebhookModel,
    EventType,
    SeverityLevel,
    WebhookType,
    utc_now,
)


class TestAlertWebhookModel:
    """Test cases for AlertWebhookModel."""

    def test_create_webhook(self):
        """Test creating an alert webhook model."""
        webhook = AlertWebhookModel(
            name="Test Webhook",
            webhook_url="encrypted_url",
            webhook_type=WebhookType.DISCORD,
            is_active=True,
        )

        assert webhook.name == "Test Webhook"
        assert webhook.webhook_url == "encrypted_url"
        assert webhook.webhook_type == WebhookType.DISCORD
        assert webhook.is_active is True
        assert webhook.tenant_id is None

    def test_webhook_with_tenant(self):
        """Test webhook with tenant ID."""
        tenant_id = str(uuid4())
        webhook = AlertWebhookModel(
            name="Tenant Webhook",
            webhook_url="encrypted_url",
            webhook_type=WebhookType.DISCORD,
            tenant_id=tenant_id,
        )

        assert webhook.tenant_id == tenant_id

    def test_webhook_types(self):
        """Test webhook type enum."""
        assert WebhookType.DISCORD.value == "discord"
        assert WebhookType.SLACK.value == "slack"


class TestAlertRuleModel:
    """Test cases for AlertRuleModel."""

    def test_create_rule(self):
        """Test creating an alert rule."""
        rule = AlertRuleModel(
            name="Impossible Travel Rule",
            event_types=[EventType.IMPOSSIBLE_TRAVEL.value],
            min_severity=SeverityLevel.HIGH,
            cooldown_minutes=30,
            is_active=True,
        )

        assert rule.name == "Impossible Travel Rule"
        assert rule.event_types == ["impossible_travel"]
        assert rule.min_severity == SeverityLevel.HIGH
        assert rule.cooldown_minutes == 30
        assert rule.is_active is True

    def test_rule_with_multiple_event_types(self):
        """Test rule with multiple event types."""
        rule = AlertRuleModel(
            name="Security Events",
            event_types=[
                EventType.IMPOSSIBLE_TRAVEL.value,
                EventType.NEW_COUNTRY.value,
                EventType.BRUTE_FORCE.value,
            ],
            min_severity=SeverityLevel.MEDIUM,
        )

        assert len(rule.event_types) == 3
        assert "impossible_travel" in rule.event_types

    def test_severity_levels(self):
        """Test severity level enum values."""
        assert SeverityLevel.LOW.value == "LOW"
        assert SeverityLevel.MEDIUM.value == "MEDIUM"
        assert SeverityLevel.HIGH.value == "HIGH"
        assert SeverityLevel.CRITICAL.value == "CRITICAL"


class TestAlertHistoryModel:
    """Test cases for AlertHistoryModel."""

    def test_create_history(self):
        """Test creating alert history."""
        history = AlertHistoryModel(
            webhook_id=uuid4(),
            severity=SeverityLevel.HIGH,
            event_type=EventType.IMPOSSIBLE_TRAVEL.value,
            title="Test Alert",
            message="Test message",
            dedup_hash="abc123",
        )

        assert history.severity == SeverityLevel.HIGH
        assert history.event_type == "impossible_travel"
        assert history.title == "Test Alert"
        assert history.dedup_hash == "abc123"

    def test_generate_dedup_hash_impossible_travel(self):
        """Test dedup hash for impossible travel."""
        metadata = {
            "previous_location": {
                "country": "US",
                "city": "New York",
            },
            "current_location": {
                "country": "JP",
                "city": "Tokyo",
            },
        }

        hash1 = AlertHistoryModel.generate_dedup_hash(
            event_type="impossible_travel",
            user_email="user@example.com",
            tenant_id="tenant-123",
            metadata=metadata,
        )

        hash2 = AlertHistoryModel.generate_dedup_hash(
            event_type="impossible_travel",
            user_email="user@example.com",
            tenant_id="tenant-123",
            metadata=metadata,
        )

        # Same inputs should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_generate_dedup_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = AlertHistoryModel.generate_dedup_hash(
            event_type="impossible_travel",
            user_email="user1@example.com",
            tenant_id="tenant-123",
            metadata={},
        )

        hash2 = AlertHistoryModel.generate_dedup_hash(
            event_type="impossible_travel",
            user_email="user2@example.com",
            tenant_id="tenant-123",
            metadata={},
        )

        # Different user should produce different hash
        assert hash1 != hash2

    def test_generate_dedup_hash_new_country(self):
        """Test dedup hash for new country event."""
        metadata = {
            "country_code": "FR",
            "known_countries": ["US", "UK"],
        }

        hash1 = AlertHistoryModel.generate_dedup_hash(
            event_type="new_country",
            user_email="user@example.com",
            tenant_id=None,
            metadata=metadata,
        )

        # Hash should include country code
        assert len(hash1) == 64

    def test_generate_dedup_hash_with_ip(self):
        """Test dedup hash includes IP address."""
        metadata = {
            "ip_address": "192.168.1.1",
        }

        hash1 = AlertHistoryModel.generate_dedup_hash(
            event_type="new_ip",
            user_email="user@example.com",
            tenant_id=None,
            metadata=metadata,
        )

        hash2 = AlertHistoryModel.generate_dedup_hash(
            event_type="new_ip",
            user_email="user@example.com",
            tenant_id=None,
            metadata={"ip_address": "192.168.1.2"},
        )

        # Different IPs should produce different hashes
        assert hash1 != hash2


class TestEventType:
    """Test cases for EventType enum."""

    def test_event_type_values(self):
        """Test event type enum values."""
        assert EventType.IMPOSSIBLE_TRAVEL.value == "impossible_travel"
        assert EventType.NEW_COUNTRY.value == "new_country"
        assert EventType.BRUTE_FORCE.value == "brute_force"
        assert EventType.ADMIN_ACTION.value == "admin_action"
        assert EventType.NEW_IP.value == "new_ip"
        assert EventType.MULTIPLE_FAILURES.value == "multiple_failures"
        assert EventType.SUSPICIOUS_LOCATION.value == "suspicious_location"

    def test_event_type_names(self):
        """Test event type display names."""
        assert EVENT_TYPE_NAMES[EventType.IMPOSSIBLE_TRAVEL] == "Impossible Travel"
        assert EVENT_TYPE_NAMES[EventType.NEW_COUNTRY] == "New Country Login"
        assert EVENT_TYPE_NAMES[EventType.BRUTE_FORCE] == "Brute Force Attack"


class TestSeverityHelpers:
    """Test cases for severity helper dictionaries."""

    def test_severity_colors(self):
        """Test severity color mappings."""
        assert SEVERITY_COLORS[SeverityLevel.LOW] == 3066993  # Green
        assert SEVERITY_COLORS[SeverityLevel.MEDIUM] == 16776960  # Yellow
        assert SEVERITY_COLORS[SeverityLevel.HIGH] == 15158332  # Orange
        assert SEVERITY_COLORS[SeverityLevel.CRITICAL] == 16711680  # Red

    def test_severity_emojis(self):
        """Test severity emoji mappings."""
        assert SEVERITY_EMOJIS[SeverityLevel.LOW] == "ℹ️"
        assert SEVERITY_EMOJIS[SeverityLevel.MEDIUM] == "⚠️"
        assert SEVERITY_EMOJIS[SeverityLevel.HIGH] == "🚨"
        assert SEVERITY_EMOJIS[SeverityLevel.CRITICAL] == "🔥"


class TestUtcNow:
    """Test cases for utc_now helper."""

    def test_utc_now_returns_datetime(self):
        """Test utc_now returns a datetime."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_utc_now_is_utc(self):
        """Test utc_now returns UTC datetime."""
        result = utc_now()
        assert result.tzinfo == UTC
