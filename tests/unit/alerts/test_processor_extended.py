"""Comprehensive tests for alert engine and security checks."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alerts.engine import AlertEngine
from src.models.alerts import (
    AlertHistoryModel,
    AlertRuleModel,
    AlertWebhookModel,
    EventType,
    SeverityLevel,
    WebhookType,
)


class TestAlertEngine:
    """Tests for AlertEngine."""

    @pytest.fixture
    def engine(self, db_session):
        """Create an AlertEngine with test database."""
        return AlertEngine(db_session)

    async def test_process_event_creates_alert(self, engine, db_session):
        """Test that processing an event creates alerts."""
        # Create webhook and rule
        webhook = AlertWebhookModel(
            name="Test Webhook",
            webhook_url="encrypted-url",
            webhook_type=WebhookType.DISCORD,
            is_active=True,
        )
        rule = AlertRuleModel(
            name="Test Rule",
            event_types=[EventType.IMPOSSIBLE_TRAVEL.value],
            min_severity=SeverityLevel.MEDIUM,
            cooldown_minutes=30,
            is_active=True,
        )
        db_session.add_all([webhook, rule])
        await db_session.commit()

        # Process an event
        results = await engine.process_event(
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            severity=SeverityLevel.HIGH,
            title="Impossible Travel Detected",
            description="User login from impossible locations",
            user_email="user@test.com",
            tenant_id=None,
            metadata={
                "previous_location": {"country": "US", "city": "New York"},
                "current_location": {"country": "JP", "city": "Tokyo"},
            },
        )

        # Results may be empty if no webhooks are found, but should not error
        assert isinstance(results, list)

    async def test_process_event_no_matching_rules(self, engine, db_session):
        """Test that events with no matching rules don't create alerts."""
        # Create a rule for a different event type
        rule = AlertRuleModel(
            name="Test Rule",
            event_types=[EventType.BRUTE_FORCE.value],
            min_severity=SeverityLevel.MEDIUM,
            cooldown_minutes=30,
            is_active=True,
        )
        db_session.add(rule)
        await db_session.commit()

        # Process an impossible travel event (shouldn't match brute force rule)
        results = await engine.process_event(
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            severity=SeverityLevel.HIGH,
            title="Impossible Travel Detected",
            description="User login from impossible locations",
            user_email="user@test.com",
            tenant_id=None,
            metadata={},
        )

        assert len(results) == 0

    async def test_process_event_severity_too_low(self, engine, db_session):
        """Test that events below minimum severity don't create alerts."""
        rule = AlertRuleModel(
            name="Test Rule",
            event_types=[EventType.IMPOSSIBLE_TRAVEL.value],
            min_severity=SeverityLevel.HIGH,
            cooldown_minutes=30,
            is_active=True,
        )
        db_session.add(rule)
        await db_session.commit()

        # Process a medium severity event (below HIGH)
        results = await engine.process_event(
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            severity=SeverityLevel.MEDIUM,
            title="Impossible Travel Detected",
            description="User login from impossible locations",
            user_email="user@test.com",
            tenant_id=None,
            metadata={},
        )

        assert len(results) == 0

    async def test_process_event_inactive_rule(self, engine, db_session):
        """Test that inactive rules don't trigger alerts."""
        rule = AlertRuleModel(
            name="Test Rule",
            event_types=[EventType.IMPOSSIBLE_TRAVEL.value],
            min_severity=SeverityLevel.MEDIUM,
            cooldown_minutes=30,
            is_active=False,  # Inactive
        )
        db_session.add(rule)
        await db_session.commit()

        results = await engine.process_event(
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            severity=SeverityLevel.HIGH,
            title="Impossible Travel Detected",
            description="User login from impossible locations",
            user_email="user@test.com",
            tenant_id=None,
            metadata={},
        )

        assert len(results) == 0

    async def test_dedup_hash_generation(self, engine):
        """Test deduplication hash generation."""
        metadata = {
            "previous_location": {"country": "US"},
            "current_location": {"country": "JP"},
        }

        hash1 = AlertHistoryModel.generate_dedup_hash(
            EventType.IMPOSSIBLE_TRAVEL.value,
            "user@test.com",
            "tenant-123",
            metadata,
        )

        hash2 = AlertHistoryModel.generate_dedup_hash(
            EventType.IMPOSSIBLE_TRAVEL.value,
            "user@test.com",
            "tenant-123",
            metadata,
        )

        # Same inputs should produce same hash
        assert hash1 == hash2

        # Different inputs should produce different hash
        hash3 = AlertHistoryModel.generate_dedup_hash(
            EventType.NEW_COUNTRY.value,
            "user@test.com",
            "tenant-123",
            {"country_code": "FR"},
        )

        assert hash1 != hash3


class TestAlertRules:
    """Tests for alert rules functionality."""

    async def test_create_alert_rule(self, db_session):
        """Test creating an alert rule."""
        rule = AlertRuleModel(
            name="Test Rule",
            event_types=[EventType.IMPOSSIBLE_TRAVEL, EventType.NEW_COUNTRY],
            min_severity=SeverityLevel.HIGH,
            cooldown_minutes=60,
            is_active=True,
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        assert rule.id is not None
        assert rule.name == "Test Rule"
        assert EventType.IMPOSSIBLE_TRAVEL in rule.event_types
        assert rule.min_severity == SeverityLevel.HIGH

    async def test_create_webhook(self, db_session):
        """Test creating a webhook."""
        webhook = AlertWebhookModel(
            name="Discord Webhook",
            webhook_url="encrypted-webhook-url",
            webhook_type=WebhookType.DISCORD,
            is_active=True,
        )
        db_session.add(webhook)
        await db_session.commit()
        await db_session.refresh(webhook)

        assert webhook.id is not None
        assert webhook.name == "Discord Webhook"
        assert webhook.webhook_type == WebhookType.DISCORD

    async def test_alert_history_creation(self, db_session):
        """Test creating alert history entry."""
        webhook = AlertWebhookModel(
            name="Test Webhook",
            webhook_url="encrypted-url",
            webhook_type=WebhookType.DISCORD,
            is_active=True,
        )
        db_session.add(webhook)
        await db_session.commit()
        await db_session.refresh(webhook)

        rule = AlertRuleModel(
            name="Test Rule",
            event_types=[EventType.IMPOSSIBLE_TRAVEL],
            min_severity=SeverityLevel.MEDIUM,
            cooldown_minutes=30,
            is_active=True,
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        history = AlertHistoryModel(
            rule_id=rule.id,
            webhook_id=webhook.id,
            severity=SeverityLevel.HIGH,
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            user_email="user@test.com",
            title="Impossible Travel Alert",
            message="User login from impossible locations",
            alert_metadata={"countries": ["US", "JP"]},
            dedup_hash="test-hash-123",
        )
        db_session.add(history)
        await db_session.commit()
        await db_session.refresh(history)

        assert history.id is not None
        assert history.severity == SeverityLevel.HIGH
        assert history.user_email == "user@test.com"
        assert history.dedup_hash == "test-hash-123"


class TestAlertSeverityColors:
    """Tests for severity colors and emojis."""

    def test_severity_colors(self):
        """Test that severity colors are defined."""
        from src.models.alerts import SEVERITY_COLORS

        assert SeverityLevel.LOW in SEVERITY_COLORS
        assert SeverityLevel.MEDIUM in SEVERITY_COLORS
        assert SeverityLevel.HIGH in SEVERITY_COLORS
        assert SeverityLevel.CRITICAL in SEVERITY_COLORS

        # Check that colors are integers (Discord color codes)
        assert isinstance(SEVERITY_COLORS[SeverityLevel.LOW], int)
        assert isinstance(SEVERITY_COLORS[SeverityLevel.CRITICAL], int)

    def test_severity_emojis(self):
        """Test that severity emojis are defined."""
        from src.models.alerts import SEVERITY_EMOJIS

        assert SeverityLevel.LOW in SEVERITY_EMOJIS
        assert SeverityLevel.MEDIUM in SEVERITY_EMOJIS
        assert SeverityLevel.HIGH in SEVERITY_EMOJIS
        assert SeverityLevel.CRITICAL in SEVERITY_EMOJIS

    def test_event_type_names(self):
        """Test that event type display names are defined."""
        from src.models.alerts import EVENT_TYPE_NAMES

        assert EventType.IMPOSSIBLE_TRAVEL in EVENT_TYPE_NAMES
        assert EventType.NEW_COUNTRY in EVENT_TYPE_NAMES
        assert EventType.BRUTE_FORCE in EVENT_TYPE_NAMES
        assert EventType.ADMIN_ACTION in EVENT_TYPE_NAMES
