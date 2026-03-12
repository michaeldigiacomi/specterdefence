"""Website monitoring API endpoints."""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_authorized_tenant
from src.services.monitoring.website import WebsiteMonitorService

router = APIRouter(prefix="/websites", tags=["Website Monitoring"])


class WebsiteCreate(BaseModel):
    """Create website request."""
    name: str
    url: str
    check_interval_minutes: int = 5


class WebsiteResponse(BaseModel):
    """Website response model."""
    id: str
    tenant_id: str
    name: str
    url: str
    is_enabled: bool
    check_interval_minutes: int
    last_checked_at: Optional[str] = None
    last_status: Optional[str] = None
    last_response_code: Optional[int] = None
    last_response_time_ms: Optional[float] = None
    last_error: Optional[str] = None
    uptime_percentage: float
    total_checks: int
    successful_checks: int
    
    class Config:
        from_attributes = True


class WebsiteStatsResponse(BaseModel):
    """Website stats response model."""
    total: int
    up: int
    down: int
    error: int
    unknown: int
    average_uptime: float


def _model_to_response(model) -> WebsiteResponse:
    """Convert model to response."""
    return WebsiteResponse(
        id=str(model.id),
        tenant_id=str(model.tenant_id),
        name=model.name,
        url=model.url,
        is_enabled=model.is_enabled,
        check_interval_minutes=model.check_interval_minutes,
        last_checked_at=model.last_checked_at.isoformat() if model.last_checked_at else None,
        last_status=model.last_status,
        last_response_code=model.last_response_code,
        last_response_time_ms=model.last_response_time_ms,
        last_error=model.last_error,
        uptime_percentage=model.uptime_percentage,
        total_checks=model.total_checks,
        successful_checks=model.successful_checks,
    )


@router.get("", response_model=list[WebsiteResponse])
async def list_websites(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all website monitors."""
    service = WebsiteMonitorService(db)
    websites = await service.get_websites(tenant_id)
    return [_model_to_response(w) for w in websites]


@router.get("/stats", response_model=WebsiteStatsResponse)
async def get_website_stats(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get website monitoring stats."""
    service = WebsiteMonitorService(db)
    stats = await service.get_website_stats(tenant_id)
    return WebsiteStatsResponse(**stats)


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(
    website_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific website monitor."""
    service = WebsiteMonitorService(db)
    website = await service.get_website(website_id, tenant_id)
    
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    
    return _model_to_response(website)


@router.post("", response_model=WebsiteResponse, status_code=201)
async def create_website(
    data: WebsiteCreate,
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Create a new website monitor."""
    service = WebsiteMonitorService(db)
    website = await service.create_website(
        tenant_id=tenant_id,
        name=data.name,
        url=data.url,
        check_interval_minutes=data.check_interval_minutes,
    )
    return _model_to_response(website)


@router.delete("/{website_id}", status_code=204)
async def delete_website(
    website_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete a website monitor."""
    service = WebsiteMonitorService(db)
    deleted = await service.delete_website(website_id, tenant_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Website not found")


@router.post("/{website_id}/check", response_model=WebsiteResponse)
async def check_website(
    website_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Run a check for a specific website."""
    service = WebsiteMonitorService(db)
    website = await service.run_check(website_id)
    
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    
    return _model_to_response(website)


@router.post("/check-all")
async def check_all_websites(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Run checks for all websites."""
    service = WebsiteMonitorService(db)
    websites = await service.check_all_websites(tenant_id)
    return {"checked": len(websites)}
