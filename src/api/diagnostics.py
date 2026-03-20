"""Diagnostics API endpoints for viewing data ingestion status."""

import uuid
from datetime import datetime, timedelta
from typing import Any

from src.api.auth_local import get_authorized_tenant
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.database import get_db

router = APIRouter()


class AuditLogRecord(BaseModel):
    """Audit log record for diagnostics."""

    id: uuid.UUID
    created_at: datetime
    o365_created_at: datetime | None
    log_type: str
    operation: str | None
    user_id: str | None
    user_email: str | None
    ip_address: str | None
    result_status: str | None
    processed: bool


class LoginAnalyticsRecord(BaseModel):
    """Login analytics record for diagnostics."""

    id: uuid.UUID
    created_at: datetime
    user_email: str | None
    ip_address: str | None
    is_success: bool
    failure_reason: str | None
    country: str | None
    risk_score: int
    anomaly_flags: list[str]


class DiagnosticsSummary(BaseModel):
    """Diagnostics summary."""

    audit_logs_count: int
    audit_logs_signin_count: int
    audit_logs_latest: datetime | None
    login_analytics_count: int
    login_analytics_success_count: int
    login_analytics_failed_count: int
    login_analytics_latest: datetime | None
    unprocessed_signin_count: int


@router.get("/summary", response_model=DiagnosticsSummary)
async def get_diagnostics_summary(
    tenant_id: str | None = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
) -> DiagnosticsSummary:
    # Determine if we should filter by tenant
    should_filter = tenant_id and tenant_id != "NONE"
    
    # Get audit_logs counts
    if should_filter:
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN log_type = 'signin' THEN 1 ELSE 0 END) as signin_count,
                MAX(created_at) as latest
            FROM audit_logs 
            WHERE tenant_id = :tenant_id
        """), {"tenant_id": tenant_id})
        row = result.fetchone()
        audit_logs_count = row[0] or 0
        audit_logs_signin_count = row[1] or 0
        audit_logs_latest = row[2]
    else:
        # If tenant_id is "NONE" or user has no tenants, return zeros
        # Otherwise if None (admin global), return all
        if tenant_id == "NONE":
             audit_logs_count, audit_logs_signin_count, audit_logs_latest = 0, 0, None
        else:
            result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(CASE WHEN log_type = 'signin' THEN 1 ELSE 0 END) as signin_count,
                    MAX(created_at) as latest
                FROM audit_logs
            """))
            row = result.fetchone()
            audit_logs_count = row[0] or 0
            audit_logs_signin_count = row[1] or 0
            audit_logs_latest = row[2]

    # Get login_analytics counts
    if should_filter:
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN is_success THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN NOT is_success THEN 1 ELSE 0 END) as failed_count,
                MAX(created_at) as latest
            FROM login_analytics 
            WHERE tenant_id = :tenant_id
        """), {"tenant_id": tenant_id})
        row = result.fetchone()
        login_analytics_count = row[0] or 0
        login_analytics_success_count = row[1] or 0
        login_analytics_failed_count = row[2] or 0
        login_analytics_latest = row[3]
    else:
        if tenant_id == "NONE":
            login_analytics_count, login_analytics_success_count, login_analytics_failed_count, login_analytics_latest = 0, 0, 0, None
        else:
            result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(CASE WHEN is_success THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN NOT is_success THEN 1 ELSE 0 END) as failed_count,
                    MAX(created_at) as latest
                FROM login_analytics
            """))
            row = result.fetchone()
            login_analytics_count = row[0] or 0
            login_analytics_success_count = row[1] or 0
            login_analytics_failed_count = row[2] or 0
            login_analytics_latest = row[3]

    # Get unprocessed signin count
    if should_filter:
        result = await db.execute(text("""
            SELECT COUNT(*) 
            FROM audit_logs 
            WHERE tenant_id = :tenant_id 
              AND log_type = 'signin' 
              AND processed = false
        """), {"tenant_id": tenant_id})
        unprocessed_signin_count = result.scalar() or 0
    else:
        if tenant_id == "NONE":
            unprocessed_signin_count = 0
        else:
            result = await db.execute(text("""
                SELECT COUNT(*) 
                FROM audit_logs 
                WHERE log_type = 'signin' 
                  AND processed = false
            """))
            unprocessed_signin_count = result.scalar() or 0

    return DiagnosticsSummary(
        audit_logs_count=audit_logs_count,
        audit_logs_signin_count=audit_logs_signin_count,
        audit_logs_latest=audit_logs_latest,
        login_analytics_count=login_analytics_count,
        login_analytics_success_count=login_analytics_success_count,
        login_analytics_failed_count=login_analytics_failed_count,
        login_analytics_latest=login_analytics_latest,
        unprocessed_signin_count=unprocessed_signin_count,
    )


@router.get("/audit-logs", response_model=list[AuditLogRecord])
async def get_recent_audit_logs(
    limit: int = Query(default=20, le=100),
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogRecord]:
    """Get recent audit logs."""
    
    if tenant_id and tenant_id != "NONE":
        result = await db.execute(text("""
            SELECT 
                id, created_at, o365_created_at, log_type,
                raw_data->>'Operation' as operation,
                raw_data->>'UserId' as user_id,
                raw_data->>'User' as user_email,
                raw_data->>'ClientIP' as ip_address,
                raw_data->>'ResultStatus' as result_status,
                processed
            FROM audit_logs 
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"tenant_id": tenant_id, "limit": limit})
    elif tenant_id == "NONE":
        return []
    else:
        # Admin global view
        result = await db.execute(text("""
            SELECT 
                id, created_at, o365_created_at, log_type,
                raw_data->>'Operation' as operation,
                raw_data->>'UserId' as user_id,
                raw_data->>'User' as user_email,
                raw_data->>'ClientIP' as ip_address,
                raw_data->>'ResultStatus' as result_status,
                processed
            FROM audit_logs 
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"limit": limit})
    
    rows = result.fetchall()
    return [
        AuditLogRecord(
            id=row[0],
            created_at=row[1],
            o365_created_at=row[2],
            log_type=row[3],
            operation=row[4],
            user_id=row[5],
            user_email=row[6],
            ip_address=row[7],
            result_status=row[8],
            processed=row[9],
        )
        for row in rows
    ]


@router.get("/login-analytics", response_model=list[LoginAnalyticsRecord])
async def get_recent_login_analytics(
    limit: int = Query(default=20, le=100),
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[LoginAnalyticsRecord]:
    """Get recent login analytics."""
    
    if tenant_id and tenant_id != "NONE":
        result = await db.execute(text("""
            SELECT 
                id, created_at, user_email, ip_address, 
                is_success, failure_reason, country,
                risk_score, anomaly_flags
            FROM login_analytics 
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"tenant_id": tenant_id, "limit": limit})
    elif tenant_id == "NONE":
        return []
    else:
        # Admin global view
        result = await db.execute(text("""
            SELECT 
                id, created_at, user_email, ip_address, 
                is_success, failure_reason, country,
                risk_score, anomaly_flags
            FROM login_analytics 
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"limit": limit})
    
    rows = result.fetchall()
    return [
        LoginAnalyticsRecord(
            id=row[0],
            created_at=row[1],
            user_email=row[2],
            ip_address=row[3],
            is_success=row[4],
            failure_reason=row[5],
            risk_score=row[7],
            anomaly_flags=row[8],
        )
        for row in rows
    ]