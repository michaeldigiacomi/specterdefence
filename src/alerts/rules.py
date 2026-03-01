"""Alert rule management for SpecterDefence."""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alerts import (
    AlertRuleModel,
    AlertWebhookModel,
    SeverityLevel,
    EventType,
)
from src.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class AlertRuleNotFoundError(Exception):
    """Exception raised when an alert rule is not found."""
    pass


class AlertWebhookNotFoundError(Exception):
    """Exception raised when an alert webhook is not found."""
    pass


class AlertRuleService:
    """Service for managing alert rules and webhooks."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the alert rule service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    # Webhook Management
    
    async def create_webhook(
        self,
        name: str,
        webhook_url: str,
        webhook_type: str = "discord",
        tenant_id: Optional[str] = None,
    ) -> AlertWebhookModel:
        """Create a new alert webhook.
        
        Args:
            name: Display name for the webhook
            webhook_url: The webhook URL
            webhook_type: Type of webhook (discord, slack)
            tenant_id: Optional tenant ID (null for global)
            
        Returns:
            Created webhook model
        """
        # Encrypt the webhook URL
        encrypted_url = encryption_service.encrypt(webhook_url)
        
        webhook = AlertWebhookModel(
            name=name,
            webhook_url=encrypted_url,
            webhook_type=webhook_type.lower(),
            tenant_id=tenant_id,
            is_active=True,
        )
        
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        
        logger.info(f"Created webhook: {webhook.id} ({name})")
        return webhook
    
    async def get_webhook(self, webhook_id: UUID) -> Optional[AlertWebhookModel]:
        """Get a webhook by ID.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            Webhook model or None if not found
        """
        result = await self.db.execute(
            select(AlertWebhookModel).where(AlertWebhookModel.id == webhook_id)
        )
        return result.scalar_one_or_none()
    
    async def list_webhooks(
        self,
        tenant_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[AlertWebhookModel]:
        """List webhooks.
        
        Args:
            tenant_id: Filter by tenant ID (None for global webhooks)
            include_inactive: Include inactive webhooks
            
        Returns:
            List of webhook models
        """
        query = select(AlertWebhookModel)
        
        # Filter by tenant (None = global, specific = tenant-specific)
        if tenant_id is not None:
            query = query.where(
                or_(
                    AlertWebhookModel.tenant_id == tenant_id,
                    AlertWebhookModel.tenant_id.is_(None)
                )
            )
        
        if not include_inactive:
            query = query.where(AlertWebhookModel.is_active.is_(True))
        
        query = query.order_by(AlertWebhookModel.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def delete_webhook(self, webhook_id: UUID) -> bool:
        """Delete a webhook.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            True if deleted, False if not found
        """
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return False
        
        await self.db.delete(webhook)
        await self.db.commit()
        
        logger.info(f"Deleted webhook: {webhook_id}")
        return True
    
    async def update_webhook(
        self,
        webhook_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[AlertWebhookModel]:
        """Update a webhook.
        
        Args:
            webhook_id: Webhook UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated webhook model or None if not found
        """
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return None
        
        # Encrypt webhook URL if being updated
        if "webhook_url" in updates:
            updates["webhook_url"] = encryption_service.encrypt(updates["webhook_url"])
        
        for field, value in updates.items():
            if hasattr(webhook, field):
                setattr(webhook, field, value)
        
        await self.db.commit()
        await self.db.refresh(webhook)
        
        logger.info(f"Updated webhook: {webhook_id}")
        return webhook
    
    async def get_decrypted_webhook_url(self, webhook: AlertWebhookModel) -> str:
        """Get the decrypted webhook URL.
        
        Args:
            webhook: Webhook model
            
        Returns:
            Decrypted webhook URL
        """
        return encryption_service.decrypt(webhook.webhook_url)
    
    # Rule Management
    
    async def create_rule(
        self,
        name: str,
        event_types: List[str],
        min_severity: str,
        cooldown_minutes: int = 30,
        tenant_id: Optional[str] = None,
    ) -> AlertRuleModel:
        """Create a new alert rule.
        
        Args:
            name: Display name for the rule
            event_types: List of event types to match
            min_severity: Minimum severity level to trigger
            cooldown_minutes: Cooldown period for deduplication
            tenant_id: Optional tenant ID (null for global)
            
        Returns:
            Created rule model
        """
        rule = AlertRuleModel(
            name=name,
            event_types=event_types,
            min_severity=min_severity.upper(),
            cooldown_minutes=cooldown_minutes,
            tenant_id=tenant_id,
            is_active=True,
        )
        
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        
        logger.info(f"Created alert rule: {rule.id} ({name})")
        return rule
    
    async def get_rule(self, rule_id: UUID) -> Optional[AlertRuleModel]:
        """Get a rule by ID.
        
        Args:
            rule_id: Rule UUID
            
        Returns:
            Rule model or None if not found
        """
        result = await self.db.execute(
            select(AlertRuleModel).where(AlertRuleModel.id == rule_id)
        )
        return result.scalar_one_or_none()
    
    async def list_rules(
        self,
        tenant_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[AlertRuleModel]:
        """List alert rules.
        
        Args:
            tenant_id: Filter by tenant ID (None for global rules)
            include_inactive: Include inactive rules
            
        Returns:
            List of rule models
        """
        query = select(AlertRuleModel)
        
        # Filter by tenant (None = global, specific = tenant-specific)
        if tenant_id is not None:
            query = query.where(
                or_(
                    AlertRuleModel.tenant_id == tenant_id,
                    AlertRuleModel.tenant_id.is_(None)
                )
            )
        
        if not include_inactive:
            query = query.where(AlertRuleModel.is_active.is_(True))
        
        query = query.order_by(AlertRuleModel.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_rule(
        self,
        rule_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[AlertRuleModel]:
        """Update an alert rule.
        
        Args:
            rule_id: Rule UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated rule model or None if not found
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        
        # Normalize severity to uppercase
        if "min_severity" in updates:
            updates["min_severity"] = updates["min_severity"].upper()
        
        for field, value in updates.items():
            if hasattr(rule, field):
                setattr(rule, field, value)
        
        await self.db.commit()
        await self.db.refresh(rule)
        
        logger.info(f"Updated alert rule: {rule_id}")
        return rule
    
    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete an alert rule.
        
        Args:
            rule_id: Rule UUID
            
        Returns:
            True if deleted, False if not found
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return False
        
        await self.db.delete(rule)
        await self.db.commit()
        
        logger.info(f"Deleted alert rule: {rule_id}")
        return True
    
    async def find_matching_rules(
        self,
        event_type: str,
        severity: SeverityLevel,
        tenant_id: Optional[str] = None,
    ) -> List[AlertRuleModel]:
        """Find rules that match an event.
        
        Args:
            event_type: Type of event
            severity: Severity level of the event
            tenant_id: Optional tenant ID
            
        Returns:
            List of matching rule models
        """
        # Get severity order for comparison
        severity_order = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        
        event_severity_level = severity_order.get(severity, 0)
        
        # Build query
        query = select(AlertRuleModel).where(
            and_(
                AlertRuleModel.is_active.is_(True),
                AlertRuleModel.event_types.contains([event_type]),
            )
        )
        
        # Filter by tenant (get global rules and tenant-specific rules)
        if tenant_id is not None:
            query = query.where(
                or_(
                    AlertRuleModel.tenant_id == tenant_id,
                    AlertRuleModel.tenant_id.is_(None)
                )
            )
        
        result = await self.db.execute(query)
        rules = result.scalars().all()
        
        # Filter by severity level (only rules with min_severity <= event severity)
        matching_rules = []
        for rule in rules:
            rule_severity_level = severity_order.get(rule.min_severity, 0)
            if rule_severity_level <= event_severity_level:
                matching_rules.append(rule)
        
        return matching_rules
