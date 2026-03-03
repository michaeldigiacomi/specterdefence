"""OAuth app models for SpecterDefence."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import ARRAY, JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class RiskLevel(StrEnum):
    """Risk levels for OAuth applications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AppStatus(StrEnum):
    """Status of OAuth application analysis."""
    APPROVED = "approved"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    REVOKED = "revoked"
    PENDING_REVIEW = "pending_review"


class PublisherType(StrEnum):
    """Type of app publisher."""
    MICROSOFT = "microsoft"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class OAuthAppModel(Base):
    """OAuth application database model for tracking and analysis."""

    __tablename__ = "oauth_apps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="Internal tenant UUID"
    )

    # App identification
    app_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Microsoft Graph application ID (client ID)"
    )
    display_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Display name of the application"
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Application description"
    )

    # Publisher information
    publisher_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Publisher display name"
    )
    publisher_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Publisher ID"
    )
    publisher_type: Mapped[PublisherType] = mapped_column(
        SQLEnum(PublisherType, name="publisher_type_enum"),
        nullable=False,
        default=PublisherType.UNKNOWN,
        comment="Type of publisher"
    )
    is_microsoft_publisher: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app is from Microsoft"
    )
    is_verified_publisher: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether publisher is verified"
    )

    # Risk analysis
    risk_level: Mapped[RiskLevel] = mapped_column(
        SQLEnum(RiskLevel, name="risk_level_enum"),
        nullable=False,
        default=RiskLevel.LOW,
        comment="Risk level based on permissions and publisher"
    )
    status: Mapped[AppStatus] = mapped_column(
        SQLEnum(AppStatus, name="app_status_enum"),
        nullable=False,
        default=AppStatus.PENDING_REVIEW,
        comment="Analysis status of the app"
    )
    risk_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Calculated risk score (0-100)"
    )

    # Permission analysis
    permission_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of permissions"
    )
    high_risk_permissions: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)),
        default=list,
        nullable=False,
        comment="List of high-risk permission names"
    )
    has_mail_permissions: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app has mail access permissions"
    )
    has_user_read_all: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app has User.Read.All permission"
    )
    has_group_read_all: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app has Group.Read.All permission"
    )
    has_files_read_all: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app has Files.Read.All permission"
    )
    has_calendar_access: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app has calendar access"
    )
    has_admin_consent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether app has admin consent"
    )

    # Consent tracking
    consent_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of users who consented to this app"
    )
    admin_consented: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether admin has consented on behalf of organization"
    )

    # Detection flags
    is_new_app: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a newly detected app"
    )
    detection_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)),
        default=list,
        nullable=False,
        comment="List of detection reasons"
    )

    # Timestamps
    app_created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="When the app was registered in Azure AD"
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        comment="When the app was first detected by SpecterDefence"
    )
    last_scan_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        comment="When app was last scanned"
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

    # Raw data
    app_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Raw app data from Graph API"
    )
    permissions_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Raw permissions data from Graph API"
    )

    __table_args__ = (
        # Composite index for deduplication lookups
        Index('ix_oauth_apps_tenant_app', 'tenant_id', 'app_id', unique=True),
        # Index for suspicious app queries
        Index('ix_oauth_apps_status_risk', 'status', 'risk_level'),
        # Index for high-risk permission queries
        Index('ix_oauth_apps_high_risk', 'has_mail_permissions', 'publisher_type'),
        # Index for tenant-based queries with time filtering
        Index('ix_oauth_apps_tenant_scan', 'tenant_id', 'last_scan_at'),
    )

    def __repr__(self) -> str:
        return f"<OAuthApp(id={self.id}, name={self.display_name}, risk={self.risk_level})>"

    def generate_alert_title(self) -> str:
        """Generate alert title based on app characteristics."""
        if self.status == AppStatus.MALICIOUS:
            return f"Malicious OAuth App Detected: {self.display_name}"
        elif self.status == AppStatus.SUSPICIOUS:
            return f"Suspicious OAuth App Detected: {self.display_name}"
        return f"OAuth App Alert: {self.display_name}"

    def generate_alert_description(self) -> str:
        """Generate detailed alert description."""
        parts = []

        if self.has_mail_permissions:
            parts.append("Has access to user mailboxes")

        if self.has_user_read_all:
            parts.append("Can read all user profiles")

        if self.has_group_read_all:
            parts.append("Can read all groups")

        if self.has_files_read_all:
            parts.append("Can read all files")

        if not self.is_microsoft_publisher and not self.is_verified_publisher:
            parts.append(f"Unverified publisher: {self.publisher_name or 'Unknown'}")

        if self.consent_count > 0:
            parts.append(f"Consented by {self.consent_count} user(s)")

        if self.detection_reasons:
            parts.append(f"Risk factors: {', '.join(self.detection_reasons)}")

        return "; ".join(parts) if parts else "OAuth application requires review"


class OAuthAppConsentModel(Base):
    """Tracks individual user consents for OAuth applications."""

    __tablename__ = "oauth_app_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_apps.id"),
        nullable=False,
        index=True,
        comment="Reference to the OAuth app"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Microsoft Graph user ID"
    )
    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="User email address"
    )
    user_display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User display name"
    )
    consent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of consent (principal, admin)"
    )
    scope: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Consented scope/permissions"
    )
    consent_state: Mapped[str] = mapped_column(
        String(50),
        default="Consented",
        nullable=False,
        comment="Consent state (Consented, Revoked)"
    )
    consented_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="When the user consented"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="When the consent expires"
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

    # Raw data
    consent_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Raw consent data from Graph API"
    )

    __table_args__ = (
        # Composite index for user consent lookups
        Index('ix_oauth_consents_app_user', 'app_id', 'user_id', unique=True),
        # Index for tenant-based queries
        Index('ix_oauth_consents_tenant_user', 'tenant_id', 'user_email'),
    )

    def __repr__(self) -> str:
        return f"<OAuthAppConsent(app={self.app_id}, user={self.user_email})>"


class OAuthAppAlertModel(Base):
    """Alerts specifically for OAuth application violations."""

    __tablename__ = "oauth_app_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_apps.id"),
        nullable=False,
        comment="Reference to the OAuth app"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of alert (new_app, high_risk_permissions, etc.)"
    )
    severity: Mapped[RiskLevel] = mapped_column(
        SQLEnum(RiskLevel, name="oauth_alert_severity_enum"),
        nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    __table_args__ = (
        Index('ix_oauth_app_alerts_unack', 'tenant_id', 'is_acknowledged', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<OAuthAppAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


class OAuthAppPermissionModel(Base):
    """Detailed permission information for OAuth applications."""

    __tablename__ = "oauth_app_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_apps.id"),
        nullable=False,
        index=True,
        comment="Reference to the OAuth app"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Permission ID or value"
    )
    permission_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of permission (Application, Delegated)"
    )
    permission_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Permission value/name"
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Permission display name"
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Permission description"
    )
    is_high_risk: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a high-risk permission"
    )
    risk_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Category of risk (mail, user, files, etc.)"
    )
    is_admin_consent_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether admin consent is required"
    )
    consent_state: Mapped[str] = mapped_column(
        String(50),
        default="NotConsented",
        nullable=False,
        comment="Consent state"
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

    __table_args__ = (
        Index('ix_oauth_permissions_app_perm', 'app_id', 'permission_value', unique=True),
        Index('ix_oauth_permissions_high_risk', 'is_high_risk', 'risk_category'),
    )

    def __repr__(self) -> str:
        return f"<OAuthAppPermission(app={self.app_id}, perm={self.permission_value})>"
