"""Domain expiry monitoring API endpoints."""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_authorized_tenant
from src.services.monitoring.domain import DomainExpiryService

router = APIRouter(prefix="/domains", tags=["Domain Expiry Monitoring"])


class DomainCreate(BaseModel):
    """Create domain request."""
    domain: str


class DomainResponse(BaseModel):
    """Domain response model."""
    id: str
    tenant_id: str
    domain: str
    registrar: Optional[str] = None
    registration_date: Optional[str] = None
    expiry_date: Optional[str] = None
    days_until_expiry: Optional[int] = None
    is_expired: bool
    whois_error: Optional[str] = None
    last_checked_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class DomainStatsResponse(BaseModel):
    """Domain stats response model."""
    total: int
    active: int
    expired: int
    expiring_soon: int
    errors: int


def _model_to_response(model) -> DomainResponse:
    """Convert model to response."""
    return DomainResponse(
        id=str(model.id),
        tenant_id=str(model.tenant_id),
        domain=model.domain,
        registrar=model.registrar,
        registration_date=model.registration_date.isoformat() if model.registration_date else None,
        expiry_date=model.expiry_date.isoformat() if model.expiry_date else None,
        days_until_expiry=model.days_until_expiry,
        is_expired=model.is_expired,
        whois_error=model.whois_error,
        last_checked_at=model.last_checked_at.isoformat() if model.last_checked_at else None,
    )


@router.get("", response_model=list[DomainResponse])
async def list_domains(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all domains."""
    service = DomainExpiryService(db)
    domains = await service.get_domains(tenant_id)
    return [_model_to_response(d) for d in domains]


@router.get("/stats", response_model=DomainStatsResponse)
async def get_domain_stats(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get domain expiry stats."""
    service = DomainExpiryService(db)
    stats = await service.get_domain_stats(tenant_id)
    return DomainStatsResponse(**stats)


@router.get("/expiring", response_model=list[DomainResponse])
async def get_expiring_domains(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    days: int = Query(30, description="Days threshold"),
    db: AsyncSession = Depends(get_db),
):
    """Get domains expiring within threshold days."""
    service = DomainExpiryService(db)
    domains = await service.get_expiring_domains(tenant_id, days)
    return [_model_to_response(d) for d in domains]


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific domain."""
    service = DomainExpiryService(db)
    domain = await service.get_domain(domain_id, tenant_id)
    
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    return _model_to_response(domain)


@router.post("", response_model=DomainResponse, status_code=201)
async def create_domain(
    data: DomainCreate,
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Create a new domain monitor."""
    service = DomainExpiryService(db)
    domain = await service.create_domain(
        tenant_id=tenant_id,
        domain=data.domain,
    )
    return _model_to_response(domain)


@router.delete("/{domain_id}", status_code=204)
async def delete_domain(
    domain_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete a domain monitor."""
    service = DomainExpiryService(db)
    deleted = await service.delete_domain(domain_id, tenant_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Domain not found")


@router.post("/{domain_id}/check", response_model=DomainResponse)
async def check_domain(
    domain_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Check a domain's WHOIS information."""
    service = DomainExpiryService(db)
    domain = await service.check_domain(domain_id)
    
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    return _model_to_response(domain)


@router.post("/check-all")
async def check_all_domains(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Check all domains."""
    service = DomainExpiryService(db)
    domains = await service.check_all_domains(tenant_id)
    return {"checked": len(domains)}
