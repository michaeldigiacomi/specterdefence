"""Database models for Exchange Mailbox Analytics."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import JSONB, UUID

class MailboxRuleEventModel(Base):
    """Tracking mailbox forward/inbox rule changes (events)."""
    __tablename__ = "mailbox_rule_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)  # New-InboxRule, UpdateInboxRule
    rule_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forward_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class MailboxAccessModel(Base):
    """Tracking mailbox accesses (especially non-owner)."""
    __tablename__ = "mailbox_access"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    accessed_mailbox: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    accessed_by: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    is_non_owner: Mapped[bool] = mapped_column(Boolean, default=True)
    client_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
