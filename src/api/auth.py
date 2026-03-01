from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()

class AuthRequest(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str

class AuthResponse(BaseModel):
    message: str
    tenant_id: str

@router.post("/register", response_model=AuthResponse)
async def register_tenant(auth: AuthRequest):
    """Register a new Office 365 tenant."""
    # Placeholder for SPD-2
    return AuthResponse(
        message="Tenant registered successfully",
        tenant_id=auth.tenant_id
    )

@router.post("/token")
async def get_token():
    """Get access token for tenant."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented"
    )
