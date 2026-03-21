"""Service for analyzing Insider Threat, DLP, and Mailbox security events."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLogModel, LogType
from src.models.dlp import DLPEventModel
from src.models.mailbox import MailboxRuleEventModel, MailboxAccessModel

logger = logging.getLogger(__name__)

# DLP operations in Audit.General
DLP_OPERATIONS = {
    "DlpRuleMatch",
    "DlpRuleMatchBlocked",
    "DlpRuleMatchOverride",
}

# Mailbox rule operations in Audit.Exchange
MAILBOX_RULE_OPERATIONS = {
    "New-InboxRule",
    "Set-InboxRule",
    "UpdateInboxRules",
}

class InsiderThreatService:
    """Service for processing and analyzing Insider Threat and Mailbox events."""

    def __init__(self, db: AsyncSession):
        """Initialize the service."""
        self.db = db

    async def process_dlp_events(self, tenant_id: UUID, limit: int = 100) -> int:
        """Process DLP rule matches from general audit logs."""
        result = await self.db.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.log_type == LogType.AUDIT_GENERAL,
                    AuditLogModel.processed.is_(False),
                )
            )
            .order_by(AuditLogModel.o365_created_at)
            .limit(limit)
        )

        logs = result.scalars().all()
        processed_count = 0

        for log in logs:
            raw_data = log.raw_data
            operation = raw_data.get("Operation", "")
            
            if operation in DLP_OPERATIONS:
                # Extract DLP details
                policy_name = raw_data.get("PolicyName")
                severity = raw_data.get("Severity")
                user_id = raw_data.get("UserId")
                
                # Try to get file names and info types
                details = raw_data.get("Details", {})
                file_name = details.get("FileName") or raw_data.get("FileName")
                info_types = raw_data.get("SensitiveInfoType", [])
                if isinstance(info_types, list):
                    info_types_str = ", ".join([str(t) for t in info_types])
                else:
                    info_types_str = str(info_types)
                
                action = "Blocked" if "Blocked" in operation else "Detected"
                
                dlp_event = DLPEventModel(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    policy_name=policy_name,
                    severity=severity,
                    file_name=file_name,
                    sensitive_info_types=info_types_str,
                    action_taken=action,
                    raw_data=raw_data,
                    created_at=log.o365_created_at or datetime.now(timezone.utc)
                )
                self.db.add(dlp_event)
                processed_count += 1
            
            log.processed = True
            
        await self.db.commit()
        return processed_count

    async def process_mailbox_security(self, tenant_id: UUID, limit: int = 100) -> int:
        """Process Mailbox security events from exchange audit logs."""
        result = await self.db.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.log_type == LogType.EXCHANGE,
                    AuditLogModel.processed.is_(False),
                )
            )
            .order_by(AuditLogModel.o365_created_at)
            .limit(limit)
        )

        logs = result.scalars().all()
        processed_count = 0

        for log in logs:
            raw_data = log.raw_data
            operation = raw_data.get("Operation", "")
            
            # 1. Handle Rules
            if operation in MAILBOX_RULE_OPERATIONS:
                user_id = raw_data.get("UserId")
                params = raw_data.get("Parameters", [])
                
                # Extract rule details from parameters
                rule_name = None
                forward_to = None
                is_external = False
                
                for p in params:
                    name = p.get("Name")
                    value = p.get("Value")
                    if name == "Name":
                        rule_name = value
                    elif name in ["ForwardTo", "ForwardAsAttachmentTo", "RedirectTo"]:
                        forward_to = value
                        if value and "@" in value:
                            # Simple external check - could be improved with domain whitelist
                            is_external = True
                
                rule_record = MailboxRuleEventModel(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation=operation,
                    rule_name=rule_name,
                    forward_to=forward_to,
                    is_external=is_external,
                    raw_data=raw_data,
                    created_at=log.o365_created_at or datetime.now(timezone.utc)
                )
                self.db.add(rule_record)
                processed_count += 1
            
            # 2. Handle Non-Owner Access
            logon_type = raw_data.get("LogonType") # 0 = Owner, 1 = Admin, 2 = Delegate
            if logon_type is not None and str(logon_type) != "0":
                 access_record = MailboxAccessModel(
                    tenant_id=tenant_id,
                    accessed_mailbox=raw_data.get("MailboxGuid") or raw_data.get("UserId"),
                    accessed_by=raw_data.get("ClientInfoString") or raw_data.get("UserId"),
                    operation=operation,
                    is_non_owner=True,
                    client_ip=raw_data.get("ClientIPAddress"),
                    created_at=log.o365_created_at or datetime.now(timezone.utc)
                 )
                 self.db.add(access_record)
                 processed_count += 1
            
            log.processed = True
            
        await self.db.commit()
        return processed_count
