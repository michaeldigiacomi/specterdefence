"""OAuth applications API endpoints for SpecterDefence."""


from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
import uuid
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.oauth_apps import (
    AppStatus,
    OAuthAppModel,
    PublisherType,
    RiskLevel,
)
from src.services.oauth_apps import OAuthAppsService

router = APIRouter()


# =============================================================================
# Pydantic Models for API Requests/Responses
# =============================================================================


class OAuthAppResponse(BaseModel):
    """Response model for an OAuth application."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    app_id: str
    display_name: str
    description: str | None
    publisher_name: str | None
    publisher_id: str | None
    publisher_type: str
    is_microsoft_publisher: bool
    is_verified_publisher: bool
    risk_level: str
    status: str
    risk_score: int
    permission_count: int
    high_risk_permissions: list[str]
    has_mail_permissions: bool
    has_user_read_all: bool
    has_group_read_all: bool
    has_files_read_all: bool
    has_calendar_access: bool
    has_admin_consent: bool
    consent_count: int
    admin_consented: bool
    is_new_app: bool
    detection_reasons: list[str]
    app_created_at: str | None
    first_seen_at: str
    last_scan_at: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OAuthAppListResponse(BaseModel):
    """Response model for listing OAuth apps."""

    items: list[OAuthAppResponse]
    total: int
    limit: int
    offset: int


class OAuthAppPermissionResponse(BaseModel):
    """Response model for an OAuth app permission."""

    id: uuid.UUID
    permission_id: str
    permission_type: str
    permission_value: str
    display_name: str | None
    description: str | None
    is_high_risk: bool
    risk_category: str | None
    is_admin_consent_required: bool
    consent_state: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OAuthAppConsentResponse(BaseModel):
    """Response model for an OAuth app consent."""

    id: uuid.UUID
    user_id: str
    user_email: str
    user_display_name: str | None
    consent_type: str
    scope: str
    consent_state: str
    consented_at: str | None
    expires_at: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OAuthAppAlertResponse(BaseModel):
    """Response model for an OAuth app alert."""

    id: uuid.UUID
    app_id: uuid.UUID
    tenant_id: uuid.UUID
    alert_type: str
    severity: str
    title: str
    description: str
    is_acknowledged: bool
    acknowledged_by: str | None
    acknowledged_at: str | None
    created_at: str

    class Config:
        from_attributes = True


class OAuthAppAlertListResponse(BaseModel):
    """Response model for listing OAuth app alerts."""

    items: list[OAuthAppAlertResponse]
    total: int
    limit: int
    offset: int


class ScanRequest(BaseModel):
    """Request model for triggering an OAuth app scan."""

    tenant_id: uuid.UUID | None = Field(
        None, description="Specific tenant to scan (if not provided, scans all tenants)"
    )
    trigger_alerts: bool = Field(True, description="Whether to trigger alerts for suspicious apps")


class ScanResponse(BaseModel):
    """Response model for scan operation."""

    success: bool
    tenant_id: uuid.UUID | None
    results: dict
    message: str


class RevokeAppRequest(BaseModel):
    """Request model for revoking an OAuth app."""

    revoke_type: str = Field("disable", description="Type of revocation (disable, delete)")


class RevokeAppResponse(BaseModel):
    """Response model for revoke operation."""

    success: bool
    message: str
    error: str | None = None


class AcknowledgeAlertRequest(BaseModel):
    """Request model for acknowledging an alert."""

    acknowledged_by: str = Field(..., min_length=1, description="User acknowledging the alert")


class AcknowledgeAlertResponse(BaseModel):
    """Response model for acknowledging an alert."""

    success: bool
    alert: OAuthAppAlertResponse | None
    message: str


class OAuthAppsSummary(BaseModel):
    """Summary of OAuth applications."""

    total_apps: int
    by_risk_level: dict
    by_status: dict
    mail_access_apps: int
    unverified_publisher_apps: int
    total_alerts: int
    unacknowledged_alerts: int


class AppPermissionsResponse(BaseModel):
    """Response model for app permissions."""

    app: OAuthAppResponse
    permissions: list[OAuthAppPermissionResponse]
    consents: list[OAuthAppConsentResponse]


# =============================================================================
# Dependencies
# =============================================================================


async def get_oauth_apps_service(db: AsyncSession = Depends(get_db)) -> OAuthAppsService:
    """Dependency to get OAuth apps service."""
    return OAuthAppsService(db)


# =============================================================================
# Helper Functions
# =============================================================================


def _format_app_response(app: OAuthAppModel) -> OAuthAppResponse:
    """Format an app model for response."""
    return OAuthAppResponse(
        id=str(app.id),
        tenant_id=app.tenant_id,
        app_id=app.app_id,
        display_name=app.display_name,
        description=app.description,
        publisher_name=app.publisher_name,
        publisher_id=app.publisher_id,
        publisher_type=app.publisher_type.value,
        is_microsoft_publisher=app.is_microsoft_publisher,
        is_verified_publisher=app.is_verified_publisher,
        risk_level=app.risk_level.value,
        status=app.status.value,
        risk_score=app.risk_score,
        permission_count=app.permission_count,
        high_risk_permissions=app.high_risk_permissions,
        has_mail_permissions=app.has_mail_permissions,
        has_user_read_all=app.has_user_read_all,
        has_group_read_all=app.has_group_read_all,
        has_files_read_all=app.has_files_read_all,
        has_calendar_access=app.has_calendar_access,
        has_admin_consent=app.has_admin_consent,
        consent_count=app.consent_count,
        admin_consented=app.admin_consented,
        is_new_app=app.is_new_app,
        detection_reasons=app.detection_reasons,
        app_created_at=app.app_created_at.isoformat() if app.app_created_at else None,
        first_seen_at=app.first_seen_at.isoformat(),
        last_scan_at=app.last_scan_at.isoformat(),
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
    )


# =============================================================================
# OAuth Apps Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=OAuthAppListResponse,
    summary="List OAuth applications",
    description="List OAuth applications across all tenants with optional filtering.",
)
async def list_oauth_apps(
    tenant_id: str | None = None,
    status: str | None = None,
    risk_level: str | None = None,
    publisher_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> OAuthAppListResponse:
    """List OAuth applications with filtering.

    Args:
        tenant_id: Filter by tenant UUID
        status: Filter by status (approved, suspicious, malicious, revoked, pending_review)
        risk_level: Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)
        publisher_type: Filter by publisher type (microsoft, verified, unverified, unknown)
        limit: Maximum results (1-1000)
        offset: Offset for pagination
        service: OAuth apps service

    Returns:
        Paginated list of OAuth apps
    """
    # Convert string enums
    status_enum = None
    risk_enum = None
    publisher_enum = None

    if status:
        try:
            status_enum = AppStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status}"
            )

    if risk_level:
        try:
            risk_enum = RiskLevel(risk_level.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk level: {risk_level}",
            )

    if publisher_type:
        try:
            publisher_enum = PublisherType(publisher_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid publisher type: {publisher_type}",
            )

    result = await service.get_apps(
        tenant_id=tenant_id,
        status=status_enum,
        risk_level=risk_enum,
        publisher_type=publisher_enum,
        limit=limit,
        offset=offset,
    )

    return OAuthAppListResponse(
        items=[_format_app_response(app) for app in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )



# =============================================================================
# Tenant-Specific Endpoints
# =============================================================================


@router.get(
    "/tenants/{tenant_id}/apps",
    response_model=OAuthAppListResponse,
    summary="Get tenant OAuth apps",
    description="Get all OAuth applications for a specific tenant.",
)
async def get_tenant_oauth_apps(
    tenant_id: str,
    status: str | None = None,
    risk_level: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> OAuthAppListResponse:
    """Get OAuth apps for a specific tenant.

    Args:
        tenant_id: Tenant UUID
        status: Filter by status
        risk_level: Filter by risk level
        limit: Maximum results
        offset: Offset for pagination
        service: OAuth apps service

    Returns:
        Paginated list of OAuth apps
    """
    # Convert string enums
    status_enum = None
    risk_enum = None

    if status:
        try:
            status_enum = AppStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status}"
            )

    if risk_level:
        try:
            risk_enum = RiskLevel(risk_level.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk level: {risk_level}",
            )

    result = await service.get_apps(
        tenant_id=tenant_id, status=status_enum, risk_level=risk_enum, limit=limit, offset=offset
    )

    return OAuthAppListResponse(
        items=[_format_app_response(app) for app in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get(
    "/tenants/{tenant_id}/suspicious",
    response_model=list[OAuthAppResponse],
    summary="Get suspicious apps",
    description="Get suspicious and malicious OAuth apps for a tenant.",
)
async def get_suspicious_apps(
    tenant_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> list[OAuthAppResponse]:
    """Get suspicious and malicious OAuth apps.

    Args:
        tenant_id: Tenant UUID
        limit: Maximum results
        service: OAuth apps service

    Returns:
        List of suspicious/malicious apps
    """
    apps = await service.get_suspicious_apps(tenant_id=tenant_id, limit=limit)

    return [_format_app_response(app) for app in apps]


@router.get(
    "/tenants/{tenant_id}/high-risk",
    response_model=list[OAuthAppResponse],
    summary="Get high-risk apps",
    description="Get high-risk and critical OAuth apps for a tenant.",
)
async def get_high_risk_apps(
    tenant_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> list[OAuthAppResponse]:
    """Get high-risk and critical OAuth apps.

    Args:
        tenant_id: Tenant UUID
        limit: Maximum results
        service: OAuth apps service

    Returns:
        List of high-risk apps
    """
    apps = await service.get_high_risk_apps(tenant_id=tenant_id, limit=limit)

    return [_format_app_response(app) for app in apps]


@router.get(
    "/tenants/{tenant_id}/summary",
    response_model=OAuthAppsSummary,
    summary="Get apps summary",
    description="Get summary of OAuth apps for a tenant.",
)
async def get_oauth_apps_summary(
    tenant_id: str, service: OAuthAppsService = Depends(get_oauth_apps_service)
) -> OAuthAppsSummary:
    """Get summary of OAuth apps.

    Args:
        tenant_id: Tenant UUID
        service: OAuth apps service

    Returns:
        Summary of OAuth apps
    """
    summary = await service.get_apps_summary(tenant_id=tenant_id)

    return OAuthAppsSummary(
        total_apps=summary["total_apps"],
        by_risk_level=summary["by_risk_level"],
        by_status=summary["by_status"],
        mail_access_apps=summary["mail_access_apps"],
        unverified_publisher_apps=summary["unverified_publisher_apps"],
        total_alerts=summary["total_alerts"],
        unacknowledged_alerts=summary["unacknowledged_alerts"],
    )


# =============================================================================
# Scan Endpoints
# =============================================================================


@router.post(
    "/scan",
    response_model=ScanResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Trigger OAuth app scan",
    description="Trigger a manual scan of OAuth applications for a tenant.",
)
async def scan_oauth_apps(
    request: ScanRequest, service: OAuthAppsService = Depends(get_oauth_apps_service)
) -> ScanResponse:
    """Trigger a manual scan of OAuth applications.

    Args:
        request: Scan request parameters
        service: OAuth apps service

    Returns:
        Scan results summary

    Raises:
        HTTPException: If tenant not found or scan fails
    """
    if not request.tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="tenant_id is required"
        )

    try:
        results = await service.scan_tenant_oauth_apps(
            tenant_id=request.tenant_id, trigger_alerts=request.trigger_alerts
        )

        return ScanResponse(
            success=True,
            tenant_id=request.tenant_id,
            results=results,
            message=f"Scan completed successfully. Found {results['total_apps']} apps, "
            f"{results['suspicious_apps']} suspicious, {results['malicious_apps']} malicious.",
        )
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Scan failed: {str(e)}"
        )


# =============================================================================
# Alert Endpoints
# =============================================================================


@router.get(
    "/alerts",
    response_model=OAuthAppAlertListResponse,
    summary="List OAuth app alerts",
    description="List OAuth app alerts with optional filtering.",
)
async def list_oauth_app_alerts(
    tenant_id: str | None = None,
    acknowledged: bool | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> OAuthAppAlertListResponse:
    """List OAuth app alerts.

    Args:
        tenant_id: Filter by tenant
        acknowledged: Filter by acknowledgment status
        severity: Filter by severity
        limit: Maximum results
        offset: Offset for pagination
        service: OAuth apps service

    Returns:
        Paginated list of alerts
    """
    severity_enum = None
    if severity:
        try:
            severity_enum = RiskLevel(severity.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid severity: {severity}"
            )

    result = await service.get_alerts(
        tenant_id=tenant_id,
        acknowledged=acknowledged,
        severity=severity_enum,
        limit=limit,
        offset=offset,
    )

    return OAuthAppAlertListResponse(
        items=[
            OAuthAppAlertResponse(
                id=str(alert.id),
                app_id=str(alert.app_id),
                tenant_id=alert.tenant_id,
                alert_type=alert.alert_type,
                severity=alert.severity.value,
                title=alert.title,
                description=alert.description,
                is_acknowledged=alert.is_acknowledged,
                acknowledged_by=alert.acknowledged_by,
                acknowledged_at=alert.acknowledged_at.isoformat()
                if alert.acknowledged_at
                else None,
                created_at=alert.created_at.isoformat(),
            )
            for alert in result["items"]
        ],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AcknowledgeAlertResponse,
    summary="Acknowledge alert",
    description="Acknowledge an OAuth app alert.",
)
async def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeAlertRequest,
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> AcknowledgeAlertResponse:
    """Acknowledge an OAuth app alert.

    Args:
        alert_id: Alert UUID
        request: Acknowledgment request
        service: OAuth apps service

    Returns:
        Acknowledgment result

    Raises:
        HTTPException: If alert not found
    """
    alert = await service.acknowledge_alert(alert_id, request.acknowledged_by)

    if not alert:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=f"Alert with ID {alert_id} not found"
        )

    return AcknowledgeAlertResponse(
        success=True,
        alert=OAuthAppAlertResponse(
            id=str(alert.id),
            app_id=str(alert.app_id),
            tenant_id=alert.tenant_id,
            alert_type=alert.alert_type,
            severity=alert.severity.value,
            title=alert.title,
            description=alert.description,
            is_acknowledged=alert.is_acknowledged,
            acknowledged_by=alert.acknowledged_by,
            acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            created_at=alert.created_at.isoformat(),
        ),
        message="Alert acknowledged successfully",
    )


# =============================================================================
# ID-based Endpoints (Must be at the end to avoid routing conflicts)
# =============================================================================

@router.get(
    "/{app_id}",
    response_model=OAuthAppResponse,
    summary="Get OAuth application",
    description="Get a specific OAuth application by ID.",
)
async def get_oauth_app(
    app_id: str, service: OAuthAppsService = Depends(get_oauth_apps_service)
) -> OAuthAppResponse:
    """Get a specific OAuth application.

    Args:
        app_id: App UUID
        service: OAuth apps service

    Returns:
        OAuth app details

    Raises:
        HTTPException: If app not found
    """
    app = await service.get_app_by_id(app_id)
    if not app:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"OAuth app with ID {app_id} not found",
        )

    return _format_app_response(app)


@router.get(
    "/{app_id}/permissions",
    response_model=AppPermissionsResponse,
    summary="Get app permissions",
    description="Get detailed permissions and consents for an OAuth application.",
)
async def get_app_permissions(
    app_id: str, service: OAuthAppsService = Depends(get_oauth_apps_service)
) -> AppPermissionsResponse:
    """Get permissions and consents for an OAuth app.

    Args:
        app_id: App UUID
        service: OAuth apps service

    Returns:
        App with permissions and consents

    Raises:
        HTTPException: If app not found
    """
    app = await service.get_app_by_id(app_id)
    if not app:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"OAuth app with ID {app_id} not found",
        )

    permissions = await service.get_app_permissions_detail(app_id)
    consents = await service.get_app_consents(app_id)

    return AppPermissionsResponse(
        app=_format_app_response(app),
        permissions=[
            OAuthAppPermissionResponse(
                id=str(p.id),
                permission_id=p.permission_id,
                permission_type=p.permission_type,
                permission_value=p.permission_value,
                display_name=p.display_name,
                description=p.description,
                is_high_risk=p.is_high_risk,
                risk_category=p.risk_category,
                is_admin_consent_required=p.is_admin_consent_required,
                consent_state=p.consent_state,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in permissions
        ],
        consents=[
            OAuthAppConsentResponse(
                id=str(c.id),
                user_id=c.user_id,
                user_email=c.user_email,
                user_display_name=c.user_display_name,
                consent_type=c.consent_type,
                scope=c.scope,
                consent_state=c.consent_state,
                consented_at=c.consented_at.isoformat() if c.consented_at else None,
                expires_at=c.expires_at.isoformat() if c.expires_at else None,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
            )
            for c in consents
        ],
    )


@router.post(
    "/{app_id}/revoke",
    response_model=RevokeAppResponse,
    summary="Revoke OAuth application",
    description="Revoke/suspend a suspicious OAuth application.",
)
async def revoke_oauth_app(
    app_id: str,
    request: RevokeAppRequest,
    service: OAuthAppsService = Depends(get_oauth_apps_service),
) -> RevokeAppResponse:
    """Revoke/suspend an OAuth application.

    Args:
        app_id: App UUID
        request: Revoke request
        service: OAuth apps service

    Returns:
        Revoke result
    """
    result = await service.revoke_app(app_id, request.revoke_type)

    if result["success"]:
        return RevokeAppResponse(
            success=True, message=result.get("message", "App revoked successfully")
        )
    else:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to revoke app"),
        )

