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
    diagnostics,
    endpoints,
    health,
    mailbox_rules,
    mfa_report,
    monitoring,
    oauth_apps,
    settings,
    sharepoint,
    tenants,
    users,
    websocket,
    dlp,
    mailbox,
)

router = APIRouter()

# Unprotected routes
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth_local.router, prefix="/auth/local", tags=["local-auth"])
router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
router.include_router(endpoints.router, prefix="/endpoints", tags=["endpoints"])

# Protected routes
protected_deps = [Depends(get_current_user)]

router.include_router(auth.router, prefix="/auth", tags=["authentication"], dependencies=protected_deps)
router.include_router(users.router, prefix="/users", tags=["users"], dependencies=protected_deps)
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"], dependencies=protected_deps)
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"], dependencies=protected_deps)
router.include_router(alerts.router, prefix="/alerts", tags=["alerts"], dependencies=protected_deps)
router.include_router(mailbox_rules.router, prefix="/mailbox-rules", tags=["mailbox-rules"], dependencies=protected_deps)
router.include_router(oauth_apps.router, prefix="/oauth-apps", tags=["oauth-apps"], dependencies=protected_deps)
router.include_router(ca_policies.router, prefix="/ca-policies", tags=["ca-policies"], dependencies=protected_deps)
router.include_router(mfa_report.router, prefix="/mfa-report", tags=["mfa-report"], dependencies=protected_deps)
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"], dependencies=protected_deps)
router.include_router(settings.router, prefix="/settings", tags=["settings"], dependencies=protected_deps)
router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"], dependencies=protected_deps)
router.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"], dependencies=protected_deps)
router.include_router(sharepoint.router, prefix="/sharepoint", tags=["sharepoint"], dependencies=protected_deps)
router.include_router(dlp.router, prefix="/dlp", tags=["dlp"], dependencies=protected_deps)
router.include_router(mailbox.router, prefix="/mailbox-security", tags=["mailbox-security"], dependencies=protected_deps)
router.include_router(mailbox.router, prefix="/mailbox-security", tags=["mailbox-security"], dependencies=protected_deps)
