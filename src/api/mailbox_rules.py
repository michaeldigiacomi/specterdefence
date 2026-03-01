"""Mailbox rule API endpoints for SpecterDefence."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.mailbox_rules import MailboxRuleService
from src.models.mailbox_rules import (
    MailboxRuleModel,
    MailboxRuleAlertModel,
    RuleType,
    RuleSeverity,
    RuleStatus,
)
from pydantic import BaseModel, Field

router = APIRouter()


# =============================================================================
# Pydantic Models for API Requests/Responses
# =============================================================================

class MailboxRuleResponse(BaseModel):
    """Response model for a mailbox rule."""
    id: str
    tenant_id: str
    user_email: str
    rule_id: str
    rule_name: str
    rule_type: str
    is_enabled: bool
    status: str
    severity: str
    forward_to: Optional[str]
    forward_to_external: bool
    external_domain: Optional[str]
    redirect_to: Optional[str]
    is_hidden_folder_redirect: bool
    has_suspicious_patterns: bool
    created_outside_business_hours: bool
    created_by_non_owner: bool
    created_by: Optional[str]
    detection_reasons: List[str]
    rule_created_at: Optional[str]
    rule_modified_at: Optional[str]
    last_scan_at: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class MailboxRuleListResponse(BaseModel):
    """Response model for listing mailbox rules."""
    items: List[MailboxRuleResponse]
    total: int
    limit: int
    offset: int


class MailboxRuleAlertResponse(BaseModel):
    """Response model for a mailbox rule alert."""
    id: str
    rule_id: str
    tenant_id: str
    user_email: str
    alert_type: str
    severity: str
    title: str
    description: str
    is_acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class MailboxRuleAlertListResponse(BaseModel):
    """Response model for listing mailbox rule alerts."""
    items: List[MailboxRuleAlertResponse]
    total: int
    limit: int
    offset: int


class ScanRequest(BaseModel):
    """Request model for triggering a mailbox rule scan."""
    tenant_id: Optional[str] = Field(
        None,
        description="Specific tenant to scan (if not provided, scans all tenants)"
    )
    trigger_alerts: bool = Field(
        True,
        description="Whether to trigger alerts for suspicious rules"
    )


class ScanResponse(BaseModel):
    """Response model for scan operation."""
    success: bool
    tenant_id: Optional[str]
    results: dict
    message: str


class AcknowledgeAlertRequest(BaseModel):
    """Request model for acknowledging an alert."""
    acknowledged_by: str = Field(..., min_length=1, description="User acknowledging the alert")


class AcknowledgeAlertResponse(BaseModel):
    """Response model for acknowledging an alert."""
    success: bool
    alert: Optional[MailboxRuleAlertResponse]
    message: str


class SuspiciousRulesSummary(BaseModel):
    """Summary of suspicious mailbox rules."""
    total_suspicious: int
    total_malicious: int
    by_severity: dict
    by_type: dict
    recent_alerts: int


# =============================================================================
# Dependencies
# =============================================================================

async def get_mailbox_rule_service(db: AsyncSession = Depends(get_db)) -> MailboxRuleService:
    """Dependency to get mailbox rule service."""
    return MailboxRuleService(db)


# =============================================================================
# Mailbox Rules Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=MailboxRuleListResponse,
    summary="List mailbox rules",
    description="List mailbox rules across all tenants with optional filtering."
)
async def list_mailbox_rules(
    tenant_id: Optional[str] = None,
    user_email: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    rule_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> MailboxRuleListResponse:
    """List mailbox rules with filtering.
    
    Args:
        tenant_id: Filter by tenant UUID
        user_email: Filter by user email
        status: Filter by status (active, suspicious, malicious, benign, disabled)
        severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
        rule_type: Filter by rule type
        limit: Maximum results (1-1000)
        offset: Offset for pagination
        service: Mailbox rule service
        
    Returns:
        Paginated list of mailbox rules
    """
    # Convert string enums
    status_enum = None
    severity_enum = None
    type_enum = None
    
    if status:
        try:
            status_enum = RuleStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    if severity:
        try:
            severity_enum = RuleSeverity(severity.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}"
            )
    
    if rule_type:
        try:
            type_enum = RuleType(rule_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rule type: {rule_type}"
            )
    
    result = await service.get_rules(
        tenant_id=tenant_id,
        user_email=user_email,
        status=status_enum,
        severity=severity_enum,
        rule_type=type_enum,
        limit=limit,
        offset=offset
    )
    
    return MailboxRuleListResponse(
        items=[
            MailboxRuleResponse(
                id=str(rule.id),
                tenant_id=rule.tenant_id,
                user_email=rule.user_email,
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_type=rule.rule_type.value,
                is_enabled=rule.is_enabled,
                status=rule.status.value,
                severity=rule.severity.value,
                forward_to=rule.forward_to,
                forward_to_external=rule.forward_to_external,
                external_domain=rule.external_domain,
                redirect_to=rule.redirect_to,
                is_hidden_folder_redirect=rule.is_hidden_folder_redirect,
                has_suspicious_patterns=rule.has_suspicious_patterns,
                created_outside_business_hours=rule.created_outside_business_hours,
                created_by_non_owner=rule.created_by_non_owner,
                created_by=rule.created_by,
                detection_reasons=rule.detection_reasons,
                rule_created_at=rule.rule_created_at.isoformat() if rule.rule_created_at else None,
                rule_modified_at=rule.rule_modified_at.isoformat() if rule.rule_modified_at else None,
                last_scan_at=rule.last_scan_at.isoformat(),
                created_at=rule.created_at.isoformat(),
                updated_at=rule.updated_at.isoformat(),
            )
            for rule in result["items"]
        ],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get(
    "/{rule_id}",
    response_model=MailboxRuleResponse,
    summary="Get mailbox rule",
    description="Get a specific mailbox rule by ID."
)
async def get_mailbox_rule(
    rule_id: str,
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> MailboxRuleResponse:
    """Get a specific mailbox rule.
    
    Args:
        rule_id: Rule UUID
        service: Mailbox rule service
        
    Returns:
        Mailbox rule details
        
    Raises:
        HTTPException: If rule not found
    """
    rule = await service.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Mailbox rule with ID {rule_id} not found"
        )
    
    return MailboxRuleResponse(
        id=str(rule.id),
        tenant_id=rule.tenant_id,
        user_email=rule.user_email,
        rule_id=rule.rule_id,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type.value,
        is_enabled=rule.is_enabled,
        status=rule.status.value,
        severity=rule.severity.value,
        forward_to=rule.forward_to,
        forward_to_external=rule.forward_to_external,
        external_domain=rule.external_domain,
        redirect_to=rule.redirect_to,
        is_hidden_folder_redirect=rule.is_hidden_folder_redirect,
        has_suspicious_patterns=rule.has_suspicious_patterns,
        created_outside_business_hours=rule.created_outside_business_hours,
        created_by_non_owner=rule.created_by_non_owner,
        created_by=rule.created_by,
        detection_reasons=rule.detection_reasons,
        rule_created_at=rule.rule_created_at.isoformat() if rule.rule_created_at else None,
        rule_modified_at=rule.rule_modified_at.isoformat() if rule.rule_modified_at else None,
        last_scan_at=rule.last_scan_at.isoformat(),
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.get(
    "/tenants/{tenant_id}/rules",
    response_model=MailboxRuleListResponse,
    summary="Get tenant mailbox rules",
    description="Get all mailbox rules for a specific tenant."
)
async def get_tenant_mailbox_rules(
    tenant_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> MailboxRuleListResponse:
    """Get mailbox rules for a specific tenant.
    
    Args:
        tenant_id: Tenant UUID
        status: Filter by status
        severity: Filter by severity
        limit: Maximum results
        offset: Offset for pagination
        service: Mailbox rule service
        
    Returns:
        Paginated list of mailbox rules
    """
    # Convert string enums
    status_enum = None
    severity_enum = None
    
    if status:
        try:
            status_enum = RuleStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    if severity:
        try:
            severity_enum = RuleSeverity(severity.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}"
            )
    
    result = await service.get_rules(
        tenant_id=tenant_id,
        status=status_enum,
        severity=severity_enum,
        limit=limit,
        offset=offset
    )
    
    return MailboxRuleListResponse(
        items=[
            MailboxRuleResponse(
                id=str(rule.id),
                tenant_id=rule.tenant_id,
                user_email=rule.user_email,
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_type=rule.rule_type.value,
                is_enabled=rule.is_enabled,
                status=rule.status.value,
                severity=rule.severity.value,
                forward_to=rule.forward_to,
                forward_to_external=rule.forward_to_external,
                external_domain=rule.external_domain,
                redirect_to=rule.redirect_to,
                is_hidden_folder_redirect=rule.is_hidden_folder_redirect,
                has_suspicious_patterns=rule.has_suspicious_patterns,
                created_outside_business_hours=rule.created_outside_business_hours,
                created_by_non_owner=rule.created_by_non_owner,
                created_by=rule.created_by,
                detection_reasons=rule.detection_reasons,
                rule_created_at=rule.rule_created_at.isoformat() if rule.rule_created_at else None,
                rule_modified_at=rule.rule_modified_at.isoformat() if rule.rule_modified_at else None,
                last_scan_at=rule.last_scan_at.isoformat(),
                created_at=rule.created_at.isoformat(),
                updated_at=rule.updated_at.isoformat(),
            )
            for rule in result["items"]
        ],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get(
    "/tenants/{tenant_id}/suspicious",
    response_model=List[MailboxRuleResponse],
    summary="Get suspicious rules",
    description="Get suspicious and malicious mailbox rules for a tenant."
)
async def get_suspicious_rules(
    tenant_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> List[MailboxRuleResponse]:
    """Get suspicious and malicious mailbox rules.
    
    Args:
        tenant_id: Tenant UUID
        limit: Maximum results
        service: Mailbox rule service
        
    Returns:
        List of suspicious/malicious rules
    """
    rules = await service.get_suspicious_rules(tenant_id=tenant_id, limit=limit)
    
    return [
        MailboxRuleResponse(
            id=str(rule.id),
            tenant_id=rule.tenant_id,
            user_email=rule.user_email,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            rule_type=rule.rule_type.value,
            is_enabled=rule.is_enabled,
            status=rule.status.value,
            severity=rule.severity.value,
            forward_to=rule.forward_to,
            forward_to_external=rule.forward_to_external,
            external_domain=rule.external_domain,
            redirect_to=rule.redirect_to,
            is_hidden_folder_redirect=rule.is_hidden_folder_redirect,
            has_suspicious_patterns=rule.has_suspicious_patterns,
            created_outside_business_hours=rule.created_outside_business_hours,
            created_by_non_owner=rule.created_by_non_owner,
            created_by=rule.created_by,
            detection_reasons=rule.detection_reasons,
            rule_created_at=rule.rule_created_at.isoformat() if rule.rule_created_at else None,
            rule_modified_at=rule.rule_modified_at.isoformat() if rule.rule_modified_at else None,
            last_scan_at=rule.last_scan_at.isoformat(),
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat(),
        )
        for rule in rules
    ]


# =============================================================================
# Scan Endpoints
# =============================================================================

@router.post(
    "/scan",
    response_model=ScanResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Trigger mailbox rule scan",
    description="Trigger a manual scan of mailbox rules for a tenant."
)
async def scan_mailbox_rules(
    request: ScanRequest,
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> ScanResponse:
    """Trigger a manual scan of mailbox rules.
    
    Args:
        request: Scan request parameters
        service: Mailbox rule service
        
    Returns:
        Scan results summary
        
    Raises:
        HTTPException: If tenant not found or scan fails
    """
    if not request.tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )
    
    try:
        results = await service.scan_tenant_mailbox_rules(
            tenant_id=request.tenant_id,
            trigger_alerts=request.trigger_alerts
        )
        
        return ScanResponse(
            success=True,
            tenant_id=request.tenant_id,
            results=results,
            message=f"Scan completed successfully. Found {results['total_rules']} rules, "
                    f"{results['suspicious_rules']} suspicious, {results['malicious_rules']} malicious."
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
# Alert Endpoints
# =============================================================================

@router.get(
    "/alerts",
    response_model=MailboxRuleAlertListResponse,
    summary="List mailbox rule alerts",
    description="List mailbox rule alerts with optional filtering."
)
async def list_mailbox_rule_alerts(
    tenant_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> MailboxRuleAlertListResponse:
    """List mailbox rule alerts.
    
    Args:
        tenant_id: Filter by tenant
        acknowledged: Filter by acknowledgment status
        severity: Filter by severity
        limit: Maximum results
        offset: Offset for pagination
        service: Mailbox rule service
        
    Returns:
        Paginated list of alerts
    """
    severity_enum = None
    if severity:
        try:
            severity_enum = RuleSeverity(severity.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}"
            )
    
    result = await service.get_alerts(
        tenant_id=tenant_id,
        acknowledged=acknowledged,
        severity=severity_enum,
        limit=limit,
        offset=offset
    )
    
    return MailboxRuleAlertListResponse(
        items=[
            MailboxRuleAlertResponse(
                id=str(alert.id),
                rule_id=str(alert.rule_id),
                tenant_id=alert.tenant_id,
                user_email=alert.user_email,
                alert_type=alert.alert_type,
                severity=alert.severity.value,
                title=alert.title,
                description=alert.description,
                is_acknowledged=alert.is_acknowledged,
                acknowledged_by=alert.acknowledged_by,
                acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
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
    description="Acknowledge a mailbox rule alert."
)
async def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeAlertRequest,
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> AcknowledgeAlertResponse:
    """Acknowledge a mailbox rule alert.
    
    Args:
        alert_id: Alert UUID
        request: Acknowledgment request
        service: Mailbox rule service
        
    Returns:
        Acknowledgment result
        
    Raises:
        HTTPException: If alert not found
    """
    alert = await service.acknowledge_alert(alert_id, request.acknowledged_by)
    
    if not alert:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )
    
    return AcknowledgeAlertResponse(
        success=True,
        alert=MailboxRuleAlertResponse(
            id=str(alert.id),
            rule_id=str(alert.rule_id),
            tenant_id=alert.tenant_id,
            user_email=alert.user_email,
            alert_type=alert.alert_type,
            severity=alert.severity.value,
            title=alert.title,
            description=alert.description,
            is_acknowledged=alert.is_acknowledged,
            acknowledged_by=alert.acknowledged_by,
            acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            created_at=alert.created_at.isoformat(),
        ),
        message="Alert acknowledged successfully"
    )


# =============================================================================
# Summary Endpoints
# =============================================================================

@router.get(
    "/tenants/{tenant_id}/summary",
    response_model=SuspiciousRulesSummary,
    summary="Get rules summary",
    description="Get summary of suspicious mailbox rules for a tenant."
)
async def get_rules_summary(
    tenant_id: str,
    service: MailboxRuleService = Depends(get_mailbox_rule_service)
) -> SuspiciousRulesSummary:
    """Get summary of suspicious mailbox rules.
    
    Args:
        tenant_id: Tenant UUID
        service: Mailbox rule service
        
    Returns:
        Summary of suspicious rules
    """
    from sqlalchemy import func
    
    # Get suspicious and malicious rules
    suspicious_rules = await service.get_suspicious_rules(
        tenant_id=tenant_id,
        limit=1000
    )
    
    # Calculate summary stats
    total_suspicious = sum(1 for r in suspicious_rules if r.status == RuleStatus.SUSPICIOUS)
    total_malicious = sum(1 for r in suspicious_rules if r.status == RuleStatus.MALICIOUS)
    
    by_severity = {}
    by_type = {}
    
    for rule in suspicious_rules:
        severity = rule.severity.value
        rule_type = rule.rule_type.value
        
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_type[rule_type] = by_type.get(rule_type, 0) + 1
    
    # Get recent alerts count
    alerts_result = await service.get_alerts(
        tenant_id=tenant_id,
        limit=1000
    )
    recent_alerts = alerts_result["total"]
    
    return SuspiciousRulesSummary(
        total_suspicious=total_suspicious,
        total_malicious=total_malicious,
        by_severity=by_severity,
        by_type=by_type,
        recent_alerts=recent_alerts
    )
