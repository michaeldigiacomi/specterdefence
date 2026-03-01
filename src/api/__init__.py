# SpecterDefence API

from fastapi import APIRouter
from src.api import tenants, health, auth

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
