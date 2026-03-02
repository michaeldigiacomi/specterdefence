"""Unit tests for alert engine."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.discord import DiscordWebhookError
from src.alerts.engine import AlertEngine
from src.models.alerts import (
    AlertHistoryModel,
    AlertRuleModel,
    AlertWebhookModel,
    EventType,
    SeverityLevel,
)


class TestAlertEngine:
    """Test cases for AlertEngine."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = AsyncMock()
        return db

    @pytest.fixture
    def engine(self, mock_db):
        """Create an AlertEngine instance."""
        return AlertEngine(mock_db)

    @pytest.mark.asyncio
    async def test_process_event_no_matching_rules(self, engine, mock_db):
        """Test processing event with no matching rules."""
        # Mock empty rules list
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await engine.process_event(
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            severity=SeverityLevel.HIGH,
            title="Test",
            description="Test desc",
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_process_event_with_matching_rules(self, engine, mock_db):
        """Test processing event with matching rules."""
        # Create mock rule
        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()
        rule.cooldown_minutes = 30

        # Create mock webhook
        webhook = MagicMock(spec=AlertWebhookModel)
        webhook.id = uuid4()
        webhook.webhook_url = "encrypted_url"

        # Mock rule service methods
        engine.rule_service.find_matching_rules = AsyncMock(return_value=[rule])
        engine.rule_service.list_webhooks = AsyncMock(return_value=[webhook])

        # Mock history query (no duplicate)
        mock_history_result = MagicMock()
        mock_history_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_history_result

        with patch.object(engine, '_send_alert', return_value={"status": "sent"}):
            results = await engine.process_event(
                event_type=EventType.IMPOSSIBLE_TRAVEL,
                severity=SeverityLevel.HIGH,
                title="Test",
                description="Test desc",
            )

        assert len(results) == 1
        assert results[0]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_process_event_duplicate_detected(self, engine, mock_db):
        """Test that duplicate events are skipped."""
        # Create mock rule
        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()
        rule.cooldown_minutes = 30

        # Create mock webhook (needed even though we won't send)
        webhook = MagicMock(spec=AlertWebhookModel)
        webhook.id = uuid4()
        webhook.webhook_url = "encrypted_url"

        # Mock rule service
        engine.rule_service.find_matching_rules = AsyncMock(return_value=[rule])
        engine.rule_service.list_webhooks = AsyncMock(return_value=[webhook])

        # Mock history query (found duplicate)
        mock_history = MagicMock(spec=AlertHistoryModel)
        mock_history_result = MagicMock()
        mock_history_result.scalar_one_or_none.return_value = mock_history
        mock_db.execute.return_value = mock_history_result

        results = await engine.process_event(
            event_type=EventType.IMPOSSIBLE_TRAVEL,
            severity=SeverityLevel.HIGH,
            title="Test",
            description="Test desc",
        )

        assert len(results) == 1
        assert results[0]["status"] == "skipped"
        assert results[0]["reason"] == "duplicate"

    @pytest.mark.asyncio
    async def test_check_duplicate_found(self, engine, mock_db):
        """Test duplicate check when duplicate exists."""
        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()
        rule.cooldown_minutes = 30

        # Mock history found
        mock_history = MagicMock(spec=AlertHistoryModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_history
        mock_db.execute.return_value = mock_result

        result = await engine._check_duplicate(
            dedup_hash="test_hash",
            rule=rule,
            tenant_id=None,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_duplicate_not_found(self, engine, mock_db):
        """Test duplicate check when no duplicate exists."""
        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()
        rule.cooldown_minutes = 30

        # Mock no history found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await engine._check_duplicate(
            dedup_hash="test_hash",
            rule=rule,
            tenant_id=None,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_success(self, engine, mock_db):
        """Test successful alert sending."""
        webhook = MagicMock(spec=AlertWebhookModel)
        webhook.id = uuid4()
        webhook.name = "Test Webhook"
        webhook.webhook_url = "encrypted_url"

        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()

        mock_client = AsyncMock()
        mock_client.send_alert = AsyncMock()

        with patch.object(engine, '_get_discord_client', return_value=mock_client):
            result = await engine._send_alert(
                webhook=webhook,
                rule=rule,
                event_type=EventType.IMPOSSIBLE_TRAVEL,
                severity=SeverityLevel.HIGH,
                title="Test Alert",
                description="Test description",
                user_email="user@example.com",
                tenant_id=None,
                metadata={},
                dedup_hash="hash123",
            )

        assert result["status"] == "sent"
        assert result["webhook_id"] == str(webhook.id)
        mock_client.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_webhook_error(self, engine, mock_db):
        """Test alert sending with webhook error."""
        webhook = MagicMock(spec=AlertWebhookModel)
        webhook.id = uuid4()
        webhook.name = "Test Webhook"
        webhook.webhook_url = "encrypted_url"

        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()

        mock_client = AsyncMock()
        mock_client.send_alert = AsyncMock(side_effect=DiscordWebhookError("Failed"))

        with patch.object(engine, '_get_discord_client', return_value=mock_client):
            result = await engine._send_alert(
                webhook=webhook,
                rule=rule,
                event_type=EventType.IMPOSSIBLE_TRAVEL,
                severity=SeverityLevel.HIGH,
                title="Test Alert",
                description="Test description",
                user_email=None,
                tenant_id=None,
                metadata={},
                dedup_hash="hash123",
            )

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_discord_client(self, engine):
        """Test getting/creating Discord client."""
        webhook = MagicMock(spec=AlertWebhookModel)
        webhook.id = uuid4()
        webhook.webhook_url = "encrypted_url"

        with patch('src.alerts.engine.encryption_service.decrypt', return_value='https://discord.com/webhook'):
            client1 = await engine._get_discord_client(webhook)
            client2 = await engine._get_discord_client(webhook)

        # Should return same cached client
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_record_alert(self, engine, mock_db):
        """Test recording alert history."""
        webhook = MagicMock(spec=AlertWebhookModel)
        webhook.id = uuid4()

        rule = MagicMock(spec=AlertRuleModel)
        rule.id = uuid4()

        result = await engine._record_alert(
            rule=rule,
            webhook=webhook,
            event_type=EventType.NEW_COUNTRY,
            severity=SeverityLevel.MEDIUM,
            title="Test Alert",
            description="Test description",
            user_email="user@example.com",
            tenant_id="tenant-123",
            metadata={"country": "FR"},
            dedup_hash="hash123",
        )

        assert isinstance(result, AlertHistoryModel)
        assert result.event_type == "new_country"
        assert result.severity == SeverityLevel.MEDIUM
        assert result.user_email == "user@example.com"
        assert result.tenant_id == "tenant-123"
        assert result.dedup_hash == "hash123"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alert_history(self, engine, mock_db):
        """Test getting alert history."""
        history1 = MagicMock(spec=AlertHistoryModel)
        history1.id = uuid4()
        history2 = MagicMock(spec=AlertHistoryModel)
        history2.id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [history1, history2]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await engine.get_alert_history(
            tenant_id="tenant-123",
            limit=10,
            offset=0,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_alert_history_with_filters(self, engine, mock_db):
        """Test getting filtered alert history."""
        history = MagicMock(spec=AlertHistoryModel)
        history.id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [history]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await engine.get_alert_history(
            tenant_id="tenant-123",
            event_type="impossible_travel",
            severity=SeverityLevel.HIGH,
            user_email="user@example.com",
            limit=5,
            offset=10,
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_close(self, engine):
        """Test closing the engine and clients."""
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()

        engine._discord_clients = {
            uuid4(): mock_client1,
            uuid4(): mock_client2,
        }

        await engine.close()

        mock_client1.close.assert_called_once()
        mock_client2.close.assert_called_once()
        assert len(engine._discord_clients) == 0
