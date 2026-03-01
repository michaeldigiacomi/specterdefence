"""Unit tests for alert rules service."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.rules import AlertRuleService, AlertRuleNotFoundError
from src.models.alerts import AlertWebhookModel, AlertRuleModel, SeverityLevel, EventType


class TestAlertRuleService:
    """Test cases for AlertRuleService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create an AlertRuleService instance."""
        return AlertRuleService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_webhook(self, service, mock_db):
        """Test creating a webhook."""
        with patch('src.alerts.rules.encryption_service.encrypt', return_value='encrypted_url'):
            webhook = await service.create_webhook(
                name="Test Webhook",
                webhook_url="https://discord.com/webhook",
                webhook_type="discord",
            )
        
        assert webhook.name == "Test Webhook"
        assert webhook.webhook_url == "encrypted_url"
        assert webhook.webhook_type == "discord"
        assert webhook.is_active is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_webhook_with_tenant(self, service, mock_db):
        """Test creating a tenant-specific webhook."""
        tenant_id = str(uuid4())
        
        with patch('src.alerts.rules.encryption_service.encrypt', return_value='encrypted_url'):
            webhook = await service.create_webhook(
                name="Tenant Webhook",
                webhook_url="https://discord.com/webhook",
                webhook_type="discord",
                tenant_id=tenant_id,
            )
        
        assert webhook.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_get_webhook_found(self, service, mock_db):
        """Test getting an existing webhook."""
        webhook_id = uuid4()
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_webhook
        mock_db.execute.return_value = mock_result
        
        result = await service.get_webhook(webhook_id)
        
        assert result == mock_webhook
    
    @pytest.mark.asyncio
    async def test_get_webhook_not_found(self, service, mock_db):
        """Test getting a non-existent webhook."""
        webhook_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.get_webhook(webhook_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_webhook_success(self, service, mock_db):
        """Test deleting an existing webhook."""
        webhook_id = uuid4()
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_webhook
        mock_db.execute.return_value = mock_result
        
        result = await service.delete_webhook(webhook_id)
        
        assert result is True
        mock_db.delete.assert_called_once_with(mock_webhook)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, service, mock_db):
        """Test deleting a non-existent webhook."""
        webhook_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.delete_webhook(webhook_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_webhook(self, service, mock_db):
        """Test updating a webhook."""
        webhook_id = uuid4()
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        mock_webhook.name = "Old Name"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_webhook
        mock_db.execute.return_value = mock_result
        
        with patch('src.alerts.rules.encryption_service.encrypt', return_value='new_encrypted_url'):
            result = await service.update_webhook(
                webhook_id,
                {"name": "New Name", "webhook_url": "https://new.url"}
            )
        
        assert result == mock_webhook
        assert mock_webhook.name == "New Name"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_decrypted_webhook_url(self, service):
        """Test decrypting webhook URL."""
        mock_webhook = MagicMock(spec=AlertWebhookModel)
        mock_webhook.webhook_url = "encrypted_url"
        
        with patch('src.alerts.rules.encryption_service.decrypt', return_value='https://discord.com/webhook'):
            result = await service.get_decrypted_webhook_url(mock_webhook)
        
        assert result == "https://discord.com/webhook"
    
    @pytest.mark.asyncio
    async def test_create_rule(self, service, mock_db):
        """Test creating an alert rule."""
        rule = await service.create_rule(
            name="Test Rule",
            event_types=["impossible_travel", "new_country"],
            min_severity="HIGH",
            cooldown_minutes=60,
        )
        
        assert rule.name == "Test Rule"
        assert rule.event_types == ["impossible_travel", "new_country"]
        assert rule.min_severity == SeverityLevel.HIGH
        assert rule.cooldown_minutes == 60
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_rule_default_cooldown(self, service, mock_db):
        """Test creating a rule with default cooldown."""
        rule = await service.create_rule(
            name="Default Rule",
            event_types=["brute_force"],
            min_severity="MEDIUM",
        )
        
        assert rule.cooldown_minutes == 30  # Default value
    
    @pytest.mark.asyncio
    async def test_get_rule_found(self, service, mock_db):
        """Test getting an existing rule."""
        rule_id = uuid4()
        mock_rule = MagicMock(spec=AlertRuleModel)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_db.execute.return_value = mock_result
        
        result = await service.get_rule(rule_id)
        
        assert result == mock_rule
    
    @pytest.mark.asyncio
    async def test_update_rule(self, service, mock_db):
        """Test updating a rule."""
        rule_id = uuid4()
        mock_rule = MagicMock(spec=AlertRuleModel)
        mock_rule.name = "Old Name"
        mock_rule.min_severity = SeverityLevel.LOW
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_db.execute.return_value = mock_result
        
        result = await service.update_rule(
            rule_id,
            {"name": "New Name", "min_severity": "critical", "is_active": False}
        )
        
        assert result == mock_rule
        assert mock_rule.name == "New Name"
        assert mock_rule.min_severity == "CRITICAL"  # Normalized to uppercase
        assert mock_rule.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_rule_success(self, service, mock_db):
        """Test deleting an existing rule."""
        rule_id = uuid4()
        mock_rule = MagicMock(spec=AlertRuleModel)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_db.execute.return_value = mock_result
        
        result = await service.delete_rule(rule_id)
        
        assert result is True
        mock_db.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_matching_rules(self, service, mock_db):
        """Test finding matching rules."""
        # Create mock rules
        rule1 = MagicMock(spec=AlertRuleModel)
        rule1.id = uuid4()
        rule1.min_severity = SeverityLevel.MEDIUM
        rule1.is_active = True
        rule1.event_types = ["impossible_travel"]
        
        rule2 = MagicMock(spec=AlertRuleModel)
        rule2.id = uuid4()
        rule2.min_severity = SeverityLevel.LOW
        rule2.is_active = True
        rule2.event_types = ["impossible_travel"]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [rule1, rule2]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        results = await service.find_matching_rules(
            event_type="impossible_travel",
            severity=SeverityLevel.HIGH,
        )
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_find_matching_rules_severity_filter(self, service, mock_db):
        """Test that rules are filtered by severity level."""
        # Create mock rules - only one should match based on severity
        rule1 = MagicMock(spec=AlertRuleModel)
        rule1.id = uuid4()
        rule1.min_severity = SeverityLevel.HIGH  # Requires HIGH or above
        rule1.is_active = True
        rule1.event_types = ["impossible_travel"]
        
        rule2 = MagicMock(spec=AlertRuleModel)
        rule2.id = uuid4()
        rule2.min_severity = SeverityLevel.CRITICAL  # Requires CRITICAL
        rule2.is_active = True
        rule2.event_types = ["impossible_travel"]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [rule1, rule2]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        # Event with HIGH severity - only rule1 should match
        results = await service.find_matching_rules(
            event_type="impossible_travel",
            severity=SeverityLevel.HIGH,
        )
        
        assert len(results) == 1
        assert results[0].id == rule1.id
    
    @pytest.mark.asyncio
    async def test_find_matching_rules_with_tenant(self, service, mock_db):
        """Test finding rules scoped to a tenant."""
        tenant_id = str(uuid4())
        
        rule1 = MagicMock(spec=AlertRuleModel)
        rule1.id = uuid4()
        rule1.min_severity = SeverityLevel.LOW
        rule1.is_active = True
        rule1.event_types = ["new_country"]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [rule1]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        results = await service.find_matching_rules(
            event_type="new_country",
            severity=SeverityLevel.MEDIUM,
            tenant_id=tenant_id,
        )
        
        assert len(results) == 1
