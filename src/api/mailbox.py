"""Mailbox Security API."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.mailbox import MailboxRuleEventModel, MailboxAccessModel
from src.api.auth_local import get_current_user

router = APIRouter()

@router.get(
    "/events",
    dependencies=[Depends(get_current_user)],
)
async def get_mailbox_events(
    tenant_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
):
    """Get recent mailbox rule change events."""
    query = select(MailboxRuleEventModel).order_by(desc(MailboxRuleEventModel.created_at))
    if tenant_id:
        query = query.where(MailboxRuleEventModel.tenant_id == tenant_id)
    result = await session.execute(query.limit(limit))
    return {"items": result.scalars().all()}

@router.get(
    "/access",
    dependencies=[Depends(get_current_user)],
)
async def get_mailbox_access(
    tenant_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
):
    """Get recent non-owner mailbox access events."""
    query = select(MailboxAccessModel).order_by(desc(MailboxAccessModel.created_at))
    if tenant_id:
        query = query.where(MailboxAccessModel.tenant_id == tenant_id)
    result = await session.execute(query.limit(limit))
    return {"items": result.scalars().all()}

@router.get(
    "/stats",
    dependencies=[Depends(get_current_user)],
)
async def get_mailbox_security_stats(
    tenant_id: uuid.UUID | None = None,
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
):
    """Get statistics for mailbox security."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Non-owner access count
    access_query = select(func.count(MailboxAccessModel.id)).where(MailboxAccessModel.created_at >= start_date)
    if tenant_id:
        access_query = access_query.where(MailboxAccessModel.tenant_id == tenant_id)
    
    # Forwarding rules count
    rules_query = select(func.count(MailboxRuleEventModel.id)).where(
        and_(
            MailboxRuleEventModel.created_at >= start_date,
            MailboxRuleEventModel.is_external.is_(True)
        )
    )
    if tenant_id:
        rules_query = rules_query.where(MailboxRuleEventModel.tenant_id == tenant_id)
    
    access_res = await session.execute(access_query)
    rules_res = await session.execute(rules_query)
    
    return {
        "non_owner_access_count": access_res.scalar(),
        "external_forward_rules_count": rules_res.scalar(),
    }
