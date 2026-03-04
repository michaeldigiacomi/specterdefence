"""Alert engine with deduplication for SpecterDefence."""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.discord import DiscordWebhookClient, DiscordWebhookError
from src.alerts.rules import AlertRuleService
from src.models.alerts import (
    AlertHistoryModel,
    AlertRuleModel,
    AlertWebhookModel,
    EventType,
    SeverityLevel,
)
from src.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class AlertEngine:
    """Alert processing engine with deduplication."""

    def __init__(self, db: AsyncSession):
        """Initialize the alert engine.

        Args:
            db: Database session
        """
        self.db = db
        self.rule_service = AlertRuleService(db)
        self._discord_clients: dict[UUID, DiscordWebhookClient] = {}

    async def process_event(
        self,
        event_type: EventType,
        severity: SeverityLevel,
        title: str,
        description: str,
        user_email: str | None = None,
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Process a security event and send alerts.

        This method:
        1. Finds matching alert rules
        2. Checks deduplication
        3. Sends alerts to configured webhooks
        4. Records alert history

        Args:
            event_type: Type of security event
            severity: Severity level
            title: Alert title
            description: Alert description
            user_email: User email (optional)
            tenant_id: Tenant ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            List of alert results with status for each webhook
        """
        results = []
        metadata = metadata or {}

        # Find matching rules
        matching_rules = await self.rule_service.find_matching_rules(
            event_type=event_type.value,
            severity=severity,
            tenant_id=tenant_id,
        )

        if not matching_rules:
            logger.debug(f"No matching rules for event: {event_type.value}")
            return results

        logger.info(f"Found {len(matching_rules)} matching rules for {event_type.value}")

        # Get active webhooks for this tenant (including global webhooks)
        webhooks = await self.rule_service.list_webhooks(
            tenant_id=tenant_id,
            include_inactive=False,
        )

        if not webhooks:
            logger.warning(f"No active webhooks found for tenant: {tenant_id}")
            return results

        # Generate deduplication hash
        dedup_hash = AlertHistoryModel.generate_dedup_hash(
            event_type=event_type.value,
            user_email=user_email,
            tenant_id=tenant_id,
            metadata=metadata,
        )

        # Process each rule
        for rule in matching_rules:
            # Check deduplication for this rule
            is_duplicate = await self._check_duplicate(
                dedup_hash=dedup_hash,
                rule=rule,
                tenant_id=tenant_id,
            )

            if is_duplicate:
                logger.info(f"Skipping duplicate alert for rule {rule.id}")
                results.append(
                    {
                        "rule_id": str(rule.id),
                        "status": "skipped",
                        "reason": "duplicate",
                        "webhook_id": None,
                    }
                )
                continue

            # Send alert to all webhooks
            for webhook in webhooks:
                result = await self._send_alert(
                    webhook=webhook,
                    rule=rule,
                    event_type=event_type,
                    severity=severity,
                    title=title,
                    description=description,
                    user_email=user_email,
                    tenant_id=tenant_id,
                    metadata=metadata,
                    dedup_hash=dedup_hash,
                )
                results.append(result)

        return results

    async def _check_duplicate(
        self,
        dedup_hash: str,
        rule: AlertRuleModel,
        tenant_id: str | None,
    ) -> bool:
        """Check if an alert is a duplicate within the cooldown period.

        Args:
            dedup_hash: Deduplication hash
            rule: Alert rule
            tenant_id: Tenant ID

        Returns:
            True if this is a duplicate alert, False otherwise
        """
        cooldown_until = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)

        query = select(AlertHistoryModel).where(
            and_(
                AlertHistoryModel.dedup_hash == dedup_hash,
                AlertHistoryModel.sent_at >= cooldown_until,
                AlertHistoryModel.rule_id == rule.id,
            )
        )

        # Also match tenant for proper scoping
        if tenant_id:
            query = query.where(
                or_(AlertHistoryModel.tenant_id == tenant_id, AlertHistoryModel.tenant_id.is_(None))
            )

        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        return existing is not None

    async def _send_alert(
        self,
        webhook: AlertWebhookModel,
        rule: AlertRuleModel,
        event_type: EventType,
        severity: SeverityLevel,
        title: str,
        description: str,
        user_email: str | None,
        tenant_id: str | None,
        metadata: dict[str, Any],
        dedup_hash: str,
    ) -> dict[str, Any]:
        """Send an alert to a webhook and record history.

        Args:
            webhook: Webhook configuration
            rule: Alert rule that triggered
            event_type: Type of event
            severity: Severity level
            title: Alert title
            description: Alert description
            user_email: User email
            tenant_id: Tenant ID
            metadata: Event metadata
            dedup_hash: Deduplication hash

        Returns:
            Result dictionary with status
        """
        result = {
            "rule_id": str(rule.id),
            "webhook_id": str(webhook.id),
            "webhook_name": webhook.name,
            "status": "pending",
        }

        try:
            # Get or create Discord client
            client = await self._get_discord_client(webhook)

            # Send the alert
            await client.send_alert(
                title=title,
                description=description,
                severity=severity,
                event_type=event_type,
                user_email=user_email,
                metadata=metadata,
            )

            # Record successful alert
            await self._record_alert(
                rule=rule,
                webhook=webhook,
                event_type=event_type,
                severity=severity,
                title=title,
                description=description,
                user_email=user_email,
                tenant_id=tenant_id,
                metadata=metadata,
                dedup_hash=dedup_hash,
            )

            result["status"] = "sent"
            logger.info(f"Alert sent successfully to webhook {webhook.id}")

        except DiscordWebhookError as e:
            logger.error(f"Failed to send alert to webhook {webhook.id}: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error sending alert: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _get_discord_client(self, webhook: AlertWebhookModel) -> DiscordWebhookClient:
        """Get or create a Discord client for a webhook.

        Args:
            webhook: Webhook configuration

        Returns:
            DiscordWebhookClient instance
        """
        if webhook.id not in self._discord_clients:
            decrypted_url = encryption_service.decrypt(webhook.webhook_url)
            self._discord_clients[webhook.id] = DiscordWebhookClient(decrypted_url)

        return self._discord_clients[webhook.id]

    async def _record_alert(
        self,
        rule: AlertRuleModel,
        webhook: AlertWebhookModel,
        event_type: EventType,
        severity: SeverityLevel,
        title: str,
        description: str,
        user_email: str | None,
        tenant_id: str | None,
        metadata: dict[str, Any],
        dedup_hash: str,
    ) -> AlertHistoryModel:
        """Record an alert in the history.

        Args:
            rule: Alert rule
            webhook: Webhook used
            event_type: Type of event
            severity: Severity level
            title: Alert title
            description: Alert description
            user_email: User email
            tenant_id: Tenant ID
            metadata: Event metadata
            dedup_hash: Deduplication hash

        Returns:
            Created alert history record
        """
        history = AlertHistoryModel(
            rule_id=rule.id,
            webhook_id=webhook.id,
            tenant_id=tenant_id,
            severity=severity,
            event_type=event_type.value,
            user_email=user_email,
            title=title,
            message=description,
            alert_metadata=metadata,
            dedup_hash=dedup_hash,
        )

        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)

        return history

    async def get_alert_history(
        self,
        tenant_id: str | None = None,
        event_type: str | None = None,
        severity: SeverityLevel | None = None,
        user_email: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AlertHistoryModel]:
        """Get alert history with optional filtering.

        Args:
            tenant_id: Filter by tenant
            event_type: Filter by event type
            severity: Filter by severity
            user_email: Filter by user email
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of alert history records
        """
        query = select(AlertHistoryModel)

        # Apply filters
        if tenant_id:
            query = query.where(
                or_(AlertHistoryModel.tenant_id == tenant_id, AlertHistoryModel.tenant_id.is_(None))
            )

        if event_type:
            query = query.where(AlertHistoryModel.event_type == event_type)

        if severity:
            query = query.where(AlertHistoryModel.severity == severity)

        if user_email:
            query = query.where(AlertHistoryModel.user_email == user_email)

        # Order by sent_at descending (newest first)
        query = query.order_by(desc(AlertHistoryModel.sent_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def close(self) -> None:
        """Close all webhook clients."""
        for client in self._discord_clients.values():
            await client.close()
        self._discord_clients.clear()
