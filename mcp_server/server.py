"""SpecterDefence MCP server.

Exposes SpecterDefence security data (tenants, alerts, MFA, Conditional Access,
OAuth apps, endpoint telemetry) as MCP tools so AI agents can query and triage
your Microsoft 365 security posture.

Run with:  python -m mcp_server.server        (stdio transport)

Every tool talks to the SpecterDefence REST API backend — it never touches the
database directly.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.client import BackendError, SpecterClient
from mcp_server.config import McpConfig, McpConfigError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("specterdefence.mcp")

# Reduce noisy httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)

mcp = FastMCP(
    "specterdefence",
    instructions=(
        "Tools for querying SpecterDefence, a Microsoft 365 security posture "
        "monitoring platform. Call list_tenants first to get tenant IDs; most "
        "tools accept an optional tenant_id to scope results. Time ranges are "
        "'7d', '30d' or '90d'. Severity values are low, medium, high, critical."
    ),
)

_client: SpecterClient | None = None


def get_client() -> SpecterClient:
    global _client
    if _client is None:
        _client = SpecterClient(McpConfig.from_env())
    return _client


def tool_error(e: Exception) -> str:
    """Format an exception into a concise string for the agent."""
    if isinstance(e, BackendError):
        prefix = f"HTTP {e.status_code}: " if e.status_code else ""
        return f"Error — {prefix}{e}"
    if isinstance(e, McpConfigError):
        return f"Configuration error — {e}"
    return f"Unexpected error — {type(e).__name__}: {e}"


# =============================================================================
# Tenants
# =============================================================================


@mcp.tool()
async def list_tenants(include_inactive: bool = False) -> str:
    """List all registered Microsoft 365 tenants with connection status.

    Use this first to obtain tenant IDs (internal UUIDs) for other tools.
    Args:
        include_inactive: Include inactive tenants.
    """
    try:
        tenants = await get_client().get("/tenants/", params={"include_inactive": include_inactive})
        return _fmt_json(tenants)
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def tenant_health_check(tenant_id: str) -> str:
    """Run a health check on a tenant's Microsoft Graph connection.

    Tests Graph connectivity, credentials, and permissions; updates the
    tenant's connection status. Args:
        tenant_id: Internal tenant UUID.
    """
    try:
        result = await get_client().post(f"/tenants/{tenant_id}/health-check")
        return _fmt_json(result)
    except Exception as e:
        return tool_error(e)


# =============================================================================
# Dashboard / analytics
# =============================================================================


@mcp.tool()
async def dashboard_summary() -> str:
    """Get overall security posture summary statistics.
    """
    try:
        return _fmt_json(await get_client().get("/dashboard/summary"))
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def top_risk_users(limit: int = 10, time_range: str = "30d") -> str:
    """List users with the highest risk scores and anomaly counts.

    Args:
        limit: Max users to return (1-50).
        time_range: One of '7d', '30d', '90d'.
    """
    try:
        return _fmt_json(
            await get_client().get(
                "/dashboard/top-risk-users", params={"limit": limit, "time_range": time_range}
            )
        )
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def anomaly_breakdown(time_range: str = "30d") -> str:
    """Get login-anomaly counts broken down by type (impossible travel,
    brute force, new country, etc.) with percentages.

    Args:
        time_range: One of '7d', '30d', '90d'.
    """
    try:
        return _fmt_json(
            await get_client().get("/dashboard/anomaly-breakdown", params={"time_range": time_range})
        )
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def login_timeline(time_range: str = "30d") -> str:
    """Get login activity over time with success/failed breakdown.

    Args:
        time_range: One of '7d', '30d', '90d'.
    """
    try:
        return _fmt_json(
            await get_client().get("/dashboard/login-timeline", params={"time_range": time_range})
        )
    except Exception as e:
        return tool_error(e)


# =============================================================================
# Alerts
# =============================================================================


@mcp.tool()
async def alert_history(
    tenant_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    user_email: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """Get history of sent alerts with optional filtering.

    Args:
        tenant_id: Filter by internal tenant UUID.
        event_type: Filter by event type.
        severity: One of low, medium, high, critical.
        user_email: Filter by user email.
        limit: Max results (1-1000).
        offset: Pagination offset.
    """
    try:
        return _fmt_json(
            await get_client().get(
                "/alerts/history",
                params={
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "severity": severity,
                    "user_email": user_email,
                    "limit": limit,
                    "offset": offset,
                },
            )
        )
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def list_alert_rules(include_inactive: bool = False) -> str:
    """List configured alert rules (event types, min severity, cooldowns).

    Args:
        include_inactive: Include inactive rules.
    """
    try:
        return _fmt_json(
            await get_client().get("/alerts/rules", params={"include_inactive": include_inactive})
        )
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def list_webhooks(include_inactive: bool = False) -> str:
    """List configured alert webhooks (Discord destinations).

    Args:
        include_inactive: Include inactive webhooks.
    """
    try:
        return _fmt_json(
            await get_client().get("/alerts/webhooks", params={"include_inactive": include_inactive})
        )
    except Exception as e:
        return tool_error(e)


# =============================================================================
# MFA
# =============================================================================


@mcp.tool()
async def mfa_summary() -> str:
    """Get MFA enrollment summary for the tenant(s) you have access to:
    coverage %, admin coverage, strong/weak method distribution, compliance.
    """
    try:
        return _fmt_json(await get_client().get("/mfa-report/"))
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def users_without_mfa() -> str:
    """List users who have not enrolled in MFA.
    """
    try:
        return _fmt_json(await get_client().get("/mfa-report/users-without-mfa"))
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def admins_without_mfa() -> str:
    """List admin users who have not enrolled in MFA.
    """
    try:
        return _fmt_json(await get_client().get("/mfa-report/admins-without-mfa"))
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def run_mfa_scan(tenant_id: str, full_scan: bool = False) -> str:
    """Trigger a manual MFA enrollment scan against Microsoft Graph for a tenant.

    Args:
        tenant_id: Internal tenant UUID (Azure AD tenant ID used by the scan API).
        full_scan: Force a full rescan instead of incremental.
    """
    try:
        return _fmt_json(
            await get_client().post(
                "/mfa-report/scan",
                json_body={"tenant_id": tenant_id, "full_scan": full_scan,
                           "check_compliance": True},
            )
        )
    except Exception as e:
        return tool_error(e)


# =============================================================================
# Conditional Access policies
# =============================================================================


@mcp.tool()
async def list_ca_policies(tenant_id: str | None = None, state: str | None = None) -> str:
    """List Conditional Access policies with optional filtering.

    Args:
        tenant_id: Filter by internal tenant UUID.
        state: One of 'enabled', 'disabled', 'reportOnly'.
    """
    try:
        return _fmt_json(
            await get_client().get(
                "/ca-policies/", params={"tenant_id": tenant_id, "state": state}
            )
        )
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def ca_policy_changes(tenant_id: str, limit: int = 20) -> str:
    """Get recent Conditional Access policy changes (drift detection) for a tenant.

    Args:
        tenant_id: Internal tenant UUID.
        limit: Max changes to return.
    """
    try:
        return _fmt_json(
            await get_client().get(
                "/ca-policies/changes", params={"tenant_id": tenant_id, "limit": limit}
            )
        )
    except Exception as e:
        return tool_error(e)


# =============================================================================
# OAuth apps
# =============================================================================


@mcp.tool()
async def suspicious_oauth_apps(tenant_id: str) -> str:
    """List OAuth applications flagged as suspicious for a tenant.

    Args:
        tenant_id: Internal tenant UUID.
    """
    try:
        return _fmt_json(await get_client().get(f"/oauth-apps/tenants/{tenant_id}/suspicious"))
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def oauth_app_summary(tenant_id: str) -> str:
    """Get an OAuth application risk summary for a tenant (counts by risk).

    Args:
        tenant_id: Internal tenant UUID.
    """
    try:
        return _fmt_json(await get_client().get(f"/oauth-apps/tenants/{tenant_id}/summary"))
    except Exception as e:
        return tool_error(e)


# =============================================================================
# Endpoint agents
# =============================================================================


@mcp.tool()
async def list_devices(status: str | None = None, limit: int = 100) -> str:
    """List enrolled Windows endpoint devices with heartbeat status.

    Args:
        status: Optional filter (device status, e.g. 'online' or equivalent).
        limit: Max devices (1-500).
    """
    try:
        return _fmt_json(
            await get_client().get("/endpoints/devices", params={"status": status, "limit": limit})
        )
    except Exception as e:
        return tool_error(e)


@mcp.tool()
async def device_events(
    device_id: str,
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> str:
    """Get telemetry events for an endpoint device (process creation 4688,
    PowerShell script-block 4104).

    Args:
        device_id: Internal device UUID (from list_devices).
        event_type: Optional event type filter.
        severity: Optional severity filter.
        limit: Max events (1-1000).
    """
    try:
        return _fmt_json(
            await get_client().get(
                f"/endpoints/devices/{device_id}/events",
                params={"event_type": event_type, "severity": severity, "limit": limit},
            )
        )
    except Exception as e:
        return tool_error(e)


# =============================================================================
# Helpers
# =============================================================================


def _fmt_json(data: Any) -> str:
    """Compact JSON dump so tool results stay small over the wire."""
    import json

    return json.dumps(data, default=str, separators=(",", ":"))


def main() -> None:
    """Entry point — run the MCP stdio server."""
    # Fail fast on missing config rather than at first tool call.
    McpConfig.from_env()
    logger.info("Starting SpecterDefence MCP server (stdio)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()