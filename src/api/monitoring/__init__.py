"""Monitoring API endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["Monitoring"])

# Import sub-routers
from src.api.monitoring import websites, ssl, domains

router.include_router(websites.router)
router.include_router(ssl.router)
router.include_router(domains.router)

__all__ = ["router"]
