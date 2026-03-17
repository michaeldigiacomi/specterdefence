"""Mailbox rule monitoring service for SpecterDefence."""

import contextlib
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.engine import AlertEngine
from src.clients.mailbox_rules import MailboxRuleClient
from src.clients.ms_graph import MSGraphClient
from src.models.alerts import EventType, SeverityLevel
from src.models.db import TenantModel
from src.models.mailbox_rules import (
    MailboxRuleAlertModel,
    MailboxRuleModel,
    RuleSeverity,
    RuleStatus,
    RuleType,
)
from src.services.credential_manager import CredentialStorageManager

logger = logging.getLogger(__name__)


class MailboxRuleService:
    """Service for monitoring and managing mailbox rules."""

    # Event types for mailbox rule alerts
    EVENT_TYPE_FORWARDING_EXTERNAL = "mailbox_forwarding_external"
    EVENT_TYPE_REDIRECT_HIDDEN = "mailbox_redirect_hidden"
    EVENT_TYPE_SUSPICIOUS_AUTO_REPLY = "mailbox_suspicious_auto_reply"
    EVENT_TYPE_RULE_CREATED_NON_OWNER = "mailbox_rule_non_owner"
    EVENT_TYPE_RULE_OUTSIDE_HOURS = "mailbox_rule_outside_hours"

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db_session: Async database session
        """
        self.db = db_session
        self.cred_manager = CredentialStorageManager(db_session)

    def _apply_tenant_filter(self, query: Any, model_class: Any, tenant_id: str | list[str] | None) -> Any:
        if tenant_id is None:
            return query
        if tenant_id == "NONE":
            return query.where(model_class.tenant_id == "NONE_ASSIGNED")
        if isinstance(tenant_id, list):
            return query.where(model_class.tenant_id.in_(tenant_id))
        return query.where(model_class.tenant_id == tenant_id)

    async def scan_tenant_mailbox_rules(
        self, tenant_id: str, trigger_alerts: bool = True
    ) -> dict[str, Any]:
        """Scan all mailbox rules for a tenant.

        Args:
            tenant_id: Internal tenant UUID
            trigger_alerts: Whether to trigger alerts for suspicious rules

        Returns:
            Scan results summary
        """
        # Get tenant details
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Decrypt credentials using unified manager
        creds = await self.cred_manager.get_credentials(tenant.tenant_id, user_id="mailbox_rules_scan")
        client_secret = creds.client_secret

        # Create Graph client
        graph_client = MSGraphClient(
            tenant_id=tenant.tenant_id, client_id=tenant.client_id, client_secret=client_secret
        )

        # Create mailbox rule client
        rule_client = MailboxRuleClient(graph_client)

        # Fetch all rules
        logger.info(f"Scanning mailbox rules for tenant {tenant.name}")
        rules = await rule_client.get_mailbox_rules_for_tenant()

        results = {
            "total_rules": len(rules),
            "new_rules": 0,
            "updated_rules": 0,
            "suspicious_rules": 0,
            "malicious_rules": 0,
            "alerts_triggered": 0,
        }

        # Process each rule
        for rule_data in rules:
            try:
                rule_result = await self._process_rule(
                    tenant_id=tenant_id,
                    rule_data=rule_data,
                    rule_client=rule_client,
                    trigger_alerts=trigger_alerts,
                )

                if rule_result.get("is_new"):
                    results["new_rules"] += 1
                elif rule_result.get("is_updated"):
                    results["updated_rules"] += 1

                if rule_result.get("status") == RuleStatus.SUSPICIOUS:
                    results["suspicious_rules"] += 1
                elif rule_result.get("status") == RuleStatus.MALICIOUS:
                    results["malicious_rules"] += 1

                if rule_result.get("alert_triggered"):
                    results["alerts_triggered"] += 1

            except Exception as e:
                logger.error(f"Error processing rule: {e}")
                continue

        return results

    async def _process_rule(
        self,
        tenant_id: str,
        rule_data: dict[str, Any],
        rule_client: MailboxRuleClient,
        trigger_alerts: bool,
    ) -> dict[str, Any]:
        """Process a single mailbox rule.

        Args:
            tenant_id: Internal tenant UUID
            rule_data: Rule data from Graph API
            rule_client: MailboxRuleClient instance
            trigger_alerts: Whether to trigger alerts

        Returns:
            Processing results
        """
        user_email = rule_data.get("_user_email", "")
        rule_id = rule_data.get("id", "")

        # Analyze the rule
        analysis = rule_client.analyze_rule(rule_data)

        # Check if rule already exists
        existing_rule = await self._get_existing_rule(tenant_id, user_email, rule_id)

        is_new = False
        is_updated = False
        alert_triggered = False

        if existing_rule:
            # Update existing rule
            await self._update_rule(existing_rule, rule_data, analysis)
            is_updated = True
            rule_model = existing_rule
        else:
            # Create new rule
            rule_model = await self._create_rule(tenant_id, user_email, rule_data, analysis)
            is_new = True

        # Trigger alerts if needed
        if trigger_alerts and rule_model.status in [RuleStatus.SUSPICIOUS, RuleStatus.MALICIOUS]:
            await self._trigger_alert(rule_model)
            alert_triggered = True

        return {
            "is_new": is_new,
            "is_updated": is_updated,
            "status": rule_model.status,
            "alert_triggered": alert_triggered,
        }

    async def _get_existing_rule(
        self, tenant_id: str, user_email: str, rule_id: str
    ) -> MailboxRuleModel | None:
        """Get existing rule from database.

        Args:
            tenant_id: Internal tenant UUID
            user_email: User email address
            rule_id: Microsoft Graph rule ID

        Returns:
            Existing rule or None
        """
        result = await self.db.execute(
            select(MailboxRuleModel).where(
                and_(
                    MailboxRuleModel.tenant_id == tenant_id,
                    MailboxRuleModel.user_email == user_email,
                    MailboxRuleModel.rule_id == rule_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _create_rule(
        self, tenant_id: str, user_email: str, rule_data: dict[str, Any], analysis: dict[str, Any]
    ) -> MailboxRuleModel:
        """Create a new mailbox rule record.

        Args:
            tenant_id: Internal tenant UUID
            user_email: User email address
            rule_data: Rule data from Graph API
            analysis: Analysis results

        Returns:
            Created rule model
        """
        # Parse dates
        rule_created_at = None
        rule_modified_at = None

        if rule_data.get("createdDateTime"):
            with contextlib.suppress(ValueError, AttributeError):
                rule_created_at = datetime.fromisoformat(
                    rule_data["createdDateTime"].replace("Z", "+00:00")
                )

        if rule_data.get("lastModifiedDateTime"):
            with contextlib.suppress(ValueError, AttributeError):
                rule_modified_at = datetime.fromisoformat(
                    rule_data["lastModifiedDateTime"].replace("Z", "+00:00")
                )

        rule = MailboxRuleModel(
            tenant_id=tenant_id,
            user_email=user_email,
            rule_id=rule_data.get("id", ""),
            rule_name=rule_data.get("displayName", "Unnamed Rule"),
            rule_type=RuleType(analysis.get("rule_type", "custom")),
            is_enabled=rule_data.get("isEnabled", True),
            status=RuleStatus(analysis.get("status", "benign")),
            severity=RuleSeverity(analysis.get("severity", "LOW")),
            forward_to=analysis.get("forward_to"),
            forward_to_external=analysis.get("forward_to_external", False),
            external_domain=analysis.get("external_domain"),
            redirect_to=analysis.get("redirect_to"),
            auto_reply_content=analysis.get("auto_reply_content"),
            is_hidden_folder_redirect=analysis.get("is_hidden_folder_redirect", False),
            has_suspicious_patterns=analysis.get("has_suspicious_patterns", False),
            created_outside_business_hours=analysis.get("created_outside_business_hours", False),
            created_by_non_owner=False,  # Would need audit logs to determine this
            detection_reasons=analysis.get("detection_reasons", []),
            rule_created_at=rule_created_at,
            rule_modified_at=rule_modified_at,
            rule_data=rule_data,
        )

        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)

        return rule

    async def _update_rule(
        self, rule: MailboxRuleModel, rule_data: dict[str, Any], analysis: dict[str, Any]
    ) -> None:
        """Update an existing mailbox rule record.

        Args:
            rule: Existing rule model
            rule_data: Updated rule data from Graph API
            analysis: Updated analysis results
        """
        rule.rule_name = rule_data.get("displayName", rule.rule_name)
        rule.is_enabled = rule_data.get("isEnabled", rule.is_enabled)
        rule.status = RuleStatus(analysis.get("status", rule.status.value))
        rule.severity = RuleSeverity(analysis.get("severity", rule.severity.value))
        rule.forward_to = analysis.get("forward_to") or rule.forward_to
        rule.forward_to_external = analysis.get("forward_to_external", rule.forward_to_external)
        rule.external_domain = analysis.get("external_domain") or rule.external_domain
        rule.redirect_to = analysis.get("redirect_to") or rule.redirect_to
        rule.auto_reply_content = analysis.get("auto_reply_content") or rule.auto_reply_content
        rule.is_hidden_folder_redirect = analysis.get(
            "is_hidden_folder_redirect", rule.is_hidden_folder_redirect
        )
        rule.has_suspicious_patterns = analysis.get(
            "has_suspicious_patterns", rule.has_suspicious_patterns
        )
        rule.created_outside_business_hours = analysis.get(
            "created_outside_business_hours", rule.created_outside_business_hours
        )
        rule.detection_reasons = analysis.get("detection_reasons", rule.detection_reasons)
        rule.rule_data = rule_data
        rule.last_scan_at = datetime.utcnow()

        await self.db.commit()

    async def _trigger_alert(self, rule: MailboxRuleModel) -> None:
        """Trigger an alert for a suspicious/malicious rule.

        Args:
            rule: Mailbox rule that triggered the alert
        """
        try:
            # Create alert record
            alert = MailboxRuleAlertModel(
                rule_id=rule.id,
                tenant_id=rule.tenant_id,
                user_email=rule.user_email,
                alert_type=self._get_alert_type(rule),
                severity=rule.severity,
                title=rule.generate_alert_title(),
                description=rule.generate_alert_description(),
                alert_metadata={
                    "rule_id": rule.rule_id,
                    "rule_name": rule.rule_name,
                    "forward_to": rule.forward_to,
                    "external_domain": rule.external_domain,
                    "created_by": rule.created_by,
                    "detection_reasons": rule.detection_reasons,
                },
            )

            self.db.add(alert)
            await self.db.commit()

            # Also trigger through alert engine for webhook notifications
            engine = AlertEngine(self.db)
            try:
                event_type = self._map_to_event_type(rule)
                severity = self._map_to_severity_level(rule.severity)

                await engine.process_event(
                    event_type=event_type,
                    severity=severity,
                    title=alert.title,
                    description=alert.description,
                    user_email=rule.user_email,
                    tenant_id=rule.tenant_id,
                    metadata=alert.alert_metadata,
                )
            finally:
                await engine.close()

        except Exception as e:
            logger.error(f"Error triggering alert for rule {rule.id}: {e}")

    def _get_alert_type(self, rule: MailboxRuleModel) -> str:
        """Determine alert type based on rule characteristics.

        Args:
            rule: Mailbox rule model

        Returns:
            Alert type string
        """
        if rule.forward_to_external:
            return self.EVENT_TYPE_FORWARDING_EXTERNAL
        elif rule.is_hidden_folder_redirect:
            return self.EVENT_TYPE_REDIRECT_HIDDEN
        elif rule.auto_reply_content and rule.has_suspicious_patterns:
            return self.EVENT_TYPE_SUSPICIOUS_AUTO_REPLY
        elif rule.created_by_non_owner:
            return self.EVENT_TYPE_RULE_CREATED_NON_OWNER
        elif rule.created_outside_business_hours:
            return self.EVENT_TYPE_RULE_OUTSIDE_HOURS
        return "mailbox_rule_generic"

    def _map_to_event_type(self, rule: MailboxRuleModel) -> EventType:
        """Map rule to event type for alert engine.

        Args:
            rule: Mailbox rule model

        Returns:
            EventType enum value
        """
        # For now, map all mailbox rule events to ADMIN_ACTION
        # Could extend EventType enum in the future
        return EventType.ADMIN_ACTION

    def _map_to_severity_level(self, severity: RuleSeverity) -> SeverityLevel:
        """Map rule severity to alert severity level.

        Args:
            severity: Rule severity

        Returns:
            SeverityLevel enum value
        """
        mapping = {
            RuleSeverity.LOW: SeverityLevel.LOW,
            RuleSeverity.MEDIUM: SeverityLevel.MEDIUM,
            RuleSeverity.HIGH: SeverityLevel.HIGH,
            RuleSeverity.CRITICAL: SeverityLevel.CRITICAL,
        }
        return mapping.get(severity, SeverityLevel.MEDIUM)

    async def _get_tenant(self, tenant_id: str) -> TenantModel | None:
        """Get tenant by internal ID.

        Args:
            tenant_id: Internal tenant UUID

        Returns:
            Tenant model or None
        """
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_rules(
        self,
        tenant_id: str | list[str] | None = None,
        user_email: str | None = None,
        status: RuleStatus | None = None,
        severity: RuleSeverity | None = None,
        rule_type: RuleType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get mailbox rules with filtering.

        Args:
            tenant_id: Filter by tenant
            user_email: Filter by user
            status: Filter by status
            severity: Filter by severity
            rule_type: Filter by rule type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        query = select(MailboxRuleModel)

        # Apply filters
        if tenant_id:
            if tenant_id == "NONE":
                query = query.where(MailboxRuleModel.tenant_id == "NONE_ASSIGNED")
            elif isinstance(tenant_id, list):
                query = query.where(MailboxRuleModel.tenant_id.in_(tenant_id))
            else:
                query = query.where(MailboxRuleModel.tenant_id == tenant_id)
        if user_email:
            query = query.where(MailboxRuleModel.user_email == user_email)
        if status:
            query = query.where(MailboxRuleModel.status == status)
        if severity:
            query = query.where(MailboxRuleModel.severity == severity)
        if rule_type:
            query = query.where(MailboxRuleModel.rule_type == rule_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = query.order_by(desc(MailboxRuleModel.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_rule_by_id(self, rule_id: str) -> MailboxRuleModel | None:
        """Get a specific mailbox rule by ID.

        Args:
            rule_id: Rule UUID

        Returns:
            Rule model or None
        """
        result = await self.db.execute(
            select(MailboxRuleModel).where(MailboxRuleModel.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_suspicious_rules(
        self, tenant_id: str | list[str] | None = None, limit: int = 100
    ) -> list[MailboxRuleModel]:
        """Get suspicious and malicious rules.

        Args:
            tenant_id: Optional tenant filter
            limit: Maximum results

        Returns:
            List of suspicious/malicious rules
        """
        query = select(MailboxRuleModel).where(
            MailboxRuleModel.status.in_([RuleStatus.SUSPICIOUS, RuleStatus.MALICIOUS])
        )

        if tenant_id:
            if tenant_id == "NONE":
                query = query.where(MailboxRuleModel.tenant_id == "NONE_ASSIGNED")
            elif isinstance(tenant_id, list):
                query = query.where(MailboxRuleModel.tenant_id.in_(tenant_id))
            else:
                query = query.where(MailboxRuleModel.tenant_id == tenant_id)

        query = query.order_by(desc(MailboxRuleModel.severity))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_alerts(
        self,
        tenant_id: str | list[str] | None = None,
        acknowledged: bool | None = None,
        severity: RuleSeverity | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get mailbox rule alerts.

        Args:
            tenant_id: Filter by tenant
            acknowledged: Filter by acknowledgment status
            severity: Filter by severity
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        query = select(MailboxRuleAlertModel)

        query = self._apply_tenant_filter(query, MailboxRuleAlertModel, tenant_id)
        if acknowledged is not None:
            query = query.where(MailboxRuleAlertModel.is_acknowledged == acknowledged)
        if severity:
            query = query.where(MailboxRuleAlertModel.severity == severity)

        # Get total count
        count_query = select(MailboxRuleAlertModel.id).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Apply pagination and ordering
        query = query.order_by(desc(MailboxRuleAlertModel.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str
    ) -> MailboxRuleAlertModel | None:
        """Acknowledge a mailbox rule alert.

        Args:
            alert_id: Alert UUID
            acknowledged_by: User acknowledging the alert

        Returns:
            Updated alert or None if not found
        """
        result = await self.db.execute(
            select(MailboxRuleAlertModel).where(MailboxRuleAlertModel.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.is_acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        return alert
