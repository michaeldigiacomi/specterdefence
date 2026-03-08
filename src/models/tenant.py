"""Pydantic models for tenant operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantBase(BaseModel):
    """Base tenant model."""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant display name")
    tenant_id: str = Field(
        ..., min_length=1, max_length=255, description="Azure AD tenant ID (GUID)"
    )

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validate tenant_id format."""
        if not v or not v.strip():
            raise ValueError("tenant_id cannot be empty")
        # Basic UUID format check (with or without hyphens)
        cleaned = v.replace("-", "")
        if len(cleaned) not in [32, 36]:
            raise ValueError("tenant_id must be a valid GUID")
        return v.strip()


class TenantCreate(TenantBase):
    """Model for creating a new tenant."""

    client_id: str = Field(
        ..., min_length=1, max_length=255, description="Azure AD application (client) ID"
    )
    client_secret: str = Field(
        ..., min_length=1, max_length=500, description="Azure AD application client secret"
    )

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client_id format."""
        if not v or not v.strip():
            raise ValueError("client_id cannot be empty")
        cleaned = v.replace("-", "")
        if len(cleaned) not in [32, 36]:
            raise ValueError("client_id must be a valid GUID")
        return v.strip()


class TenantUpdate(BaseModel):
    """Model for updating a tenant."""

    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None
    client_secret: str | None = Field(
        None, min_length=1, max_length=500, description="New Azure AD client secret (optional)"
    )


class TenantResponse(BaseModel):
    """Model for tenant responses (excludes sensitive data)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Internal tenant UUID")
    name: str = Field(..., description="Tenant display name")
    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_id: str = Field(..., description="Azure AD application ID (masked)")
    is_active: bool = Field(..., description="Whether tenant is active")
    connection_status: str = Field(
        ..., description="Connection status: connected, error, timeout, unknown"
    )
    connection_error: str | None = Field(None, description="Last connection error message")
    last_health_check: datetime | None = Field(None, description="Timestamp of last health check")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    ms_tenant_name: str | None = Field(None, description="Microsoft tenant display name")

    @field_validator("client_id")
    @classmethod
    def mask_client_id(cls, v: str) -> str:
        """Mask client_id for security, showing only first 8 and last 4 chars."""
        if len(v) <= 12:
            return "****"
        return f"{v[:8]}...{v[-4:]}"


class TenantDetailResponse(TenantResponse):
    """Model for detailed tenant response."""

    ms_verified_domains: list[dict] | None = Field(None, description="Microsoft verified domains")


class TenantValidationResponse(BaseModel):
    """Model for tenant validation response."""

    valid: bool = Field(..., description="Whether credentials are valid")
    display_name: str | None = Field(None, description="Microsoft tenant display name")
    tenant_id: str | None = Field(None, description="Confirmed tenant ID")
    verified_domains: list[dict] | None = Field(None, description="Verified domains")
    error: str | None = Field(None, description="Error message if validation failed")
    error_code: str | None = Field(None, description="Error code for programmatic handling")


class TenantHealthCheckConnectivity(BaseModel):
    """Model for health check connectivity results."""

    success: bool = Field(..., description="Whether connectivity test succeeded")
    latency_ms: float = Field(0.0, description="Response latency in milliseconds")
    error: str | None = Field(None, description="Error message if failed")


class TenantHealthCheckAuth(BaseModel):
    """Model for health check authentication results."""

    success: bool = Field(..., description="Whether authentication succeeded")
    error: str | None = Field(None, description="Error message if failed")
    error_code: str | None = Field(None, description="Error code for programmatic handling")


class TenantHealthCheckPermissions(BaseModel):
    """Model for health check permission results."""

    success: bool = Field(..., description="Whether all required permissions are granted")
    granted: list[str] = Field(default_factory=list, description="List of granted permissions")
    missing: list[str] = Field(default_factory=list, description="List of missing permissions")
    details: dict | None = Field(None, description="Detailed permission check results")
    error: str | None = Field(None, description="Error message if check failed")


class TenantHealthCheckInfo(BaseModel):
    """Model for health check tenant info."""

    display_name: str | None = Field(None, description="Microsoft tenant display name")
    tenant_id: str | None = Field(None, description="Microsoft tenant ID")
    verified_domains: list[str] = Field(
        default_factory=list, description="List of verified domains"
    )


class TenantHealthCheckResponse(BaseModel):
    """Model for tenant health check response."""

    tenant_id: uuid.UUID = Field(..., description="Internal tenant UUID")
    status: str = Field(
        ..., description="Overall status: healthy, unhealthy, error, timeout, unknown"
    )
    connectivity: TenantHealthCheckConnectivity = Field(
        ..., description="Connectivity test results"
    )
    authentication: TenantHealthCheckAuth = Field(..., description="Authentication test results")
    permissions: TenantHealthCheckPermissions = Field(..., description="Permission check results")
    tenant_info: TenantHealthCheckInfo = Field(
        default_factory=dict, description="Tenant information from Microsoft"
    )
    timestamp: datetime = Field(..., description="Health check timestamp")
    message: str | None = Field(None, description="Human-readable status message")


class TenantListResponse(BaseModel):
    """Model for listing tenants."""

    items: list[TenantResponse]
    total: int


class TenantCreateResponse(BaseModel):
    """Model for tenant creation response."""

    success: bool
    tenant: TenantResponse | None = None
    validation: TenantValidationResponse | None = None
    message: str
