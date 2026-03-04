"""User model for local authentication."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-naive for PostgreSQL compatibility)."""
    return datetime.utcnow()


class UserModel(Base):
    """User database model for local authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hash of user password"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last successful login"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, is_active={self.is_active})>"
