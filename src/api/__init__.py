# SpecterDefence API

from fastapi import APIRouter
from src.api import tenants, health, auth, analytics, alerts, mailbox_rules, websocket

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
router.include_router(mailbox_rules.router, prefix="/mailbox-rules", tags=["mailbox-rules"])
router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
