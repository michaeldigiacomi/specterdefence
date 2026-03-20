"""SharePoint analytics models for tracking sharing and file activity."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class SharePointSharingModel(Base):
    """Model for tracking SharePoint sharing events and public links."""

    __tablename__ = "sharepoint_sharing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False, comment="Internal tenant UUID"
    )
    audit_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="Original audit log reference"
    )
    
    # Event Info
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Resource Info
    site_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Actor Info
    user_email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    
    # Sharing Details
    sharing_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Anonymous, Secure, etc.
    share_link_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_sharepoint_sharing_tenant_file", "tenant_id", "file_path"),
    )

    def __repr__(self) -> str:
        return f"<SharePointSharing(id={self.id}, operation={self.operation}, file={self.file_name})>"

from src.models.types import UUID
