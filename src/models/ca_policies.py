"""Conditional Access policy models for SpecterDefence."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import ARRAY, JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


class PolicyState(StrEnum):
    """State of a Conditional Access policy."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    REPORT_ONLY = "reportOnly"


class PolicyEffect(StrEnum):
    """Effect of a Conditional Access policy."""

    BLOCK = "block"
    MFA_REQUIRED = "mfaRequired"
    DEVICE_COMPLIANT_REQUIRED = "deviceCompliantRequired"
    APP_ENFORCED_RESTRICTIONS = "appEnforcedRestrictions"
    SIGN_IN_FREQUENCY = "signInFrequency"
    CUSTOM = "custom"


class ChangeType(StrEnum):
    """Type of policy change."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ENABLED = "enabled"
    DISABLED = "disabled"
    BASELINE_DRIFT = "baseline_drift"


class AlertSeverity(StrEnum):
    """Severity levels for CA policy alerts."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CAPolicyModel(Base):
    """Conditional Access policy database model."""

    __tablename__ = "ca_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="Internal tenant UUID",
    )

    # Policy identification from Microsoft Graph
    policy_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Microsoft Graph Conditional Access policy ID",
    )
    display_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Display name of the policy"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Policy description"
    )

    # Policy state
    state: Mapped[PolicyState] = mapped_column(
        SQLEnum(PolicyState, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PolicyState.ENABLED,
        comment="Current state of the policy",
    )

    # Grant controls (authentication requirements)
    grant_controls_operator: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Grant controls operator (AND/OR)"
    )
    grant_controls: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
        comment="List of grant control requirements (mfa, deviceCompliance, etc.)",
    )

    # Session controls
    sign_in_frequency: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Sign-in frequency in hours"
    )
    sign_in_frequency_authentication_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Sign-in frequency authentication type"
    )

    # Targets (who/what the policy applies to)
    applies_to_all_users: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy applies to all users"
    )
    applies_to_all_apps: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy applies to all applications"
    )
    includes_guests_or_external: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether policy includes guest/external users",
    )
    includes_vip_users: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy includes VIP user groups"
    )

    # Risk conditions
    requires_high_risk_level: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether policy targets high risk level sign-ins",
    )
    requires_medium_risk_level: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether policy targets medium risk level sign-ins",
    )
    requires_low_risk_level: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether policy targets low risk level sign-ins",
    )

    # Location-based conditions
    has_location_conditions: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether policy has location-based conditions",
    )
    trusted_locations_only: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy requires trusted locations"
    )
    has_device_conditions: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy has device conditions"
    )

    # Device conditions
    requires_compliant_device: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy requires compliant device"
    )
    requires_hybrid_joined_device: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether policy requires hybrid joined device",
    )

    # Platform conditions
    includes_mobile_platforms: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy includes mobile platforms"
    )

    # Security analysis
    is_mfa_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether MFA is required by this policy"
    )
    is_baseline_policy: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is part of the security baseline",
    )
    baseline_compliant: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether policy complies with security baseline",
    )
    security_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Calculated security score (0-100)"
    )

    # Change tracking
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="When policy was first detected"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="When policy was last updated",
    )
    last_scan_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="When policy was last scanned"
    )
    policy_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When policy was created in Azure AD"
    )
    policy_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When policy was last modified in Azure AD"
    )

    # Raw data
    policy_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Raw policy data from Graph API"
    )

    __table_args__ = (
        # Composite index for deduplication lookups
        Index("ix_ca_policies_tenant_policy", "tenant_id", "policy_id", unique=True),
        # Index for policy state queries
        Index("ix_ca_policies_state", "state"),
        # Index for security baseline queries
        Index("ix_ca_policies_baseline", "tenant_id", "is_baseline_policy", "baseline_compliant"),
        # Index for MFA policy queries
        Index("ix_ca_policies_mfa", "tenant_id", "is_mfa_required", "state"),
        # Index for disabled policies
        Index("ix_ca_policies_disabled", "tenant_id", "state"),
    )

    def __repr__(self) -> str:
        return f"<CAPolicy(id={self.id}, name={self.display_name}, state={self.state})>"

    def generate_alert_title(self, change_type: ChangeType) -> str:
        """Generate alert title based on change type."""
        titles = {
            ChangeType.DISABLED: f"CA Policy Disabled: {self.display_name}",
            ChangeType.DELETED: f"CA Policy Deleted: {self.display_name}",
            ChangeType.BASELINE_DRIFT: f"CA Policy Baseline Drift: {self.display_name}",
            ChangeType.CREATED: f"New CA Policy Created: {self.display_name}",
            ChangeType.UPDATED: f"CA Policy Modified: {self.display_name}",
            ChangeType.ENABLED: f"CA Policy Enabled: {self.display_name}",
        }
        return titles.get(change_type, f"CA Policy Change: {self.display_name}")

    def generate_alert_description(
        self, change_type: ChangeType, details: dict[str, Any] = None
    ) -> str:
        """Generate detailed alert description."""
        parts = []

        if change_type == ChangeType.DISABLED:
            parts.append("Policy has been disabled, potentially reducing tenant security posture.")
        elif change_type == ChangeType.DELETED:
            parts.append("Policy has been permanently deleted.")
        elif change_type == ChangeType.BASELINE_DRIFT:
            parts.append("Policy no longer complies with the established security baseline.")
        elif change_type == ChangeType.CREATED:
            parts.append("New Conditional Access policy has been created.")

        if self.is_mfa_required and change_type in [ChangeType.DISABLED, ChangeType.DELETED]:
            parts.append("WARNING: This policy previously required MFA authentication.")

        if self.applies_to_all_users and change_type in [ChangeType.DISABLED, ChangeType.DELETED]:
            parts.append("WARNING: This policy applied to all users.")

        if self.applies_to_all_apps and change_type in [ChangeType.DISABLED, ChangeType.DELETED]:
            parts.append("WARNING: This policy applied to all applications.")

        if self.requires_compliant_device:
            parts.append("Requires compliant device.")

        if self.has_location_conditions:
            parts.append("Has location-based conditions.")

        if details and details.get("changes"):
            parts.append(f"Changes: {', '.join(details['changes'])}")

        return " ".join(parts) if parts else "Conditional Access policy change detected."


class CAPolicyChangeModel(Base):
    """Tracks changes to Conditional Access policies."""

    __tablename__ = "ca_policy_changes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ca_policies.id"),
        nullable=False,
        index=True,
        comment="Reference to the CA policy",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # Change details
    change_type: Mapped[ChangeType] = mapped_column(
        SQLEnum(ChangeType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Type of change detected",
    )
    changed_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="User who made the change (if available)"
    )
    changed_by_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Email of user who made the change"
    )

    # Change analysis
    changes_summary: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)), default=list, nullable=False, comment="Summary of changes made"
    )

    # Security impact
    security_impact: Mapped[str] = mapped_column(
        String(50),
        default="none",
        nullable=False,
        comment="Security impact (none, low, medium, high, critical)",
    )
    mfa_removed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether MFA requirement was removed"
    )
    broadened_scope: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy scope was broadened"
    )
    narrowed_scope: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether policy scope was narrowed"
    )

    # Raw data
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Previous policy state"
    )
    new_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="New policy state"
    )

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="When the change was detected"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        # Index for policy change history
        Index("ix_ca_changes_policy", "policy_id", "detected_at"),
        # Index for tenant-based queries
        Index("ix_ca_changes_tenant", "tenant_id", "detected_at"),
        # Index for high-impact changes
        Index("ix_ca_changes_impact", "tenant_id", "security_impact"),
    )

    def __repr__(self) -> str:
        return f"<CAPolicyChange(id={self.id}, type={self.change_type}, policy={self.policy_id})>"


class CAPolicyAlertModel(Base):
    """Alerts specifically for Conditional Access policy changes."""

    __tablename__ = "ca_policy_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ca_policies.id"),
        nullable=False,
        index=True,
        comment="Reference to the CA policy",
    )
    change_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ca_policy_changes.id"),
        nullable=True,
        comment="Reference to the policy change",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # Alert details
    alert_type: Mapped[ChangeType] = mapped_column(
        SQLEnum(ChangeType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Detection context
    detection_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)), default=list, nullable=False
    )

    # Alert state
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_ca_alerts_unack", "tenant_id", "is_acknowledged", "created_at"),
        Index("ix_ca_alerts_severity", "severity", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CAPolicyAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


class CABaselineConfigModel(Base):
    """Security baseline configuration for Conditional Access policies."""

    __tablename__ = "ca_baseline_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        unique=True,
        comment="Internal tenant UUID",
    )

    # Baseline requirements
    require_mfa_for_admins: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Require MFA for admin accounts"
    )
    require_mfa_for_all_users: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Require MFA for all users"
    )
    block_legacy_auth: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Block legacy authentication"
    )
    require_compliant_or_hybrid_joined: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Require compliant or hybrid joined devices"
    )
    block_high_risk_signins: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Block high risk sign-ins"
    )
    block_unknown_locations: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Block sign-ins from unknown locations"
    )
    require_mfa_for_guests: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Require MFA for guest/external users"
    )

    # Custom requirements
    custom_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Custom baseline requirements"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="User who created the baseline"
    )

    __table_args__ = (Index("ix_ca_baseline_tenant", "tenant_id"),)

    def __repr__(self) -> str:
        return f"<CABaselineConfig(tenant={self.tenant_id})>"


# Pydantic models for API requests/responses


class CAPolicyBase(BaseModel):
    """Base model for CA policies."""

    display_name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    state: PolicyState = PolicyState.ENABLED


class CAPolicyCreate(CAPolicyBase):
    """Model for creating a CA policy record."""

    policy_id: str
    policy_data: dict[str, Any] = {}


class CAPolicyUpdate(BaseModel):
    """Model for updating a CA policy record."""

    display_name: str | None = None
    description: str | None = None
    state: PolicyState | None = None
    is_baseline_policy: bool | None = None


class CAPolicyResponse(CAPolicyBase):
    """Response model for CA policies."""

    id: str
    tenant_id: str
    policy_id: str
    grant_controls: list[str]
    is_mfa_required: bool
    applies_to_all_users: bool
    applies_to_all_apps: bool
    is_baseline_policy: bool
    baseline_compliant: bool
    security_score: int
    state: PolicyState
    created_at: datetime
    updated_at: datetime
    last_scan_at: datetime

    class Config:
        from_attributes = True


class CAPolicyListResponse(BaseModel):
    """Response model for listing CA policies."""

    items: list[CAPolicyResponse]
    total: int
    limit: int
    offset: int


class CAPolicyChangeResponse(BaseModel):
    """Response model for CA policy changes."""

    id: str
    policy_id: str
    tenant_id: str
    change_type: ChangeType
    changed_by: str | None
    changed_by_email: str | None
    changes_summary: list[str]
    security_impact: str
    mfa_removed: bool
    detected_at: datetime

    class Config:
        from_attributes = True


class CAPolicyChangeListResponse(BaseModel):
    """Response model for listing CA policy changes."""

    items: list[CAPolicyChangeResponse]
    total: int
    limit: int
    offset: int


class CAPolicyAlertResponse(BaseModel):
    """Response model for CA policy alerts."""

    id: str
    policy_id: str
    tenant_id: str
    alert_type: ChangeType
    severity: AlertSeverity
    title: str
    description: str
    is_acknowledged: bool
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class CAPolicyAlertListResponse(BaseModel):
    """Response model for listing CA policy alerts."""

    items: list[CAPolicyAlertResponse]
    total: int
    limit: int
    offset: int


class CABaselineConfigBase(BaseModel):
    """Base model for baseline configuration."""

    require_mfa_for_admins: bool = True
    require_mfa_for_all_users: bool = False
    block_legacy_auth: bool = True
    require_compliant_or_hybrid_joined: bool = False
    block_high_risk_signins: bool = True
    block_unknown_locations: bool = False
    require_mfa_for_guests: bool = True
    custom_requirements: dict[str, Any] = {}


class CABaselineConfigCreate(CABaselineConfigBase):
    """Model for creating baseline configuration."""

    tenant_id: str
    created_by: str | None = None


class CABaselineConfigResponse(CABaselineConfigBase):
    """Response model for baseline configuration."""

    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    class Config:
        from_attributes = True


class CAPolicyScanRequest(BaseModel):
    """Request model for triggering a CA policy scan."""

    tenant_id: str
    trigger_alerts: bool = True
    compare_baseline: bool = True


class CAPolicyScanResponse(BaseModel):
    """Response model for CA policy scan."""

    success: bool
    tenant_id: str
    policies_found: int
    changes_detected: int
    alerts_triggered: int
    baseline_violations: int
    message: str


class AcknowledgeAlertRequest(BaseModel):
    """Request model for acknowledging an alert."""

    acknowledged_by: str = Field(..., min_length=1)


class CAPolicySummary(BaseModel):
    """Summary of CA policies for a tenant."""

    total_policies: int
    enabled: int
    disabled: int
    report_only: int
    mfa_policies: int
    baseline_policies: int
    baseline_compliant: int
    baseline_violations: int
    recent_changes: int
    high_severity_alerts: int
    policies_covering_all_users: int
    policies_covering_all_apps: int
