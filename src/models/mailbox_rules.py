"""Mailbox rule models for SpecterDefence."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import ARRAY, JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class RuleType(StrEnum):
    """Types of mailbox rules."""

    FORWARDING = "forwarding"
    AUTO_REPLY = "auto_reply"
    REDIRECT = "redirect"
    MOVE_TO_FOLDER = "move_to_folder"
    DELETE = "delete"
    MARK_AS_READ = "mark_as_read"
    CUSTOM = "custom"


class RuleSeverity(StrEnum):
    """Severity levels for mailbox rule alerts."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleStatus(StrEnum):
    """Status of mailbox rule analysis."""

    ACTIVE = "active"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    BENIGN = "benign"
    DISABLED = "disabled"


class MailboxRuleModel(Base):
    """Mailbox rule database model for tracking and analysis."""

    __tablename__ = "mailbox_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="Internal tenant UUID",
    )
    user_email: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Email of the mailbox owner"
    )
    rule_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Microsoft Graph rule ID"
    )
    rule_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Display name of the rule"
    )
    rule_type: Mapped[RuleType] = mapped_column(
        SQLEnum(RuleType, name="rule_type_enum"), nullable=False, comment="Type of mailbox rule"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether the rule is enabled in Exchange"
    )
    status: Mapped[RuleStatus] = mapped_column(
        SQLEnum(RuleStatus, name="rule_status_enum"),
        nullable=False,
        default=RuleStatus.ACTIVE,
        comment="Analysis status of the rule",
    )
    severity: Mapped[RuleSeverity] = mapped_column(
        SQLEnum(RuleSeverity, name="rule_severity_enum"),
        nullable=False,
        default=RuleSeverity.LOW,
        comment="Severity level based on analysis",
    )

    # Rule details
    forward_to: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Forward destination email if applicable"
    )
    forward_to_external: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether forwarding is to external domain"
    )
    external_domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="External domain if forwarding externally"
    )
    redirect_to: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Redirect destination if applicable"
    )
    auto_reply_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Auto-reply message content if applicable"
    )

    # Detection flags
    is_hidden_folder_redirect: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether rule redirects to hidden/deleted items",
    )
    has_suspicious_patterns: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether rule contains suspicious patterns"
    )
    created_outside_business_hours: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether rule was created outside business hours",
    )
    created_by_non_owner: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether rule was created by someone other than mailbox owner",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="UPN of user who created the rule"
    )

    # Detection reasons
    detection_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)), default=list, nullable=False, comment="List of detection reasons"
    )

    # Timestamps
    rule_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When the rule was created in Exchange"
    )
    rule_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When the rule was last modified"
    )
    last_scan_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="When rule was last scanned"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Raw data
    rule_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Raw rule data from Graph API"
    )

    __table_args__ = (
        # Composite index for deduplication lookups
        Index("ix_mailbox_rules_user_rule", "user_email", "rule_id", unique=True),
        # Index for suspicious rule queries
        Index("ix_mailbox_rules_status_severity", "status", "severity"),
        # Index for tenant-based queries with time filtering
        Index("ix_mailbox_rules_tenant_scan", "tenant_id", "last_scan_at"),
    )

    def __repr__(self) -> str:
        return f"<MailboxRule(id={self.id}, user={self.user_email}, type={self.rule_type})>"

    def generate_alert_title(self) -> str:
        """Generate alert title based on rule characteristics."""
        if self.status == RuleStatus.MALICIOUS:
            return f"Malicious Mailbox Rule Detected: {self.rule_name}"
        elif self.status == RuleStatus.SUSPICIOUS:
            return f"Suspicious Mailbox Rule Detected: {self.rule_name}"
        return f"Mailbox Rule Alert: {self.rule_name}"

    def generate_alert_description(self) -> str:
        """Generate detailed alert description."""
        parts = []

        if self.forward_to_external:
            parts.append(f"Forwards emails to external address: {self.forward_to}")

        if self.is_hidden_folder_redirect:
            parts.append("Redirects emails to hidden/deleted items folder")

        if self.created_by_non_owner:
            parts.append(f"Created by non-owner: {self.created_by}")

        if self.created_outside_business_hours:
            parts.append("Created outside business hours")

        if self.detection_reasons:
            parts.append(f"Detection reasons: {', '.join(self.detection_reasons)}")

        return "; ".join(parts) if parts else "Mailbox rule requires review"


class MailboxRuleAlertModel(Base):
    """Alerts specifically for mailbox rule violations."""

    __tablename__ = "mailbox_rule_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox_rules.id"),
        nullable=False,
        comment="Reference to the mailbox rule",
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Type of alert (forwarding, redirect, etc.)"
    )
    severity: Mapped[RuleSeverity] = mapped_column(
        SQLEnum(RuleSeverity, name="rule_alert_severity_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_mailbox_rule_alerts_unack", "tenant_id", "is_acknowledged", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<MailboxRuleAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"
