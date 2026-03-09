"""Conditional Access policies API endpoints for SpecterDefence."""


from src.api.auth_local import get_authorized_tenant
from fastapi import APIRouter, Depends, HTTPException, Query
from src.api.auth_local import get_authorized_tenant
from fastapi import status as http_status
import uuid
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.ca_policies import (
    AcknowledgeAlertRequest,
    AlertSeverity,
    CAPolicyAlertListResponse,
    CAPolicyAlertModel,
    CAPolicyAlertResponse,
    CAPolicyChangeListResponse,
    CAPolicyChangeModel,
    CAPolicyChangeResponse,
    CAPolicyListResponse,
    CAPolicyModel,
    CAPolicyResponse,
    CAPolicyScanRequest,
    CAPolicyScanResponse,
    CAPolicySummary,
    ChangeType,
    PolicyState,
)
from src.services.ca_policies import CAPoliciesService

router = APIRouter()


# =============================================================================
# Pydantic Models for API Requests/Responses
# =============================================================================


class SetBaselineRequest(BaseModel):
    """Request model for setting security baseline."""

    require_mfa_for_admins: bool = Field(default=True, description="Require MFA for admin accounts")
    require_mfa_for_all_users: bool = Field(default=False, description="Require MFA for all users")
    block_legacy_auth: bool = Field(default=True, description="Block legacy authentication")
    require_compliant_or_hybrid_joined: bool = Field(
        default=False, description="Require compliant or hybrid joined devices"
    )
    block_high_risk_signins: bool = Field(default=True, description="Block high risk sign-ins")
    block_unknown_locations: bool = Field(
        default=False, description="Block sign-ins from unknown locations"
    )
    require_mfa_for_guests: bool = Field(
        default=True, description="Require MFA for guest/external users"
    )
    custom_requirements: dict = Field(
        default_factory=dict, description="Custom baseline requirements"
    )


class BaselineResponse(BaseModel):
    """Response model for baseline configuration."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    require_mfa_for_admins: bool
    require_mfa_for_all_users: bool
    block_legacy_auth: bool
    require_compliant_or_hybrid_joined: bool
    block_high_risk_signins: bool
    block_unknown_locations: bool
    require_mfa_for_guests: bool
    custom_requirements: dict
    created_at: str
    updated_at: str
    created_by: str | None


class AcknowledgeAlertResponse(BaseModel):
    """Response model for acknowledging an alert."""

    success: bool
    alert: CAPolicyAlertResponse | None
    message: str


# =============================================================================
# Dependencies
# =============================================================================


async def get_ca_policies_service(db: AsyncSession = Depends(get_db)) -> CAPoliciesService:
    """Dependency to get CA policies service."""
    return CAPoliciesService(db)


# =============================================================================
# Helper Functions
# =============================================================================


def _format_policy_response(policy: CAPolicyModel) -> CAPolicyResponse:
    """Format a policy model for response."""
    return CAPolicyResponse(
        id=str(policy.id),
        tenant_id=policy.tenant_id,
        policy_id=policy.policy_id,
        display_name=policy.display_name,
        description=policy.description,
        state=policy.state,
        grant_controls=policy.grant_controls,
        is_mfa_required=policy.is_mfa_required,
        applies_to_all_users=policy.applies_to_all_users,
        applies_to_all_apps=policy.applies_to_all_apps,
        is_baseline_policy=policy.is_baseline_policy,
        baseline_compliant=policy.baseline_compliant,
        security_score=policy.security_score,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        last_scan_at=policy.last_scan_at,
    )


def _format_change_response(change: CAPolicyChangeModel) -> CAPolicyChangeResponse:
    """Format a change model for response."""
    return CAPolicyChangeResponse(
        id=str(change.id),
        policy_id=str(change.policy_id),
        tenant_id=change.tenant_id,
        change_type=change.change_type,
        changed_by=change.changed_by,
        changed_by_email=change.changed_by_email,
        changes_summary=change.changes_summary,
        security_impact=change.security_impact,
        mfa_removed=change.mfa_removed,
        detected_at=change.detected_at,
    )


def _format_alert_response(alert: CAPolicyAlertModel) -> CAPolicyAlertResponse:
    """Format an alert model for response."""
    return CAPolicyAlertResponse(
        id=str(alert.id),
        policy_id=str(alert.policy_id),
        tenant_id=alert.tenant_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        is_acknowledged=alert.is_acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        created_at=alert.created_at,
    )


# =============================================================================
# CA Policies Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=CAPolicyListResponse,
    summary="List Conditional Access policies",
    description="List Conditional Access policies across all tenants with optional filtering.",
)
async def list_ca_policies(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    state: str | None = None,
    is_baseline_policy: bool | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> CAPolicyListResponse:
    """List Conditional Access policies with filtering.

    Args:
        tenant_id: Filter by tenant UUID
        state: Filter by state (enabled, disabled, reportOnly)
        is_baseline_policy: Filter by baseline status
        limit: Maximum results (1-1000)
        offset: Offset for pagination
        service: CA policies service

    Returns:
        Paginated list of CA policies
    """
    # Convert string state to enum
    state_enum = None
    if state:
        try:
            state_enum = PolicyState(state.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state: {state}. Must be one of: enabled, disabled, reportOnly",
            )

    result = await service.get_policies(
        tenant_id=tenant_id,
        state=state_enum,
        is_baseline_policy=is_baseline_policy,
        limit=limit,
        offset=offset,
    )

    return CAPolicyListResponse(
        items=[_format_policy_response(policy) for policy in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )



# =============================================================================
# Tenant-Specific Endpoints
# =============================================================================


@router.get(
    "/tenants/{tenant_id}/policies",
    response_model=CAPolicyListResponse,
    summary="Get tenant CA policies",
    description="Get all Conditional Access policies for a specific tenant.",
)
async def get_tenant_ca_policies(
    tenant_id: str,
    state: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> CAPolicyListResponse:
    """Get CA policies for a specific tenant.

    Args:
        tenant_id: Tenant UUID
        state: Filter by state
        limit: Maximum results
        offset: Offset for pagination
        service: CA policies service

    Returns:
        Paginated list of CA policies
    """
    # Convert string state to enum
    state_enum = None
    if state:
        try:
            state_enum = PolicyState(state.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid state: {state}"
            )

    result = await service.get_policies(
        tenant_id=tenant_id, state=state_enum, limit=limit, offset=offset
    )

    return CAPolicyListResponse(
        items=[_format_policy_response(policy) for policy in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get(
    "/tenants/{tenant_id}/disabled",
    response_model=list[CAPolicyResponse],
    summary="Get disabled policies",
    description="Get all disabled Conditional Access policies for a tenant.",
)
async def get_disabled_policies(
    tenant_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> list[CAPolicyResponse]:
    """Get disabled CA policies.

    Args:
        tenant_id: Tenant UUID
        limit: Maximum results
        service: CA policies service

    Returns:
        List of disabled policies
    """
    policies = await service.get_disabled_policies(tenant_id=tenant_id, limit=limit)
    return [_format_policy_response(policy) for policy in policies]


@router.get(
    "/tenants/{tenant_id}/mfa",
    response_model=list[CAPolicyResponse],
    summary="Get MFA policies",
    description="Get all Conditional Access policies that require MFA for a tenant.",
)
async def get_mfa_policies(
    tenant_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> list[CAPolicyResponse]:
    """Get MFA policies.

    Args:
        tenant_id: Tenant UUID
        limit: Maximum results
        service: CA policies service

    Returns:
        List of MFA policies
    """
    policies = await service.get_mfa_policies(tenant_id=tenant_id, limit=limit)
    return [_format_policy_response(policy) for policy in policies]


@router.get(
    "/tenants/{tenant_id}/summary",
    response_model=CAPolicySummary,
    summary="Get policies summary",
    description="Get summary of Conditional Access policies for a tenant.",
)
async def get_ca_policies_summary(
    tenant_id: str, service: CAPoliciesService = Depends(get_ca_policies_service)
) -> CAPolicySummary:
    """Get summary of CA policies.

    Args:
        tenant_id: Tenant UUID
        service: CA policies service

    Returns:
        Summary of CA policies
    """
    summary = await service.get_policies_summary(tenant_id=tenant_id)

    return CAPolicySummary(
        total_policies=summary["total_policies"],
        enabled=summary["enabled"],
        disabled=summary["disabled"],
        report_only=summary["report_only"],
        mfa_policies=summary["mfa_policies"],
        baseline_policies=summary["baseline_policies"],
        baseline_compliant=summary["baseline_compliant"],
        baseline_violations=summary["baseline_violations"],
        recent_changes=summary["recent_changes"],
        high_severity_alerts=summary["high_severity_alerts"],
        policies_covering_all_users=summary["policies_covering_all_users"],
        policies_covering_all_apps=summary["policies_covering_all_apps"],
    )


# =============================================================================
# Scan Endpoints
# =============================================================================


@router.post(
    "/scan",
    response_model=CAPolicyScanResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Trigger CA policy scan",
    description="Trigger a manual scan of Conditional Access policies for a tenant.",
)
async def scan_ca_policies(
    request: CAPolicyScanRequest, service: CAPoliciesService = Depends(get_ca_policies_service)
) -> CAPolicyScanResponse:
    """Trigger a manual scan of Conditional Access policies.

    Args:
        request: Scan request parameters
        service: CA policies service

    Returns:
        Scan results summary

    Raises:
        HTTPException: If tenant not found or scan fails
    """
    try:
        results = await service.scan_tenant_policies(
            tenant_id=request.tenant_id,
            trigger_alerts=request.trigger_alerts,
            compare_baseline=request.compare_baseline,
        )

        return CAPolicyScanResponse(
            success=True,
            tenant_id=request.tenant_id,
            policies_found=results["policies_found"],
            changes_detected=results["changes_detected"],
            alerts_triggered=results["alerts_triggered"],
            baseline_violations=results["baseline_violations"],
            message=f"Scan completed successfully. Found {results['policies_found']} policies, "
            f"{results['changes_detected']} changes detected, "
            f"{results['alerts_triggered']} alerts triggered.",
        )
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Scan failed: {str(e)}"
        )


# =============================================================================
# Change History Endpoints
# =============================================================================


@router.get(
    "/changes",
    response_model=CAPolicyChangeListResponse,
    summary="List policy changes",
    description="List Conditional Access policy changes across all tenants with optional filtering.",
)
async def list_policy_changes(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    change_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> CAPolicyChangeListResponse:
    """List CA policy changes with filtering.

    Args:
        tenant_id: Filter by tenant UUID
        change_type: Filter by change type (created, updated, deleted, enabled, disabled)
        limit: Maximum results
        offset: Offset for pagination
        service: CA policies service

    Returns:
        Paginated list of policy changes
    """
    # Convert string change_type to enum
    change_type_enum = None
    if change_type:
        try:
            change_type_enum = ChangeType(change_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid change type: {change_type}",
            )

    result = await service.get_policy_changes(
        tenant_id=tenant_id, change_type=change_type_enum, limit=limit, offset=offset
    )

    return CAPolicyChangeListResponse(
        items=[_format_change_response(change) for change in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


# =============================================================================
# Alert Endpoints
# =============================================================================


@router.get(
    "/alerts",
    response_model=CAPolicyAlertListResponse,
    summary="List CA policy alerts",
    description="List Conditional Access policy alerts with optional filtering.",
)
async def list_ca_policy_alerts(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    acknowledged: bool | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> CAPolicyAlertListResponse:
    """List CA policy alerts.

    Args:
        tenant_id: Filter by tenant
        acknowledged: Filter by acknowledgment status
        severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
        limit: Maximum results
        offset: Offset for pagination
        service: CA policies service

    Returns:
        Paginated list of alerts
    """
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity.upper())
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

    return CAPolicyAlertListResponse(
        items=[_format_alert_response(alert) for alert in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AcknowledgeAlertResponse,
    summary="Acknowledge alert",
    description="Acknowledge a Conditional Access policy alert.",
)
async def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeAlertRequest,
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> AcknowledgeAlertResponse:
    """Acknowledge a CA policy alert.

    Args:
        alert_id: Alert UUID
        request: Acknowledgment request
        service: CA policies service

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
        success=True, alert=_format_alert_response(alert), message="Alert acknowledged successfully"
    )


# =============================================================================
# Baseline Endpoints
# =============================================================================


@router.get(
    "/tenants/{tenant_id}/baseline",
    response_model=BaselineResponse,
    summary="Get baseline configuration",
    description="Get the security baseline configuration for a tenant.",
)
async def get_baseline_config(
    tenant_id: str, service: CAPoliciesService = Depends(get_ca_policies_service)
) -> BaselineResponse:
    """Get security baseline configuration.

    Args:
        tenant_id: Tenant UUID
        service: CA policies service

    Returns:
        Baseline configuration

    Raises:
        HTTPException: If baseline not found
    """
    baseline = await service._get_baseline_config(tenant_id)

    if not baseline:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Baseline configuration for tenant {tenant_id} not found",
        )

    return BaselineResponse(
        id=str(baseline.id),
        tenant_id=baseline.tenant_id,
        require_mfa_for_admins=baseline.require_mfa_for_admins,
        require_mfa_for_all_users=baseline.require_mfa_for_all_users,
        block_legacy_auth=baseline.block_legacy_auth,
        require_compliant_or_hybrid_joined=baseline.require_compliant_or_hybrid_joined,
        block_high_risk_signins=baseline.block_high_risk_signins,
        block_unknown_locations=baseline.block_unknown_locations,
        require_mfa_for_guests=baseline.require_mfa_for_guests,
        custom_requirements=baseline.custom_requirements,
        created_at=baseline.created_at.isoformat(),
        updated_at=baseline.updated_at.isoformat(),
        created_by=baseline.created_by,
    )


@router.post(
    "/tenants/{tenant_id}/baseline",
    response_model=BaselineResponse,
    summary="Set baseline configuration",
    description="Set or update the security baseline configuration for a tenant.",
)
async def set_baseline_config(
    tenant_id: str,
    request: SetBaselineRequest,
    created_by: str | None = None,
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> BaselineResponse:
    """Set or update security baseline configuration.

    Args:
        tenant_id: Tenant UUID
        request: Baseline configuration request
        created_by: User creating the baseline
        service: CA policies service

    Returns:
        Created or updated baseline configuration
    """
    config_data = request.model_dump()
    baseline = await service.set_baseline_config(
        tenant_id=tenant_id, config_data=config_data, created_by=created_by
    )

    return BaselineResponse(
        id=str(baseline.id),
        tenant_id=baseline.tenant_id,
        require_mfa_for_admins=baseline.require_mfa_for_admins,
        require_mfa_for_all_users=baseline.require_mfa_for_all_users,
        block_legacy_auth=baseline.block_legacy_auth,
        require_compliant_or_hybrid_joined=baseline.require_compliant_or_hybrid_joined,
        block_high_risk_signins=baseline.block_high_risk_signins,
        block_unknown_locations=baseline.block_unknown_locations,
        require_mfa_for_guests=baseline.require_mfa_for_guests,
        custom_requirements=baseline.custom_requirements,
        created_at=baseline.created_at.isoformat(),
        updated_at=baseline.updated_at.isoformat(),
        created_by=baseline.created_by,
    )


# =============================================================================
# ID-based Endpoints (Must be at the end to avoid routing conflicts)
# =============================================================================

@router.get(
    "/{policy_id}",
    response_model=CAPolicyResponse,
    summary="Get Conditional Access policy",
    description="Get a specific Conditional Access policy by ID.",
)
async def get_ca_policy(
    policy_id: str, service: CAPoliciesService = Depends(get_ca_policies_service)
) -> CAPolicyResponse:
    """Get a specific Conditional Access policy.

    Args:
        policy_id: Policy UUID
        service: CA policies service

    Returns:
        CA policy details

    Raises:
        HTTPException: If policy not found
    """
    policy = await service.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"CA policy with ID {policy_id} not found",
        )

    return _format_policy_response(policy)


@router.get(
    "/{policy_id}/changes",
    response_model=CAPolicyChangeListResponse,
    summary="Get policy change history",
    description="Get the change history for a specific Conditional Access policy.",
)
async def get_policy_changes(
    policy_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: CAPoliciesService = Depends(get_ca_policies_service),
) -> CAPolicyChangeListResponse:
    """Get change history for a CA policy.

    Args:
        policy_id: Policy UUID
        limit: Maximum results
        offset: Offset for pagination
        service: CA policies service

    Returns:
        Paginated list of policy changes
    """
    # Verify policy exists
    policy = await service.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"CA policy with ID {policy_id} not found",
        )

    result = await service.get_policy_changes(policy_id=policy.id, limit=limit, offset=offset)

    return CAPolicyChangeListResponse(
        items=[_format_change_response(change) for change in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )

