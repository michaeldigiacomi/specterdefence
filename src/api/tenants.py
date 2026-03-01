from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class TenantBase(BaseModel):
    tenant_id: str
    display_name: str
    domain: str

class TenantCreate(TenantBase):
    client_id: str
    client_secret: str

class TenantResponse(TenantBase):
    id: str
    status: str
    created_at: datetime
    last_synced: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[TenantResponse])
async def list_tenants():
    """List all registered tenants."""
    return []

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(tenant: TenantCreate):
    """Create a new tenant registration."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented"
    )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str):
    """Get a specific tenant by ID."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented"
    )

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: str):
    """Delete a tenant registration."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented"
    )
