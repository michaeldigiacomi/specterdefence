# SpecterDefence API

from fastapi import APIRouter, Depends

from src.api.auth_local import get_current_user

from src.api import (
    alerts,
    analytics,
    auth,
    auth_local,
    ca_policies,
    dashboard,
    health,
    mailbox_rules,
    mfa_report,
    oauth_apps,
    settings,
    tenants,
    websocket,
)

router = APIRouter()

# Unprotected routes
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth_local.router, prefix="/auth/local", tags=["local-auth"])
router.include_router(websocket.router, prefix="/ws", tags=["websocket"])

# Protected routes
protected_deps = [Depends(get_current_user)]

router.include_router(auth.router, prefix="/auth", tags=["authentication"], dependencies=protected_deps)
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"], dependencies=protected_deps)
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"], dependencies=protected_deps)
router.include_router(alerts.router, prefix="/alerts", tags=["alerts"], dependencies=protected_deps)
router.include_router(mailbox_rules.router, prefix="/mailbox-rules", tags=["mailbox-rules"], dependencies=protected_deps)
router.include_router(oauth_apps.router, prefix="/oauth-apps", tags=["oauth-apps"], dependencies=protected_deps)
router.include_router(ca_policies.router, prefix="/ca-policies", tags=["ca-policies"], dependencies=protected_deps)
router.include_router(mfa_report.router, prefix="/mfa-report", tags=["mfa-report"], dependencies=protected_deps)
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"], dependencies=protected_deps)
router.include_router(settings.router, prefix="/settings", tags=["settings"], dependencies=protected_deps)

