# SpecterDefence API

from fastapi import APIRouter
from src.api import tenants, health, auth, analytics, alerts

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
