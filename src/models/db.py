"""SQLAlchemy models for SpecterDefence."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.types import UUID


user_tenants = Table(
    "user_tenants",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
)



def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class TenantModel(Base):
    """Tenant database model."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="Azure AD tenant ID"
    )
    client_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Azure AD application ID"
    )
    client_secret: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Encrypted client secret"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connection_status: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Connection status: connected, error, timeout, unknown",
    )
    connection_error: Mapped[str] = mapped_column(
        String(500), nullable=True, comment="Last connection error message"
    )
    last_health_check: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of last health check"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, tenant_id={self.tenant_id}, status={self.connection_status})>"

    # Relationship to user
    users = relationship("UserModel", secondary="user_tenants", back_populates="tenants")

