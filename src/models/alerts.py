"""Alert models for SpecterDefence."""

import hashlib
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.types import ARRAY, JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class WebhookType(StrEnum):
    """Types of webhooks supported."""

    DISCORD = "discord"
    SLACK = "slack"


class SeverityLevel(StrEnum):
    """Severity levels for alerts."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventType(StrEnum):
    """Types of events that can trigger alerts."""

    IMPOSSIBLE_TRAVEL = "impossible_travel"
    NEW_COUNTRY = "new_country"
    BRUTE_FORCE = "brute_force"
    ADMIN_ACTION = "admin_action"
    NEW_IP = "new_ip"
    MULTIPLE_FAILURES = "multiple_failures"
    SUSPICIOUS_LOCATION = "suspicious_location"


# Severity colors for Discord embeds
SEVERITY_COLORS = {
    SeverityLevel.LOW: 3066993,  # Green
    SeverityLevel.MEDIUM: 16776960,  # Yellow
    SeverityLevel.HIGH: 15158332,  # Orange
    SeverityLevel.CRITICAL: 16711680,  # Red
}

# Severity emojis for Discord
SEVERITY_EMOJIS = {
    SeverityLevel.LOW: "ℹ️",
    SeverityLevel.MEDIUM: "⚠️",
    SeverityLevel.HIGH: "🚨",
    SeverityLevel.CRITICAL: "🔥",
}

# Event type display names
EVENT_TYPE_NAMES = {
    EventType.IMPOSSIBLE_TRAVEL: "Impossible Travel",
    EventType.NEW_COUNTRY: "New Country Login",
    EventType.BRUTE_FORCE: "Brute Force Attack",
    EventType.ADMIN_ACTION: "Admin Action",
    EventType.NEW_IP: "New IP Address",
    EventType.MULTIPLE_FAILURES: "Multiple Failed Logins",
    EventType.SUSPICIOUS_LOCATION: "Suspicious Location",
}


class AlertWebhookModel(Base):
    """Alert webhook configuration database model."""

    __tablename__ = "alert_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
        comment="Internal tenant UUID (null = global webhook)",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Display name for this webhook"
    )
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False, comment="Encrypted webhook URL")
    webhook_type: Mapped[WebhookType] = mapped_column(
        SQLEnum(WebhookType, name="webhook_type_enum"),
        nullable=False,
        default=WebhookType.DISCORD,
        comment="Type of webhook (discord, slack)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether this webhook is active"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    alert_history: Mapped[list["AlertHistoryModel"]] = relationship(
        "AlertHistoryModel", back_populates="webhook"
    )

    def __repr__(self) -> str:
        return f"<AlertWebhook(id={self.id}, name={self.name}, type={self.webhook_type})>"


class AlertRuleModel(Base):
    """Alert rule configuration database model."""

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
        comment="Internal tenant UUID (null = global rule)",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Display name for this rule"
    )
    event_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), nullable=False, comment="List of event types this rule matches"
    )
    min_severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, name="severity_level_enum"),
        nullable=False,
        default=SeverityLevel.MEDIUM,
        comment="Minimum severity level to trigger this rule",
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False, comment="Cooldown period in minutes for deduplication"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether this rule is active"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    alert_history: Mapped[list["AlertHistoryModel"]] = relationship(
        "AlertHistoryModel", back_populates="rule"
    )

    __table_args__ = (Index("ix_alert_rules_tenant_active", "tenant_id", "is_active"),)

    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name={self.name}, severity={self.min_severity})>"


class AlertHistoryModel(Base):
    """Alert history database model for tracking sent alerts."""

    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert_rules.id"),
        nullable=True,
        comment="Reference to the rule that triggered this alert",
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert_webhooks.id"),
        nullable=False,
        comment="Reference to the webhook used",
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
        comment="Internal tenant UUID",
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, name="severity_level_enum"),
        nullable=False,
        comment="Severity level of the alert",
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Type of event that triggered the alert"
    )
    user_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment="Email of user involved in the event"
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="Alert title")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="Alert message content")
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Additional alert metadata"
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False, index=True, comment="When the alert was sent"
    )
    dedup_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="Hash for deduplication (SHA-256)"
    )

    # Relationships
    rule: Mapped[Optional["AlertRuleModel"]] = relationship(
        "AlertRuleModel", back_populates="alert_history"
    )
    webhook: Mapped["AlertWebhookModel"] = relationship(
        "AlertWebhookModel", back_populates="alert_history"
    )

    __table_args__ = (
        # Composite index for deduplication lookups
        Index("ix_alert_history_dedup_time", "dedup_hash", "sent_at"),
        # Index for tenant-based queries
        Index("ix_alert_history_tenant_time", "tenant_id", "sent_at"),
    )

    def __repr__(self) -> str:
        return f"<AlertHistory(id={self.id}, event={self.event_type}, severity={self.severity})>"

    @staticmethod
    def generate_dedup_hash(
        event_type: str, user_email: str | None, tenant_id: str | None, metadata: dict[str, Any]
    ) -> str:
        """Generate a deduplication hash for an alert.

        Args:
            event_type: Type of event
            user_email: User email (optional)
            tenant_id: Tenant ID (optional)
            metadata: Alert metadata

        Returns:
            SHA-256 hash string
        """
        # Create a unique string based on key identifying fields
        # We include specific metadata fields that identify the event uniquely
        key_parts = [
            event_type,
            user_email or "",
            tenant_id or "",
        ]

        # Add location-related fields for travel alerts
        if "previous_location" in metadata and "current_location" in metadata:
            prev = metadata["previous_location"]
            curr = metadata["current_location"]
            key_parts.extend(
                [
                    str(prev.get("country", "")),
                    str(curr.get("country", "")),
                ]
            )

        # Add country for new country alerts
        if "country_code" in metadata:
            key_parts.append(str(metadata["country_code"]))

        # Add IP for IP-related alerts
        if "ip_address" in metadata:
            key_parts.append(str(metadata["ip_address"]))

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
