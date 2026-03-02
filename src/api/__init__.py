# SpecterDefence API

from fastapi import APIRouter
from src.api import tenants, health, auth, auth_local, analytics, alerts, mailbox_rules, oauth_apps, ca_policies, websocket, dashboard, mfa_report, settings

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(auth_local.router, prefix="/auth/local", tags=["local-auth"])
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
router.include_router(mailbox_rules.router, prefix="/mailbox-rules", tags=["mailbox-rules"])
router.include_router(oauth_apps.router, prefix="/oauth-apps", tags=["oauth-apps"])
router.include_router(ca_policies.router, prefix="/ca-policies", tags=["ca-policies"])
router.include_router(mfa_report.router, prefix="/mfa-report", tags=["mfa-report"])
router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(settings.router, prefix="/settings", tags=["settings"])
