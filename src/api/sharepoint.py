"""API endpoints for SharePoint diagnostics and analytics."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth_local import get_authorized_tenant
from src.database import get_db
from src.analytics.sharepoint import SharePointAnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_sharepoint_metrics(
    tenant_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    auth_tenant: str = Depends(get_authorized_tenant),
) -> dict[str, Any]:
    """Get SharePoint sharing metrics."""
    # Use explicit tenant_id if provided (and authorized), else use auth_tenant
    effective_tenant_id = tenant_id or auth_tenant
    
    if effective_tenant_id == "NONE":
        return {
            "active_links_count": 0,
            "by_type": {},
            "top_sharers": {}
        }

    service = SharePointAnalyticsService(db)
    return await service.get_summary_metrics(effective_tenant_id)


@router.get("/sharing-links")
async def get_sharing_links(
    tenant_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth_tenant: str = Depends(get_authorized_tenant),
) -> list[dict[str, Any]]:
    """Get active SharePoint sharing links."""
    effective_tenant_id = tenant_id or auth_tenant
    
    if effective_tenant_id == "NONE":
        return []

    service = SharePointAnalyticsService(db)
    links = await service.get_active_sharing_links(effective_tenant_id, limit, offset)
    
    return [
        {
            "id": str(link.id),
            "event_time": link.event_time.isoformat(),
            "operation": link.operation,
            "file_name": link.file_name,
            "file_path": link.file_path,
            "site_url": link.site_url,
            "user_email": link.user_email,
            "sharing_type": link.sharing_type,
            "share_link_url": link.share_link_url,
            "target_user": link.target_user,
            "is_active": link.is_active,
        }
        for link in links
    ]
