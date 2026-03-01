"""Unit tests for alert API endpoints."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

# Import models and schemas
from src.models.alerts import (
    AlertWebhookModel,
    AlertRuleModel,
    AlertHistoryModel,
    SeverityLevel,
    EventType,
)
from src.api.alerts import (
    WebhookCreate,
    RuleCreate,
    RuleUpdate,
)

# Import endpoint functions with aliases to avoid pytest collection issues
import src.api.alerts as alerts_api


class TestWebhookEndpoints:
    """Test cases for webhook API endpoints."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock rule service."""
        service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_create_webhook_success(self, mock_service):
        """Test successful webhook creation."""
        # Setup mock
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        mock_webhook.id = uuid4()
        mock_webhook.name = "Test Webhook"
        mock_webhook.webhook_type = "discord"
        mock_webhook.is_active = True
        mock_webhook.created_at = datetime.utcnow()
        
        mock_service.create_webhook.return_value = mock_webhook
        
        # Create request
        request = WebhookCreate(
            name="Test Webhook",
            webhook_url="https://discord.com/api/webhooks/123/test",
            webhook_type="discord",
        )
        
        # Call endpoint
        result = await alerts_api.create_webhook(
            webhook=request,
            tenant_id=None,
            service=mock_service,
        )
        
        # Verify
        assert result.name == "Test Webhook"
        assert result.webhook_type == "discord"
        assert result.is_active is True
        mock_service.create_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_webhook_with_tenant(self, mock_service):
        """Test webhook creation with tenant ID."""
        tenant_id = str(uuid4())
        
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        mock_webhook.id = uuid4()
        mock_webhook.name = "Tenant Webhook"
        mock_webhook.webhook_type = "discord"
        mock_webhook.is_active = True
        mock_webhook.created_at = datetime.utcnow()
        
        mock_service.create_webhook.return_value = mock_webhook
        
        request = WebhookCreate(
            name="Tenant Webhook",
            webhook_url="https://discord.com/api/webhooks/123/test",
        )
        
        result = await alerts_api.create_webhook(
            webhook=request,
            tenant_id=tenant_id,
            service=mock_service,
        )
        
        mock_service.create_webhook.assert_called_once_with(
            name="Tenant Webhook",
            webhook_url="https://discord.com/api/webhooks/123/test",
            webhook_type="discord",
            tenant_id=tenant_id,
        )
    
    @pytest.mark.asyncio
    async def test_create_webhook_error(self, mock_service):
        """Test webhook creation with error."""
        mock_service.create_webhook.side_effect = Exception("DB Error")
        
        request = WebhookCreate(
            name="Test Webhook",
            webhook_url="https://discord.com/api/webhooks/123/test",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.create_webhook(
                webhook=request,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to create webhook" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_list_webhooks(self, mock_service):
        """Test listing webhooks."""
        webhook1 = MagicMock(spec=AlertWebhookModel)
        webhook1.id = uuid4()
        webhook1.name = "Webhook 1"
        webhook1.webhook_type = "discord"
        webhook1.is_active = True
        webhook1.created_at = datetime.utcnow()
        
        webhook2 = MagicMock(spec=AlertWebhookModel)
        webhook2.id = uuid4()
        webhook2.name = "Webhook 2"
        webhook2.webhook_type = "slack"
        webhook2.is_active = True
        webhook2.created_at = datetime.utcnow()
        
        mock_service.list_webhooks.return_value = [webhook1, webhook2]
        
        result = await alerts_api.list_webhooks(
            tenant_id=None,
            include_inactive=False,
            service=mock_service,
        )
        
        assert len(result) == 2
        assert result[0].name == "Webhook 1"
        assert result[1].name == "Webhook 2"
    
    @pytest.mark.asyncio
    async def test_list_webhooks_with_tenant(self, mock_service):
        """Test listing webhooks with tenant filter."""
        mock_service.list_webhooks.return_value = []
        
        await alerts_api.list_webhooks(
            tenant_id="tenant-123",
            include_inactive=True,
            service=mock_service,
        )
        
        mock_service.list_webhooks.assert_called_once_with(
            tenant_id="tenant-123",
            include_inactive=True,
        )
    
    @pytest.mark.asyncio
    async def test_webhook_test_success(self, mock_service):
        """Test webhook testing endpoint - success."""
        
        webhook_id = uuid4()
        
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        mock_webhook.id = webhook_id
        mock_webhook.webhook_url = "encrypted_url"
        
        mock_service.get_webhook.return_value = mock_webhook
        
        with patch('src.services.encryption.encryption_service.decrypt', return_value='https://discord.com/webhook'):
            with patch('src.alerts.discord.DiscordWebhookClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.test_webhook.return_value = True
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client
                
                result = await alerts_api.test_webhook(
                    webhook_id=webhook_id,
                    service=mock_service,
                )
        
        assert result.success is True
        assert "successfully" in result.message
    
    @pytest.mark.asyncio
    async def test_webhook_test_failure(self, mock_service):
        """Test webhook testing endpoint - failure."""
        
        webhook_id = uuid4()
        
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        mock_webhook.id = webhook_id
        mock_webhook.webhook_url = "encrypted_url"
        
        mock_service.get_webhook.return_value = mock_webhook
        
        with patch('src.services.encryption.encryption_service.decrypt', return_value='https://discord.com/webhook'):
            with patch('src.alerts.discord.DiscordWebhookClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.test_webhook.return_value = False
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client
                
                result = await alerts_api.test_webhook(
                    webhook_id=webhook_id,
                    service=mock_service,
                )
        
        assert result.success is False
        assert "Failed" in result.message
    
    @pytest.mark.asyncio
    async def test_webhook_test_not_found(self, mock_service):
        """Test webhook testing endpoint - webhook not found."""
        
        webhook_id = uuid4()
        mock_service.get_webhook.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.test_webhook(
                webhook_id=webhook_id,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_delete_webhook_success(self, mock_service):
        """Test successful webhook deletion."""
        webhook_id = uuid4()
        mock_service.delete_webhook.return_value = True
        
        result = await alerts_api.delete_webhook(
            webhook_id=webhook_id,
            service=mock_service,
        )
        
        assert result is None  # Returns 204 No Content
        mock_service.delete_webhook.assert_called_once_with(webhook_id)
    
    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, mock_service):
        """Test webhook deletion - not found."""
        webhook_id = uuid4()
        mock_service.delete_webhook.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.delete_webhook(
                webhook_id=webhook_id,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 404


class TestRuleEndpoints:
    """Test cases for alert rule API endpoints."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock rule service."""
        service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_create_rule_success(self, mock_service):
        """Test successful rule creation."""
        mock_rule = MagicMock(spec=AlertRuleModel)
        mock_rule.id = uuid4()
        mock_rule.name = "Test Rule"
        mock_rule.event_types = ["impossible_travel", "new_country"]
        mock_rule.min_severity = SeverityLevel.HIGH
        mock_rule.cooldown_minutes = 30
        mock_rule.is_active = True
        mock_rule.created_at = datetime.utcnow()
        mock_rule.updated_at = datetime.utcnow()
        
        mock_service.create_rule.return_value = mock_rule
        
        request = RuleCreate(
            name="Test Rule",
            event_types=["impossible_travel", "new_country"],
            min_severity="HIGH",
            cooldown_minutes=30,
        )
        
        result = await alerts_api.create_rule(
            rule=request,
            tenant_id=None,
            service=mock_service,
        )
        
        assert result.name == "Test Rule"
        assert result.min_severity == "HIGH"
        mock_service.create_rule.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_rule_error(self, mock_service):
        """Test rule creation with error."""
        mock_service.create_rule.side_effect = Exception("DB Error")
        
        request = RuleCreate(
            name="Test Rule",
            event_types=["impossible_travel"],
            min_severity="HIGH",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.create_rule(
                rule=request,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_list_rules(self, mock_service):
        """Test listing rules."""
        rule1 = MagicMock(spec=AlertRuleModel)
        rule1.id = uuid4()
        rule1.name = "Rule 1"
        rule1.event_types = ["impossible_travel"]
        rule1.min_severity = SeverityLevel.HIGH
        rule1.cooldown_minutes = 30
        rule1.is_active = True
        rule1.created_at = datetime.utcnow()
        rule1.updated_at = datetime.utcnow()
        
        rule2 = MagicMock(spec=AlertRuleModel)
        rule2.id = uuid4()
        rule2.name = "Rule 2"
        rule2.event_types = ["new_country"]
        rule2.min_severity = SeverityLevel.MEDIUM
        rule2.cooldown_minutes = 60
        rule2.is_active = True
        rule2.created_at = datetime.utcnow()
        rule2.updated_at = datetime.utcnow()
        
        mock_service.list_rules.return_value = [rule1, rule2]
        
        result = await alerts_api.list_rules(
            tenant_id=None,
            include_inactive=False,
            service=mock_service,
        )
        
        assert len(result) == 2
        assert result[0].name == "Rule 1"
        assert result[1].name == "Rule 2"
    
    @pytest.mark.asyncio
    async def test_get_rule_success(self, mock_service):
        """Test getting a specific rule."""
        rule_id = uuid4()
        
        mock_rule = MagicMock(spec=AlertRuleModel)
        mock_rule.id = rule_id
        mock_rule.name = "Test Rule"
        mock_rule.event_types = ["impossible_travel"]
        mock_rule.min_severity = SeverityLevel.HIGH
        mock_rule.cooldown_minutes = 30
        mock_rule.is_active = True
        mock_rule.created_at = datetime.utcnow()
        mock_rule.updated_at = datetime.utcnow()
        
        mock_service.get_rule.return_value = mock_rule
        
        result = await alerts_api.get_rule(
            rule_id=rule_id,
            service=mock_service,
        )
        
        assert result.name == "Test Rule"
        assert result.id == rule_id
    
    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, mock_service):
        """Test getting a non-existent rule."""
        rule_id = uuid4()
        mock_service.get_rule.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.get_rule(
                rule_id=rule_id,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_rule_success(self, mock_service):
        """Test successful rule update."""
        rule_id = uuid4()
        
        mock_rule = MagicMock(spec=AlertRuleModel)
        mock_rule.id = rule_id
        mock_rule.name = "Updated Rule"
        mock_rule.event_types = ["impossible_travel"]
        mock_rule.min_severity = SeverityLevel.CRITICAL
        mock_rule.cooldown_minutes = 15
        mock_rule.is_active = True
        mock_rule.created_at = datetime.utcnow()
        mock_rule.updated_at = datetime.utcnow()
        
        mock_service.update_rule.return_value = mock_rule
        
        updates = RuleUpdate(
            name="Updated Rule",
            min_severity="CRITICAL",
            cooldown_minutes=15,
        )
        
        result = await alerts_api.update_rule(
            rule_id=rule_id,
            updates=updates,
            service=mock_service,
        )
        
        assert result.name == "Updated Rule"
        assert result.min_severity == "CRITICAL"
    
    @pytest.mark.asyncio
    async def test_update_rule_not_found(self, mock_service):
        """Test updating a non-existent rule."""
        rule_id = uuid4()
        mock_service.update_rule.return_value = None
        
        updates = RuleUpdate(name="Updated Rule")
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.update_rule(
                rule_id=rule_id,
                updates=updates,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_rule_no_fields(self, mock_service):
        """Test updating with no fields."""
        rule_id = uuid4()
        updates = RuleUpdate()
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.update_rule(
                rule_id=rule_id,
                updates=updates,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 400
        assert "No fields to update" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_delete_rule_success(self, mock_service):
        """Test successful rule deletion."""
        rule_id = uuid4()
        mock_service.delete_rule.return_value = True
        
        result = await alerts_api.delete_rule(
            rule_id=rule_id,
            service=mock_service,
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self, mock_service):
        """Test deleting a non-existent rule."""
        rule_id = uuid4()
        mock_service.delete_rule.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.delete_rule(
                rule_id=rule_id,
                service=mock_service,
            )
        
        assert exc_info.value.status_code == 404


class TestAlertHistoryEndpoints:
    """Test cases for alert history API endpoints."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock alert engine."""
        engine = AsyncMock()
        return engine
    
    @pytest.mark.asyncio
    async def test_get_alert_history(self, mock_engine):
        """Test getting alert history."""
        history1 = MagicMock(spec=AlertHistoryModel)
        history1.id = uuid4()
        history1.rule_id = uuid4()
        history1.webhook_id = uuid4()
        history1.severity = SeverityLevel.HIGH
        history1.event_type = "impossible_travel"
        history1.user_email = "user@example.com"
        history1.title = "Test Alert"
        history1.message = "Test message"
        history1.alert_metadata = {}
        history1.sent_at = datetime.utcnow()
        
        mock_engine.get_alert_history.return_value = [history1]
        
        result = await alerts_api.get_alert_history(
            tenant_id=None,
            event_type=None,
            severity=None,
            user_email=None,
            limit=100,
            offset=0,
            engine=mock_engine,
        )
        
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].title == "Test Alert"
    
    @pytest.mark.asyncio
    async def test_get_alert_history_with_filters(self, mock_engine):
        """Test getting alert history with filters."""
        mock_engine.get_alert_history.return_value = []
        
        result = await alerts_api.get_alert_history(
            tenant_id="tenant-123",
            event_type="impossible_travel",
            severity="HIGH",
            user_email="user@example.com",
            limit=50,
            offset=10,
            engine=mock_engine,
        )
        
        mock_engine.get_alert_history.assert_called_once()
        call_args = mock_engine.get_alert_history.call_args
        assert call_args[1]["tenant_id"] == "tenant-123"
        assert call_args[1]["event_type"] == "impossible_travel"
        assert call_args[1]["severity"] == SeverityLevel.HIGH
        assert call_args[1]["user_email"] == "user@example.com"
        assert call_args[1]["limit"] == 50
        assert call_args[1]["offset"] == 10
    
    @pytest.mark.asyncio
    async def test_get_alert_history_invalid_severity(self, mock_engine):
        """Test getting alert history with invalid severity."""
        with pytest.raises(HTTPException) as exc_info:
            await alerts_api.get_alert_history(
                tenant_id=None,
                event_type=None,
                severity="INVALID",
                user_email=None,
                limit=100,
                offset=0,
                engine=mock_engine,
            )
        
        assert exc_info.value.status_code == 400
        assert "Invalid severity" in exc_info.value.detail
