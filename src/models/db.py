"""SQLAlchemy models for SpecterDefence."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class TenantModel(Base):
    """Tenant database model."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
        DateTime, nullable=True, comment="Timestamp of last health check"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, tenant_id={self.tenant_id}, status={self.connection_status})>"
