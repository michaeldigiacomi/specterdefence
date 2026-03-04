"""Settings models for SpecterDefence."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class TimeZone(StrEnum):
    """Supported timezones."""

    UTC = "UTC"
    US_EASTERN = "America/New_York"
    US_CENTRAL = "America/Chicago"
    US_MOUNTAIN = "America/Denver"
    US_PACIFIC = "America/Los_Angeles"
    EUROPE_LONDON = "Europe/London"
    EUROPE_PARIS = "Europe/Paris"
    EUROPE_BERLIN = "Europe/Berlin"
    ASIA_TOKYO = "Asia/Tokyo"
    ASIA_SINGAPORE = "Asia/Singapore"
    AUSTRALIA_SYDNEY = "Australia/Sydney"


class NotificationChannel(StrEnum):
    """Notification channels."""

    EMAIL = "email"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class SettingsCategory(StrEnum):
    """Settings categories."""

    TENANT = "tenant"
    ALERT_RULES = "alert_rules"
    NOTIFICATIONS = "notifications"
    DETECTION = "detection"
    SYSTEM = "system"
    USER = "user"


class SystemSettingsModel(Base):
    """System-wide settings model."""

    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Data retention
    audit_log_retention_days: Mapped[int] = mapped_column(
        Integer, default=90, nullable=False, comment="Days to retain audit logs"
    )
    login_history_retention_days: Mapped[int] = mapped_column(
        Integer, default=365, nullable=False, comment="Days to retain login history"
    )
    alert_history_retention_days: Mapped[int] = mapped_column(
        Integer, default=180, nullable=False, comment="Days to retain alert history"
    )

    # System maintenance
    auto_cleanup_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Enable automatic cleanup of old data"
    )
    cleanup_schedule: Mapped[str] = mapped_column(
        String(50),
        default="0 2 * * *",
        nullable=False,
        comment="Cron schedule for cleanup (default: 2 AM daily)",
    )

    # API settings
    api_rate_limit: Mapped[int] = mapped_column(
        Integer, default=1000, nullable=False, comment="API rate limit per hour"
    )
    max_export_rows: Mapped[int] = mapped_column(
        Integer, default=10000, nullable=False, comment="Maximum rows for data export"
    )

    # Logging
    log_level: Mapped[str] = mapped_column(
        String(20), default="INFO", nullable=False, comment="System log level"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class UserPreferencesModel(Base):
    """User preferences model."""

    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User identification (using email for now, can be replaced with user_id)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Display preferences
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    date_format: Mapped[str] = mapped_column(
        String(20), default="ISO", nullable=False, comment="Date format: ISO, US, EU"
    )
    theme: Mapped[str] = mapped_column(
        String(20), default="system", nullable=False, comment="Theme: light, dark, system"
    )

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    discord_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_min_severity: Mapped[str] = mapped_column(
        String(20), default="MEDIUM", nullable=False, comment="Minimum severity for notifications"
    )

    # Dashboard preferences
    default_dashboard_view: Mapped[str] = mapped_column(
        String(50), default="overview", nullable=False, comment="Default dashboard view"
    )
    refresh_interval_seconds: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False, comment="Dashboard auto-refresh interval in seconds"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class DetectionThresholdsModel(Base):
    """Anomaly detection thresholds model."""

    __tablename__ = "detection_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tenant association (null = global defaults)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Impossible travel
    impossible_travel_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    impossible_travel_min_speed_kmh: Mapped[float] = mapped_column(
        Float,
        default=800.0,
        nullable=False,
        comment="Minimum speed (km/h) to trigger impossible travel",
    )
    impossible_travel_time_window_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False, comment="Time window in minutes for travel comparison"
    )

    # New country detection
    new_country_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_country_learning_period_days: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False, comment="Learning period before flagging new countries"
    )

    # Brute force detection
    brute_force_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    brute_force_threshold: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False, comment="Failed login attempts threshold"
    )
    brute_force_window_minutes: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False, comment="Time window for brute force detection"
    )

    # New IP detection
    new_ip_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_ip_learning_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)

    # Multiple failures detection
    multiple_failures_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    multiple_failures_threshold: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False, comment="Failed attempts threshold per user"
    )
    multiple_failures_window_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )

    # Risk scoring
    risk_score_base_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class ApiKeyModel(Base):
    """API key management model."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Display name for the API key"
    )

    # Hashed key storage (we only show the full key once on creation)
    key_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="SHA-256 hash of the API key"
    )
    key_prefix: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="First 8 characters of the key for identification"
    )

    # Permissions
    scopes: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False, comment="List of allowed scopes"
    )

    # Access control
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Restrict to specific tenant (null = all tenants)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"


class ConfigurationBackupModel(Base):
    """Configuration backup/restore model."""

    __tablename__ = "configuration_backups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Backup data (JSON)
    config_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Complete configuration snapshot"
    )

    # Categories included in backup
    categories: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<ConfigBackup(id={self.id}, name={self.name})>"
