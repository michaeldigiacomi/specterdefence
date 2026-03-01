"""MFA Enrollment Tracking API endpoints for SpecterDefence."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.mfa_report import MFAReportService
from src.models.mfa_report import (
    MFAUserModel,
    MFAEnrollmentHistoryModel,
    MFAComplianceAlertModel,
    MFAStrengthLevel,
    ComplianceStatus,
    MFAUserResponse,
    MFAUserListResponse,
    MFAEnrollmentSummary,
    MFAEnrollmentTrendsResponse,
    MFAMethodsDistributionResponse,
    MFAStrengthDistributionResponse,
    MFAComplianceReport,
    MFAScanRequest,
    MFAScanResponse,
    MFAExemptionRequest,
    MFAExemptionResponse,
    MFAResolveAlertRequest,
    MFAResolveAlertResponse,
)
from pydantic import BaseModel, Field

router = APIRouter()


# =============================================================================
# Pydantic Models for API Requests/Responses
# =============================================================================

class UsersWithoutMFAResponse(BaseModel):
    """Response model for users without MFA."""
    items: List[MFAUserResponse]
    total: int
    limit: int
    offset: int
    critical_count: int  # Admins without MFA


class AdminsWithoutMFAResponse(BaseModel):
    """Response model for admins without MFA."""
    items: List[MFAUserResponse]
    total: int
    message: str


# =============================================================================
# Dependencies
# =============================================================================

async def get_mfa_report_service(db: AsyncSession = Depends(get_db)) -> MFAReportService:
    """Dependency to get MFA report service."""
    return MFAReportService(db)


# =============================================================================
# Helper Functions
# =============================================================================

def _format_user_response(user: MFAUserModel) -> MFAUserResponse:
    """Format a user model for response."""
    return MFAUserResponse(
        id=str(user.id),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        user_principal_name=user.user_principal_name,
        display_name=user.display_name,
        is_mfa_registered=user.is_mfa_registered,
        mfa_methods=user.mfa_methods,
        primary_mfa_method=user.primary_mfa_method,
        mfa_strength=user.mfa_strength,
        is_admin=user.is_admin,
        admin_roles=user.admin_roles,
        compliance_status=user.compliance_status,
        compliance_exempt=user.compliance_exempt,
        exemption_reason=user.exemption_reason,
        first_mfa_registration=user.first_mfa_registration,
        last_mfa_update=user.last_mfa_update,
        account_enabled=user.account_enabled,
        user_type=user.user_type,
        created_at=user.created_at,
        updated_at=user.updated_at,
        needs_attention=user.needs_attention,
    )


# =============================================================================
# MFA Report Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=MFAEnrollmentSummary,
    summary="Get MFA enrollment summary",
    description="Get a summary of MFA enrollment for a tenant."
)
async def get_mfa_summary(
    tenant_id: str = Query(..., description="Tenant UUID"),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAEnrollmentSummary:
    """Get MFA enrollment summary for a tenant.
    
    Args:
        tenant_id: Tenant UUID
        service: MFA report service
        
    Returns:
        MFA enrollment summary
    """
    summary = await service.get_enrollment_summary(tenant_id=tenant_id)
    
    return MFAEnrollmentSummary(
        tenant_id=summary["tenant_id"],
        snapshot_date=summary["snapshot_date"],
        total_users=summary["total_users"],
        mfa_registered_users=summary["mfa_registered_users"],
        non_compliant_users=summary["non_compliant_users"],
        total_admins=summary["total_admins"],
        admins_with_mfa=summary["admins_with_mfa"],
        admins_without_mfa=summary["admins_without_mfa"],
        fido2_users=summary["fido2_users"],
        authenticator_app_users=summary["authenticator_app_users"],
        sms_users=summary["sms_users"],
        strong_mfa_users=summary["strong_mfa_users"],
        moderate_mfa_users=summary["moderate_mfa_users"],
        weak_mfa_users=summary["weak_mfa_users"],
        exempt_users=summary["exempt_users"],
        mfa_coverage_percentage=summary["mfa_coverage_percentage"],
        admin_mfa_coverage_percentage=summary["admin_mfa_coverage_percentage"],
        compliance_rate=summary["compliance_rate"],
        meets_admin_requirement=summary["meets_admin_requirement"],
        meets_user_target=summary["meets_user_target"],
    )


@router.get(
    "/users",
    response_model=MFAUserListResponse,
    summary="List MFA users",
    description="List users with their MFA enrollment status."
)
async def list_mfa_users(
    tenant_id: str = Query(..., description="Tenant UUID"),
    is_mfa_registered: Optional[bool] = Query(None, description="Filter by MFA registration"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    mfa_strength: Optional[str] = Query(None, description="Filter by MFA strength (strong, moderate, weak, none)"),
    needs_attention: Optional[bool] = Query(None, description="Filter by attention required"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAUserListResponse:
    """List MFA users with filtering.
    
    Args:
        tenant_id: Tenant UUID
        is_mfa_registered: Filter by MFA registration status
        is_admin: Filter by admin status
        mfa_strength: Filter by MFA strength level
        needs_attention: Filter by attention required
        limit: Maximum results
        offset: Pagination offset
        service: MFA report service
        
    Returns:
        Paginated list of MFA users
    """
    # Convert string strength to enum
    strength_enum = None
    if mfa_strength:
        try:
            strength_enum = MFAStrengthLevel(mfa_strength.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MFA strength: {mfa_strength}. Must be one of: strong, moderate, weak, none"
            )
    
    result = await service.get_users(
        tenant_id=tenant_id,
        is_mfa_registered=is_mfa_registered,
        is_admin=is_admin,
        mfa_strength=strength_enum,
        needs_attention=needs_attention,
        limit=limit,
        offset=offset,
    )
    
    return MFAUserListResponse(
        items=[_format_user_response(user) for user in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get(
    "/users-without-mfa",
    response_model=UsersWithoutMFAResponse,
    summary="Get users without MFA",
    description="Get all users without MFA registration (non-compliant)."
)
async def get_users_without_mfa(
    tenant_id: str = Query(..., description="Tenant UUID"),
    include_exempt: bool = Query(default=False, description="Include exempt users"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> UsersWithoutMFAResponse:
    """Get users without MFA registration.
    
    Args:
        tenant_id: Tenant UUID
        include_exempt: Whether to include exempt users
        limit: Maximum results
        offset: Pagination offset
        service: MFA report service
        
    Returns:
        List of users without MFA
    """
    result = await service.get_users_without_mfa(
        tenant_id=tenant_id,
        include_exempt=include_exempt,
        limit=limit,
        offset=offset,
    )
    
    # Count critical findings (admins without MFA)
    critical_count = sum(1 for user in result["items"] if user.is_admin)
    
    return UsersWithoutMFAResponse(
        items=[_format_user_response(user) for user in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
        critical_count=critical_count,
    )


@router.get(
    "/admins-without-mfa",
    response_model=AdminsWithoutMFAResponse,
    summary="Get admins without MFA (CRITICAL)",
    description="Get admin users without MFA registration. This is a critical security finding!"
)
async def get_admins_without_mfa(
    tenant_id: str = Query(..., description="Tenant UUID"),
    limit: int = Query(default=100, ge=1, le=500),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> AdminsWithoutMFAResponse:
    """Get admin users without MFA (critical findings).
    
    Args:
        tenant_id: Tenant UUID
        limit: Maximum results
        service: MFA report service
        
    Returns:
        List of admin users without MFA
    """
    admins = await service.get_admins_without_mfa(
        tenant_id=tenant_id,
        limit=limit,
    )
    
    message = (
        f"CRITICAL: {len(admins)} admin(s) without MFA detected! "
        "Immediate action required."
        if admins else
        "All admins have MFA registered."
    )
    
    return AdminsWithoutMFAResponse(
        items=[_format_user_response(admin) for admin in admins],
        total=len(admins),
        message=message,
    )


@router.get(
    "/trends",
    response_model=MFAEnrollmentTrendsResponse,
    summary="Get MFA enrollment trends",
    description="Get MFA enrollment trends over time."
)
async def get_mfa_trends(
    tenant_id: str = Query(..., description="Tenant UUID"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAEnrollmentTrendsResponse:
    """Get MFA enrollment trends over time.
    
    Args:
        tenant_id: Tenant UUID
        days: Number of days to look back
        service: MFA report service
        
    Returns:
        MFA enrollment trends
    """
    trends = await service.get_enrollment_trends(
        tenant_id=tenant_id,
        days=days,
    )
    
    return MFAEnrollmentTrendsResponse(
        tenant_id=trends["tenant_id"],
        trends=trends["trends"],
        period_days=trends["period_days"],
    )


@router.get(
    "/method-distribution",
    response_model=MFAMethodsDistributionResponse,
    summary="Get MFA method distribution",
    description="Get the distribution of MFA methods used by users."
)
async def get_method_distribution(
    tenant_id: str = Query(..., description="Tenant UUID"),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAMethodsDistributionResponse:
    """Get distribution of MFA methods.
    
    Args:
        tenant_id: Tenant UUID
        service: MFA report service
        
    Returns:
        MFA method distribution
    """
    distribution = await service.get_mfa_method_distribution(tenant_id=tenant_id)
    
    return MFAMethodsDistributionResponse(
        tenant_id=distribution["tenant_id"],
        total_mfa_users=distribution["total_mfa_users"],
        distribution=distribution["distribution"],
    )


@router.get(
    "/strength-distribution",
    response_model=MFAStrengthDistributionResponse,
    summary="Get MFA strength distribution",
    description="Get the distribution of MFA strength levels."
)
async def get_strength_distribution(
    tenant_id: str = Query(..., description="Tenant UUID"),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAStrengthDistributionResponse:
    """Get distribution of MFA strength levels.
    
    Args:
        tenant_id: Tenant UUID
        service: MFA report service
        
    Returns:
        MFA strength distribution
    """
    distribution = await service.get_mfa_strength_distribution(tenant_id=tenant_id)
    
    return MFAStrengthDistributionResponse(
        tenant_id=distribution["tenant_id"],
        distribution=distribution["distribution"],
        strong_mfa_percentage=distribution["strong_mfa_percentage"],
        moderate_mfa_percentage=distribution["moderate_mfa_percentage"],
        weak_mfa_percentage=distribution["weak_mfa_percentage"],
        no_mfa_percentage=distribution["no_mfa_percentage"],
    )


@router.get(
    "/compliance-report",
    response_model=MFAComplianceReport,
    summary="Get full compliance report",
    description="Get a comprehensive MFA compliance report including recommendations."
)
async def get_compliance_report(
    tenant_id: str = Query(..., description="Tenant UUID"),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAComplianceReport:
    """Get comprehensive MFA compliance report.
    
    Args:
        tenant_id: Tenant UUID
        service: MFA report service
        
    Returns:
        MFA compliance report
    """
    # Get summary
    summary = await service.get_enrollment_summary(tenant_id=tenant_id)
    
    # Get non-compliant users
    non_compliant_result = await service.get_users_without_mfa(
        tenant_id=tenant_id,
        include_exempt=False,
        limit=100,
    )
    
    # Get admins without MFA
    admins_without_mfa = await service.get_admins_without_mfa(
        tenant_id=tenant_id,
        limit=100,
    )
    
    # Get users with weak MFA
    weak_mfa_result = await service.get_users(
        tenant_id=tenant_id,
        mfa_strength=MFAStrengthLevel.WEAK,
        limit=100,
    )
    
    # Generate recommendations
    recommendations = []
    
    if admins_without_mfa:
        recommendations.append(
            f"CRITICAL: {len(admins_without_mfa)} admin(s) without MFA. "
            "Immediate enrollment required."
        )
    
    if summary["mfa_coverage_percentage"] < 95:
        recommendations.append(
            f"MFA coverage at {summary['mfa_coverage_percentage']}%. "
            f"Target: 95%+. {summary['non_compliant_users']} users need to enroll."
        )
    
    if summary["weak_mfa_users"] > 0:
        recommendations.append(
            f"{summary['weak_mfa_users']} user(s) using weak MFA (SMS/Voice). "
            "Recommend upgrading to Authenticator app or FIDO2."
        )
    
    if summary["strong_mfa_users"] == 0 and summary["mfa_registered_users"] > 0:
        recommendations.append(
            "No users with strong MFA (FIDO2/Hardware tokens). "
            "Consider promoting FIDO2 adoption for high-security accounts."
        )
    
    if not recommendations:
        recommendations.append(
            "Excellent MFA posture! Maintain current compliance levels."
        )
    
    return MFAComplianceReport(
        tenant_id=tenant_id,
        generated_at=datetime.utcnow(),
        summary=MFAEnrollmentSummary(
            tenant_id=summary["tenant_id"],
            snapshot_date=summary["snapshot_date"],
            total_users=summary["total_users"],
            mfa_registered_users=summary["mfa_registered_users"],
            non_compliant_users=summary["non_compliant_users"],
            total_admins=summary["total_admins"],
            admins_with_mfa=summary["admins_with_mfa"],
            admins_without_mfa=summary["admins_without_mfa"],
            fido2_users=summary["fido2_users"],
            authenticator_app_users=summary["authenticator_app_users"],
            sms_users=summary["sms_users"],
            strong_mfa_users=summary["strong_mfa_users"],
            moderate_mfa_users=summary["moderate_mfa_users"],
            weak_mfa_users=summary["weak_mfa_users"],
            exempt_users=summary["exempt_users"],
            mfa_coverage_percentage=summary["mfa_coverage_percentage"],
            admin_mfa_coverage_percentage=summary["admin_mfa_coverage_percentage"],
            compliance_rate=summary["compliance_rate"],
            meets_admin_requirement=summary["meets_admin_requirement"],
            meets_user_target=summary["meets_user_target"],
        ),
        non_compliant_users=[_format_user_response(u) for u in non_compliant_result["items"]],
        admins_without_mfa=[_format_user_response(u) for u in admins_without_mfa],
        users_with_weak_mfa=[_format_user_response(u) for u in weak_mfa_result["items"]],
        recommendations=recommendations,
    )


# =============================================================================
# Scan Endpoints
# =============================================================================

@router.post(
    "/scan",
    response_model=MFAScanResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Trigger MFA scan",
    description="Trigger a manual scan of MFA enrollment for a tenant."
)
async def scan_mfa(
    request: MFAScanRequest,
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAScanResponse:
    """Trigger a manual MFA scan.
    
    Args:
        request: Scan request parameters
        service: MFA report service
        
    Returns:
        Scan results summary
    """
    try:
        results = await service.scan_tenant_mfa(
            tenant_id=request.tenant_id,
            full_scan=request.full_scan,
            check_compliance=request.check_compliance,
        )
        
        return MFAScanResponse(
            success=results["success"],
            tenant_id=request.tenant_id,
            users_scanned=results["users_scanned"],
            new_mfa_registrations=results["new_mfa_registrations"],
            compliance_violations=results["compliance_violations"],
            critical_findings=results["critical_findings"],
            message=results["message"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.post(
    "/users/{user_id}/exemption",
    response_model=MFAExemptionResponse,
    summary="Set MFA exemption",
    description="Grant or revoke MFA exemption for a user."
)
async def set_user_exemption(
    user_id: str,
    request: MFAExemptionRequest,
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAExemptionResponse:
    """Set MFA exemption for a user.
    
    Args:
        user_id: User UUID
        request: Exemption request
        service: MFA report service
        
    Returns:
        Exemption result
    """
    # For revocation, use empty reason
    exempt = bool(request.exemption_reason)
    
    user = await service.set_user_exemption(
        user_id=user_id,
        exempt=exempt,
        reason=request.exemption_reason,
        expires_at=request.expires_at,
    )
    
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return MFAExemptionResponse(
        success=True,
        user_id=user_id,
        exemption_granted=user.compliance_exempt,
        exemption_reason=user.exemption_reason,
        expires_at=user.exemption_expires_at,
        message=f"MFA exemption {'granted' if user.compliance_exempt else 'revoked'} successfully",
    )


# =============================================================================
# Alert Endpoints
# =============================================================================

@router.get(
    "/alerts",
    response_model=Dict[str, Any],
    summary="List MFA compliance alerts",
    description="List MFA compliance alerts with optional filtering."
)
async def list_mfa_alerts(
    tenant_id: Optional[str] = Query(None, description="Tenant UUID"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low)"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MFAReportService = Depends(get_mfa_report_service)
) -> Dict[str, Any]:
    """List MFA compliance alerts.
    
    Args:
        tenant_id: Filter by tenant
        resolved: Filter by resolution status
        severity: Filter by severity
        limit: Maximum results
        offset: Pagination offset
        service: MFA report service
        
    Returns:
        Paginated list of alerts
    """
    alerts = await service.get_alerts(
        tenant_id=tenant_id,
        resolved=resolved,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    
    return {
        "items": [
            {
                "id": str(alert.id),
                "user_id": str(alert.user_id) if alert.user_id else None,
                "tenant_id": alert.tenant_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "is_resolved": alert.is_resolved,
                "resolved_at": alert.resolved_at,
                "resolved_by": alert.resolved_by,
                "created_at": alert.created_at,
            }
            for alert in alerts["items"]
        ],
        "total": alerts["total"],
        "limit": alerts["limit"],
        "offset": alerts["offset"],
    }


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=MFAResolveAlertResponse,
    summary="Resolve MFA alert",
    description="Resolve an MFA compliance alert."
)
async def resolve_alert(
    alert_id: str,
    request: MFAResolveAlertRequest,
    service: MFAReportService = Depends(get_mfa_report_service)
) -> MFAResolveAlertResponse:
    """Resolve an MFA compliance alert.
    
    Args:
        alert_id: Alert UUID
        request: Resolution request
        service: MFA report service
        
    Returns:
        Resolution result
    """
    alert = await service.resolve_alert(
        alert_id=alert_id,
        resolved_by=request.resolved_by,
    )
    
    if not alert:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )
    
    return MFAResolveAlertResponse(
        success=True,
        alert_id=alert_id,
        is_resolved=alert.is_resolved,
        resolved_at=alert.resolved_at,
        message="Alert resolved successfully",
    )
