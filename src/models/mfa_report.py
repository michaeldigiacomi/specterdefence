"""MFA Enrollment Tracking models for SpecterDefence."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import ARRAY, JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class MFAMethodType(StrEnum):
    """Types of MFA methods."""
    FIDO2 = "fido2"
    AUTHENTICATOR_APP = "authenticatorApp"
    MICROSOFT_AUTHENTICATOR = "microsoftAuthenticator"
    SMS = "sms"
    VOICE_CALL = "voiceCall"
    EMAIL = "email"
    SOFTWARE_TOKEN = "softwareToken"
    HARDWARE_TOKEN = "hardwareToken"
    HELLO_FOR_BUSINESS = "helloForBusiness"
    PASSWORD = "password"  # Non-MFA
    NONE = "none"  # No method registered


class UserRole(StrEnum):
    """User role types for MFA compliance."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    SERVICE_ACCOUNT = "service_account"


class ComplianceStatus(StrEnum):
    """MFA compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    EXEMPT = "exempt"
    PENDING = "pending"


class MFAStrengthLevel(StrEnum):
    """MFA strength levels based on NIST guidelines."""
    STRONG = "strong"  # FIDO2, hardware tokens
    MODERATE = "moderate"  # Authenticator apps
    WEAK = "weak"  # SMS, voice, email
    NONE = "none"  # No MFA


class MFAUserModel(Base):
    """MFA user enrollment database model."""

    __tablename__ = "mfa_users"

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

    # User identification from Microsoft Graph
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Microsoft Graph user ID"
    )
    user_principal_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="User Principal Name (email)"
    )
    display_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Display name of the user"
    )

    # MFA status
    is_mfa_registered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has MFA registered"
    )
    mfa_methods: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
        comment="List of registered MFA methods"
    )

    # Primary/strength indicators
    primary_mfa_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary/default MFA method"
    )
    mfa_strength: Mapped[MFAStrengthLevel] = mapped_column(
        SQLEnum(MFAStrengthLevel, name="mfa_strength_enum"),
        nullable=False,
        default=MFAStrengthLevel.NONE,
        comment="Calculated MFA strength level"
    )

    # Admin status
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has admin privileges"
    )
    admin_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
        comment="List of admin roles assigned"
    )

    # Compliance tracking
    compliance_status: Mapped[ComplianceStatus] = mapped_column(
        SQLEnum(ComplianceStatus, name="compliance_status_enum"),
        nullable=False,
        default=ComplianceStatus.NON_COMPLIANT,
        comment="Current compliance status"
    )
    compliance_exempt: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user is exempt from MFA requirements"
    )
    exemption_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for MFA exemption"
    )
    exemption_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="When exemption expires"
    )

    # Enrollment tracking
    first_mfa_registration: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="When user first registered MFA"
    )
    last_mfa_update: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="When MFA settings were last updated"
    )

    # User metadata
    account_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether account is enabled"
    )
    sign_in_activity: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last sign-in activity"
    )
    user_type: Mapped[str] = mapped_column(
        String(50),
        default="Member",
        nullable=False,
        comment="User type (Member, Guest, etc.)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        comment="When record was first created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="When record was last updated"
    )
    last_scan_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        comment="When user was last scanned"
    )

    # Raw data
    user_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Raw user data from Graph API"
    )

    __table_args__ = (
        # Composite index for deduplication lookups
        Index('ix_mfa_users_tenant_user', 'tenant_id', 'user_id', unique=True),
        # Index for MFA compliance queries
        Index('ix_mfa_users_compliance', 'tenant_id', 'compliance_status'),
        # Index for admin without MFA queries
        Index('ix_mfa_users_admin_no_mfa', 'tenant_id', 'is_admin', 'is_mfa_registered'),
        # Index for non-compliant users
        Index('ix_mfa_users_non_compliant', 'tenant_id', 'is_mfa_registered', 'compliance_exempt'),
        # Index for exemption queries
        Index('ix_mfa_users_exempt', 'tenant_id', 'compliance_exempt'),
        # Index for strength queries
        Index('ix_mfa_users_strength', 'tenant_id', 'mfa_strength'),
    )

    def __repr__(self) -> str:
        return f"<MFAUser(id={self.id}, upn={self.user_principal_name}, mfa={self.is_mfa_registered})>"

    @property
    def is_compliant(self) -> bool:
        """Check if user is MFA compliant."""
        if self.compliance_exempt:
            return True
        if self.is_admin:
            return self.is_mfa_registered and self.mfa_strength in [
                MFAStrengthLevel.STRONG, MFAStrengthLevel.MODERATE
            ]
        return self.is_mfa_registered

    @property
    def needs_attention(self) -> bool:
        """Check if user needs attention for MFA enrollment."""
        if self.compliance_exempt:
            return False
        if not self.account_enabled:
            return False
        if not self.is_mfa_registered:
            return True
        return bool(self.is_admin and self.mfa_strength == MFAStrengthLevel.WEAK)


class MFAEnrollmentHistoryModel(Base):
    """Tracks MFA enrollment history over time."""

    __tablename__ = "mfa_enrollment_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )

    # Snapshot data
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="Date of this snapshot"
    )

    # Enrollment counts
    total_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    mfa_registered_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    non_compliant_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Admin counts
    total_admins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    admins_with_mfa: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    admins_without_mfa: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Method breakdown
    fido2_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    authenticator_app_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    sms_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    voice_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Strength breakdown
    strong_mfa_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    moderate_mfa_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    weak_mfa_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Exemptions
    exempt_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Calculated percentages
    mfa_coverage_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    admin_mfa_coverage_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    __table_args__ = (
        # Unique constraint for one snapshot per tenant per day
        Index('ix_mfa_history_tenant_date', 'tenant_id', 'snapshot_date', unique=True),
        # Index for trend queries
        Index('ix_mfa_history_trends', 'tenant_id', 'snapshot_date'),
    )

    def __repr__(self) -> str:
        return f"<MFAEnrollmentHistory(tenant={self.tenant_id}, date={self.snapshot_date}, coverage={self.mfa_coverage_percentage})>"


class MFAComplianceAlertModel(Base):
    """Alerts for MFA compliance issues."""

    __tablename__ = "mfa_compliance_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mfa_users.id"),
        nullable=False,
        index=True
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type of alert (admin_no_mfa, weak_mfa, etc.)"
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Alert severity (critical, high, medium, low)"
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Alert state
    is_resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # Metadata
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
        Index('ix_mfa_alerts_unresolved', 'tenant_id', 'is_resolved', 'created_at'),
        Index('ix_mfa_alerts_severity', 'severity', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<MFAComplianceAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


# Pydantic models for API requests/responses


class MFAMethod(BaseModel):
    """MFA method details."""
    method_type: str
    display_name: str
    is_default: bool = False
    created_date_time: datetime | None = None


class MFAUserBase(BaseModel):
    """Base model for MFA user data."""
    user_principal_name: str
    display_name: str
    is_mfa_registered: bool = False


class MFAUserResponse(MFAUserBase):
    """Response model for MFA user."""
    id: str
    tenant_id: str
    user_id: str
    mfa_methods: list[str]
    primary_mfa_method: str | None
    mfa_strength: MFAStrengthLevel
    is_admin: bool
    admin_roles: list[str]
    compliance_status: ComplianceStatus
    compliance_exempt: bool
    exemption_reason: str | None
    first_mfa_registration: datetime | None
    last_mfa_update: datetime | None
    account_enabled: bool
    user_type: str
    created_at: datetime
    updated_at: datetime
    needs_attention: bool

    class Config:
        from_attributes = True


class MFAUserListResponse(BaseModel):
    """Response model for listing MFA users."""
    items: list[MFAUserResponse]
    total: int
    limit: int
    offset: int


class MFAEnrollmentSummary(BaseModel):
    """Summary of MFA enrollment for a tenant."""
    tenant_id: str
    snapshot_date: datetime

    # User counts
    total_users: int
    mfa_registered_users: int
    non_compliant_users: int

    # Admin counts
    total_admins: int
    admins_with_mfa: int
    admins_without_mfa: int

    # Method breakdown
    fido2_users: int
    authenticator_app_users: int
    sms_users: int
    voice_users: int

    # Strength breakdown
    strong_mfa_users: int
    moderate_mfa_users: int
    weak_mfa_users: int

    # Exemptions
    exempt_users: int

    # Calculated percentages
    mfa_coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    admin_mfa_coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    compliance_rate: float = Field(..., ge=0.0, le=100.0)

    # Status indicators
    meets_admin_requirement: bool  # 100% for admins
    meets_user_target: bool  # 95% for users


class MFAEnrollmentTrend(BaseModel):
    """MFA enrollment trend data point."""
    date: datetime
    total_users: int
    mfa_registered_users: int
    mfa_coverage_percentage: float
    admin_mfa_coverage_percentage: float


class MFAEnrollmentTrendsResponse(BaseModel):
    """Response model for MFA enrollment trends."""
    tenant_id: str
    trends: list[MFAEnrollmentTrend]
    period_days: int


class MFAComplianceReport(BaseModel):
    """MFA compliance report."""
    tenant_id: str
    generated_at: datetime

    # Summary
    summary: MFAEnrollmentSummary

    # Non-compliant users
    non_compliant_users: list[MFAUserResponse]

    # Admin users without MFA (critical)
    admins_without_mfa: list[MFAUserResponse]

    # Weak MFA usage
    users_with_weak_mfa: list[MFAUserResponse]

    # Recommendations
    recommendations: list[str]


class MFAMethodDistribution(BaseModel):
    """Distribution of MFA methods."""
    method_type: str
    count: int
    percentage: float


class MFAMethodsDistributionResponse(BaseModel):
    """Response model for MFA methods distribution."""
    tenant_id: str
    total_mfa_users: int
    distribution: list[MFAMethodDistribution]


class MFAStrengthDistribution(BaseModel):
    """Distribution of MFA strength levels."""
    strength_level: MFAStrengthLevel
    count: int
    percentage: float


class MFAStrengthDistributionResponse(BaseModel):
    """Response model for MFA strength distribution."""
    tenant_id: str
    distribution: list[MFAStrengthDistribution]
    strong_mfa_percentage: float
    moderate_mfa_percentage: float
    weak_mfa_percentage: float
    no_mfa_percentage: float


class MFAScanRequest(BaseModel):
    """Request model for triggering MFA scan."""
    tenant_id: str
    full_scan: bool = True
    check_compliance: bool = True


class MFAScanResponse(BaseModel):
    """Response model for MFA scan."""
    success: bool
    tenant_id: str
    users_scanned: int
    new_mfa_registrations: int
    compliance_violations: int
    critical_findings: int
    message: str


class MFAComplianceThresholds(BaseModel):
    """MFA compliance thresholds configuration."""
    admin_mfa_required: bool = True
    admin_mfa_strength: MFAStrengthLevel = MFAStrengthLevel.MODERATE
    user_mfa_target_percentage: float = Field(default=95.0, ge=0.0, le=100.0)
    prefer_strong_mfa: bool = True


class MFAExemptionRequest(BaseModel):
    """Request model for MFA exemption."""
    exemption_reason: str = Field(..., min_length=1, max_length=1000)
    expires_at: datetime | None = None


class MFAExemptionResponse(BaseModel):
    """Response model for MFA exemption."""
    success: bool
    user_id: str
    exemption_granted: bool
    exemption_reason: str | None
    expires_at: datetime | None
    message: str


class MFAResolveAlertRequest(BaseModel):
    """Request model for resolving MFA alert."""
    resolved_by: str = Field(..., min_length=1)


class MFAResolveAlertResponse(BaseModel):
    """Response model for resolving MFA alert."""
    success: bool
    alert_id: str
    is_resolved: bool
    resolved_at: datetime | None
    message: str
