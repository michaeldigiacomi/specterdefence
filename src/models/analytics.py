"""Analytics models for login tracking and anomaly detection."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.types import JSONB, UUID

if TYPE_CHECKING:
    from src.models.audit_log import AuditLogModel


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class LoginAnalyticsModel(Base):
    """Login analytics database model for storing geo-located login attempts."""

    __tablename__ = "login_analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_logs.id"),
        nullable=True,
        comment="Reference to original audit log",
    )
    user_email: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False, comment="User email address"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False, comment="Internal tenant UUID"
    )
    ip_address: Mapped[str] = mapped_column(
        String(45), index=True, nullable=False, comment="IP address (IPv4 or IPv6)"
    )
    country: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, comment="Country name"
    )
    country_code: Mapped[str | None] = mapped_column(
        String(2), nullable=True, comment="ISO country code"
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="City name")
    region: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Region/State name"
    )
    latitude: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Latitude coordinate"
    )
    longitude: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Longitude coordinate"
    )
    login_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Timestamp of the login attempt"
    )
    is_success: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether login was successful"
    )
    failure_reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Reason for login failure if applicable"
    )
    anomaly_flags: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False, comment="List of detected anomaly types"
    )
    risk_score: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="Calculated risk score (0-100)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    audit_log: Mapped[Optional["AuditLogModel"]] = relationship(
        "AuditLogModel", back_populates="login_analytics"
    )

    __table_args__ = (
        # Composite index for user login history queries
        Index("ix_login_analytics_user_time", "user_email", "login_time"),
        # Composite index for tenant analytics
        Index("ix_login_analytics_tenant_time", "tenant_id", "login_time"),
        # Index for IP-based queries
        Index("ix_login_analytics_ip_time", "ip_address", "login_time"),
    )

    def __repr__(self) -> str:
        return f"<LoginAnalytics(id={self.id}, user={self.user_email}, country={self.country})>"


class UserLoginHistoryModel(Base):
    """User login history for tracking known countries and IPs."""

    __tablename__ = "user_login_history"

    user_email: Mapped[str] = mapped_column(
        String(255), primary_key=True, comment="User email address (PK)"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False, comment="Internal tenant UUID"
    )
    known_countries: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False, comment="List of previously seen country codes"
    )
    known_ips: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False, comment="List of previously seen IP addresses"
    )
    last_login_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of last successful login"
    )
    last_login_country: Mapped[str | None] = mapped_column(
        String(2), nullable=True, comment="Country code of last login"
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="IP address of last login"
    )
    last_latitude: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Latitude of last login"
    )
    last_longitude: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Longitude of last login"
    )
    total_logins: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="Total number of successful logins"
    )
    failed_attempts_24h: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="Failed login attempts in last 24 hours"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (Index("ix_user_login_history_tenant", "tenant_id"),)

    def __repr__(self) -> str:
        return f"<UserLoginHistory(user={self.user_email}, last_country={self.last_login_country})>"


class AnomalyDetectionConfig(Base):
    """Configuration for anomaly detection per tenant."""

    __tablename__ = "anomaly_detection_config"

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), primary_key=True, comment="Internal tenant UUID (PK)"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether anomaly detection is enabled"
    )
    impossible_travel_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Enable impossible travel detection"
    )
    impossible_travel_speed_kmh: Mapped[int] = mapped_column(
        default=900, nullable=False, comment="Speed threshold for impossible travel (km/h)"
    )
    new_country_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Enable new country detection"
    )
    auto_add_known_countries: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Automatically add new countries to known list",
    )
    risk_score_threshold: Mapped[int] = mapped_column(
        default=70, nullable=False, comment="Risk score threshold for alerting"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<AnomalyDetectionConfig(tenant={self.tenant_id}, enabled={self.enabled})>"
