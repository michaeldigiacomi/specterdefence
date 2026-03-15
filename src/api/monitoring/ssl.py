"""SSL certificate monitoring API endpoints."""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.api.auth_local import get_authorized_tenant
from src.services.monitoring.ssl import SslCertificateService

router = APIRouter(prefix="/ssl", tags=["SSL Certificate Monitoring"])


class SslCertificateCreate(BaseModel):
    """Create SSL certificate request."""
    domain: str
    port: int = 443


class SslCertificateResponse(BaseModel):
    """SSL certificate response model."""
    id: str
    tenant_id: str
    domain: str
    port: int
    issuer: Optional[str] = None
    subject: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    days_until_expiry: Optional[int] = None
    serial_number: Optional[str] = None
    signature_algorithm: Optional[str] = None
    is_valid: bool
    has_errors: bool
    error_message: Optional[str] = None
    last_checked_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class SslStatsResponse(BaseModel):
    """SSL stats response model."""
    total: int
    valid: int
    expired: int
    expiring_soon: int
    errors: int


def _model_to_response(model) -> SslCertificateResponse:
    """Convert model to response."""
    return SslCertificateResponse(
        id=str(model.id),
        tenant_id=str(model.tenant_id),
        domain=model.domain,
        port=model.port,
        issuer=model.issuer,
        subject=model.subject,
        valid_from=model.valid_from.isoformat() if model.valid_from else None,
        valid_until=model.valid_until.isoformat() if model.valid_until else None,
        days_until_expiry=model.days_until_expiry,
        serial_number=model.serial_number,
        signature_algorithm=model.signature_algorithm,
        is_valid=model.is_valid,
        has_errors=model.has_errors,
        error_message=model.error_message,
        last_checked_at=model.last_checked_at.isoformat() if model.last_checked_at else None,
    )


@router.get("", response_model=list[SslCertificateResponse])
async def list_certificates(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all SSL certificates."""
    service = SslCertificateService(db)
    certificates = await service.get_certificates(tenant_id)
    return [_model_to_response(c) for c in certificates]


@router.get("/stats", response_model=SslStatsResponse)
async def get_ssl_stats(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get SSL certificate stats."""
    service = SslCertificateService(db)
    stats = await service.get_certificate_stats(tenant_id)
    return SslStatsResponse(**stats)


@router.get("/expiring", response_model=list[SslCertificateResponse])
async def get_expiring_certificates(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    days: int = Query(30, description="Days threshold"),
    db: AsyncSession = Depends(get_db),
):
    """Get certificates expiring within threshold days."""
    service = SslCertificateService(db)
    certificates = await service.get_expiring_certificates(tenant_id, days)
    return [_model_to_response(c) for c in certificates]


@router.get("/{certificate_id}", response_model=SslCertificateResponse)
async def get_certificate(
    certificate_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific SSL certificate."""
    service = SslCertificateService(db)
    certificate = await service.get_certificate(certificate_id, tenant_id)
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return _model_to_response(certificate)


@router.post("", response_model=SslCertificateResponse, status_code=201)
async def create_certificate(
    data: SslCertificateCreate,
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Create a new SSL certificate monitor."""
    service = SslCertificateService(db)
    certificate = await service.create_certificate(
        tenant_id=tenant_id,
        domain=data.domain,
        port=data.port,
    )
    # Automatically check the certificate to fetch details
    certificate = await service.check_certificate(certificate.id)
    return _model_to_response(certificate)


@router.delete("/{certificate_id}", status_code=204)
async def delete_certificate(
    certificate_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete an SSL certificate monitor."""
    service = SslCertificateService(db)
    deleted = await service.delete_certificate(certificate_id, tenant_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Certificate not found")


@router.post("/{certificate_id}/check", response_model=SslCertificateResponse)
async def check_certificate(
    certificate_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Check an SSL certificate."""
    service = SslCertificateService(db)
    certificate = await service.check_certificate(certificate_id)
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return _model_to_response(certificate)


@router.post("/check-all")
async def check_all_certificates(
    tenant_id: Optional[uuid.UUID] = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Check all SSL certificates."""
    service = SslCertificateService(db)
    certificates = await service.check_all_certificates(tenant_id)
    return {"checked": len(certificates)}
