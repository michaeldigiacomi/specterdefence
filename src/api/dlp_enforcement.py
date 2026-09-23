"""
DLP Enforcement API endpoints for SpecterDefence.

This module provides API endpoints to manage and trigger DLP enforcement actions.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.api.auth_local import get_current_user
from src.analytics.dlp_enforcement import DLPEnforcementService

router = APIRouter(prefix="/dlp/enforcement", tags=["dlp-enforcement"])

@router.post(
    "/analyze",
    dependencies=[Depends(get_current_user)],
)
async def analyze_dlp_violations(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Analyze DLP violations and determine enforcement actions."""
    try:
        enforcement_service = DLPEnforcementService(session)
        analysis = await enforcement_service.analyze_dlp_violations(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "analysis": analysis,
            "timestamp": datetime.now(timezone.utc)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze DLP violations: {str(e)}")

@router.post(
    "/enforce",
    dependencies=[Depends(get_current_user)],
)
async def enforce_dlp_policies(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Enforce DLP policies based on detected violations."""
    try:
        enforcement_service = DLPEnforcementService(session)
        
        # First analyze the violations
        analysis = await enforcement_service.analyze_dlp_violations(tenant_id)
        
        # Then enforce policies
        enforcement_results = await enforcement_service.enforce_dlp_policies(tenant_id, analysis)
        
        return {
            "tenant_id": tenant_id,
            "analysis": analysis,
            "enforcement_results": enforcement_results,
            "timestamp": datetime.now(timezone.utc)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enforce DLP policies: {str(e)}")

@router.get(
    "/stats",
    dependencies=[Depends(get_current_user)],
)
async def get_dlp_enforcement_stats(
    tenant_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
):
    """Get statistics for DLP enforcement activities."""
    try:
        # This would provide information on enforcement effectiveness and patterns
        return {
            "stats": {
                "total_analyses": 0,
                "successful_enforcements": 0,
                "failed_enforcements": 0,
                "average_risk_score": 0.0
            },
            "timestamp": datetime.now(timezone.utc)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get DLP enforcement stats: {str(e)}")