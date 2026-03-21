"""DLP and Insider Threat API."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.api.auth_local import get_current_user
from src.models.dlp import DLPEventModel

router = APIRouter()

@router.get(
    "/",
    dependencies=[Depends(get_current_user)],
)
async def get_dlp_events(
    tenant_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
):
    """Get recent DLP events."""
    query = select(DLPEventModel).order_by(desc(DLPEventModel.created_at))
    
    if tenant_id:
        query = query.where(DLPEventModel.tenant_id == tenant_id)
        
    result = await session.execute(query.limit(limit))
    events = result.scalars().all()
    
    return {"items": events, "total": len(events)}

@router.get(
    "/stats",
    dependencies=[Depends(get_current_user)],
)
async def get_dlp_stats(
    tenant_id: uuid.UUID | None = None,
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
):
    """Get statistics for DLP events."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    query = select(
        DLPEventModel.action_taken, 
        func.count(DLPEventModel.id).label('count')
    ).where(DLPEventModel.created_at >= start_date)
    
    if tenant_id:
        query = query.where(DLPEventModel.tenant_id == tenant_id)
        
    query = query.group_by(DLPEventModel.action_taken)
    
    result = await session.execute(query)
    stats = result.all()
    
    # Top violating users
    user_query = select(
        DLPEventModel.user_id,
        func.count(DLPEventModel.id).label('count')
    ).where(DLPEventModel.created_at >= start_date)
    
    if tenant_id:
        user_query = user_query.where(DLPEventModel.tenant_id == tenant_id)
        
    user_query = user_query.group_by(DLPEventModel.user_id).order_by(desc('count')).limit(10)
    user_result = await session.execute(user_query)
    top_users = user_result.all()
    
    return {
        "stats": [{"action": row.action_taken or "Unknown", "count": row.count} for row in stats],
        "top_users": [{"user_id": row.user_id, "count": row.count} for row in top_users]
    }
