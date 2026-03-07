"""Audit log database models for SpecterDefence."""

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from src.models.analytics import LoginAnalyticsModel

from src.database import Base
from src.models.types import JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime without timezone info (naive).
    
    This is preferred for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LogType(StrEnum):
    """Types of audit logs from Office 365."""

    SIGNIN = "signin"
    AUDIT_GENERAL = "audit_general"
    AZURE_ACTIVE_DIRECTORY = "azure_active_directory"
    EXCHANGE = "exchange"
    SHAREPOINT = "sharepoint"


class AuditLogModel(Base):
    """Audit log database model for storing Office 365 logs."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False, comment="Internal tenant UUID (FK to tenants)"
    )
    log_type: Mapped[LogType] = mapped_column(
        SQLEnum(LogType, name="log_type_enum"), nullable=False, comment="Type of audit log"
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Full O365 response as JSONB"
    )
    processed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether the log has been processed"
    )
    o365_created_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="Timestamp from O365 (CreationTime field)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        comment="When this record was created in our database",
    )

    # Relationships
    login_analytics: Mapped[list["LoginAnalyticsModel"]] = relationship(
        "LoginAnalyticsModel", back_populates="audit_log"
    )

    # Table arguments for additional indexes
    __table_args__ = (
        # Composite index for efficient querying by tenant and time
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        # Index for finding unprocessed logs
        Index("ix_audit_logs_processed", "processed", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, tenant_id={self.tenant_id}, log_type={self.log_type})>"


class CollectionStateModel(Base):
    """Tracks collection state (watermark/bookmark) per tenant."""

    __tablename__ = "collection_state"

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
        comment="Internal tenant UUID (PK and FK to tenants)",
    )
    last_collection_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Last successful collection timestamp"
    )
    next_page_token: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Pagination token for resuming interrupted collection"
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Timestamp of last successful collection run"
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Last error message if collection failed"
    )
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="When the last error occurred"
    )
    total_logs_collected: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="Cumulative count of logs collected for this tenant"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<CollectionState(tenant_id={self.tenant_id}, last_collection_time={self.last_collection_time})>"


class ContentSubscriptionModel(Base):
    """Tracks content type subscriptions for Office 365 Management API."""

    __tablename__ = "content_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False, comment="Internal tenant UUID"
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Office 365 content type (e.g., Audit.AzureActiveDirectory)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether subscription is active"
    )
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Webhook URL if using push notifications"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        # Unique constraint to prevent duplicate subscriptions
        Index("ix_content_subscriptions_tenant_type", "tenant_id", "content_type", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<ContentSubscription(tenant_id={self.tenant_id}, content_type={self.content_type})>"
        )
