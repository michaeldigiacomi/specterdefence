"""Analytics API endpoints for login tracking and anomaly detection."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.anomalies import AnomalyType
from src.analytics.logins import LoginAnalyticsService
from src.database import get_db
from src.models.analytics import LoginAnalyticsModel

router = APIRouter()


# ============== Pydantic Models ==============

class LoginRecord(BaseModel):
    """Login record response model."""

    id: str
    user_email: str
    ip_address: str
    country: str | None = None
    country_code: str | None = None
    city: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    login_time: datetime
    is_success: bool
    failure_reason: str | None = None
    anomaly_flags: list[str] = []
    risk_score: int = 0

    class Config:
        from_attributes = True


class AnomalyDetail(BaseModel):
    """Anomaly detail in response."""

    type: str
    user: str
    locations: list[str] | None = None
    time_diff_minutes: float | None = None
    risk_score: int
    country: str | None = None
    previous_countries: list[str] | None = None
    details: dict[str, Any] | None = None


class LoginAnalyticsResponse(BaseModel):
    """Response model for login analytics query."""

    logins: list[LoginRecord]
    total: int
    page: int
    page_size: int
    filters_applied: dict[str, Any]
    anomalies: list[AnomalyDetail]


class UserLoginSummary(BaseModel):
    """User login summary response."""

    user_email: str
    tenant_id: str
    total_logins: int
    known_countries: list[str]
    known_ips_count: int
    last_login_time: str | None = None
    last_login_country: str | None = None
    failed_attempts_24h: int
    recent_anomalies: list[dict[str, Any]]


class ProcessAuditLogsRequest(BaseModel):
    """Request to process audit logs."""

    tenant_id: str
    limit: int = Field(default=100, ge=1, le=1000)


class ProcessAuditLogsResponse(BaseModel):
    """Response from processing audit logs."""

    processed_count: int
    tenant_id: str
    message: str


# ============== Dependencies ==============

async def get_analytics_service(
    db: AsyncSession = Depends(get_db)
) -> LoginAnalyticsService:
    """Dependency to get login analytics service."""
    return LoginAnalyticsService(db)


# ============== API Endpoints ==============

@router.get(
    "/logins",
    response_model=LoginAnalyticsResponse,
    summary="Query login analytics",
    description="Query login events with various filters and detect anomalies."
)
async def get_login_analytics(
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    user: str | None = Query(None, description="Filter by user email"),
    start_time: datetime | None = Query(None, description="Filter from this time (ISO 8601)"),
    end_time: datetime | None = Query(None, description="Filter until this time (ISO 8601)"),
    ip: str | None = Query(None, description="Filter by IP address"),
    country: str | None = Query(None, description="Filter by country name"),
    country_code: str | None = Query(None, description="Filter by country code (2-letter)"),
    status: str | None = Query(None, description="Filter by status: 'success' or 'failed'"),
    has_anomaly: bool | None = Query(None, description="Filter for logins with anomalies"),
    anomaly_type: str | None = Query(None, description="Filter by specific anomaly type"),
    min_risk_score: int | None = Query(None, ge=0, le=100, description="Minimum risk score"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    include_anomalies: bool = Query(True, description="Include detected anomalies in response"),
    service: LoginAnalyticsService = Depends(get_analytics_service)
) -> LoginAnalyticsResponse:
    """
    Query login analytics with filters.
    
    Returns login events with applied filters and detected anomalies.
    """
    # Convert status string to boolean
    is_success = None
    if status:
        status_lower = status.lower()
        if status_lower == "success":
            is_success = True
        elif status_lower == "failed":
            is_success = False
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Use 'success' or 'failed'"
            )

    # Calculate offset
    offset = (page - 1) * page_size

    # Query logins
    logins, total = await service.query_logins(
        tenant_id=tenant_id,
        user_email=user,
        start_time=start_time,
        end_time=end_time,
        ip_address=ip,
        country=country,
        country_code=country_code,
        is_success=is_success,
        has_anomaly=has_anomaly,
        anomaly_type=anomaly_type,
        min_risk_score=min_risk_score,
        limit=page_size,
        offset=offset
    )

    # Build filters applied dict
    filters_applied = {
        "tenant_id": tenant_id,
        "user": user,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "ip": ip,
        "country": country,
        "country_code": country_code,
        "status": status,
        "has_anomaly": has_anomaly,
        "anomaly_type": anomaly_type,
        "min_risk_score": min_risk_score
    }

    # Extract anomalies for response
    anomalies = []
    if include_anomalies:
        # Group anomalies by type for summary
        anomaly_map: dict[str, list[LoginAnalyticsModel]] = {}
        for login in logins:
            for flag in login.anomaly_flags:
                if flag not in anomaly_map:
                    anomaly_map[flag] = []
                anomaly_map[flag].append(login)

        # Create anomaly details
        for anomaly_type_str, login_list in anomaly_map.items():
            for login in login_list[:5]:  # Limit to 5 per type
                anomaly_detail = await _create_anomaly_detail(login, anomaly_type_str, service)
                if anomaly_detail:
                    anomalies.append(anomaly_detail)

    return LoginAnalyticsResponse(
        logins=[LoginRecord.model_validate(login) for login in logins],
        total=total,
        page=page,
        page_size=page_size,
        filters_applied=filters_applied,
        anomalies=anomalies
    )


async def _create_anomaly_detail(
    login: LoginAnalyticsModel,
    anomaly_type: str,
    service: LoginAnalyticsService
) -> AnomalyDetail | None:
    """Create anomaly detail from login record."""
    if anomaly_type == AnomalyType.IMPOSSIBLE_TRAVEL.value:
        # Get previous login for details
        prev_login = await service._get_previous_login(login.user_email, login.tenant_id)
        if prev_login and prev_login.latitude and prev_login.longitude:
            locations = []
            if prev_login.city and prev_login.country:
                locations.append(f"{prev_login.city}, {prev_login.country}")
            elif prev_login.country:
                locations.append(prev_login.country)

            if login.city and login.country:
                locations.append(f"{login.city}, {login.country}")
            elif login.country:
                locations.append(login.country)

            time_diff = (login.login_time - prev_login.login_time).total_seconds() / 60

            return AnomalyDetail(
                type="impossible_travel",
                user=login.user_email,
                locations=locations if len(locations) == 2 else None,
                time_diff_minutes=round(time_diff, 2) if time_diff > 0 else None,
                risk_score=login.risk_score,
                details={
                    "previous_ip": prev_login.ip_address,
                    "current_ip": login.ip_address,
                    "previous_country": prev_login.country_code,
                    "current_country": login.country_code
                }
            )

    elif anomaly_type == AnomalyType.NEW_COUNTRY.value:
        # Get user history for previous countries
        user_history = await service._get_or_create_user_history(
            login.user_email, login.tenant_id
        )

        # Previous countries (excluding current)
        prev_countries = [
            c for c in user_history.known_countries
            if c != login.country_code
        ]

        return AnomalyDetail(
            type="new_country",
            user=login.user_email,
            country=login.country,
            previous_countries=prev_countries[-5:] if prev_countries else [],  # Last 5
            risk_score=login.risk_score,
            details={
                "country_code": login.country_code,
                "city": login.city
            }
        )

    elif anomaly_type == AnomalyType.FAILED_LOGIN.value:
        return AnomalyDetail(
            type="failed_login",
            user=login.user_email,
            risk_score=login.risk_score,
            details={
                "failure_reason": login.failure_reason,
                "ip_address": login.ip_address,
                "country": login.country
            }
        )

    elif anomaly_type == AnomalyType.MULTIPLE_FAILURES.value:
        user_history = await service._get_or_create_user_history(
            login.user_email, login.tenant_id
        )

        return AnomalyDetail(
            type="multiple_failures",
            user=login.user_email,
            risk_score=login.risk_score,
            details={
                "failed_attempts_24h": user_history.failed_attempts_24h,
                "failure_reason": login.failure_reason,
                "ip_address": login.ip_address
            }
        )

    # Generic anomaly
    return AnomalyDetail(
        type=anomaly_type,
        user=login.user_email,
        risk_score=login.risk_score,
        details={
            "ip_address": login.ip_address,
            "country": login.country
        }
    )


@router.get(
    "/logins/{user_email}/summary",
    response_model=UserLoginSummary,
    summary="Get user login summary",
    description="Get summary statistics for a user's login activity."
)
async def get_user_summary(
    user_email: str,
    tenant_id: str,
    service: LoginAnalyticsService = Depends(get_analytics_service)
) -> UserLoginSummary:
    """Get login summary for a specific user."""
    summary = await service.get_user_login_summary(user_email, tenant_id)
    return UserLoginSummary(**summary)


@router.post(
    "/logins/process-audit-logs",
    response_model=ProcessAuditLogsResponse,
    summary="Process audit logs",
    description="Process unprocessed signin audit logs and create login analytics."
)
async def process_audit_logs(
    request: ProcessAuditLogsRequest,
    service: LoginAnalyticsService = Depends(get_analytics_service)
) -> ProcessAuditLogsResponse:
    """
    Process unprocessed signin audit logs.
    
    This converts Office 365 signin audit logs into login analytics records.
    """
    try:
        processed_count = await service.process_audit_log_signins(
            tenant_id=request.tenant_id,
            limit=request.limit
        )

        return ProcessAuditLogsResponse(
            processed_count=processed_count,
            tenant_id=request.tenant_id,
            message=f"Successfully processed {processed_count} audit log entries"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audit logs: {str(e)}"
        )


@router.get(
    "/anomalies/recent",
    response_model=list[AnomalyDetail],
    summary="Get recent anomalies",
    description="Get recent login anomalies across all users or filtered by tenant."
)
async def get_recent_anomalies(
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    hours: int = Query(24, ge=1, le=168, description="Look back period in hours"),
    min_risk_score: int = Query(50, ge=0, le=100, description="Minimum risk score"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    service: LoginAnalyticsService = Depends(get_analytics_service)
) -> list[AnomalyDetail]:
    """Get recent anomalies detected in login activity."""
    since = datetime.utcnow() - timedelta(hours=hours)

    logins, _ = await service.query_logins(
        tenant_id=tenant_id,
        start_time=since,
        has_anomaly=True,
        min_risk_score=min_risk_score,
        limit=limit,
        offset=0
    )

    anomalies = []
    for login in logins:
        for flag in login.anomaly_flags:
            detail = await _create_anomaly_detail(login, flag, service)
            if detail:
                anomalies.append(detail)

    return anomalies
