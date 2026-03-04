from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict


@router.get("/", response_model=HealthResponse)
async def health():
    """Get detailed health status."""
    return HealthResponse(status="healthy", version="0.1.0", services={})
