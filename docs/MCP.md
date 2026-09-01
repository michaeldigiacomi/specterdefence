# SpecterDefence MCP Server

Exposes SpecterDefence security data to AI agents via the Model Context Protocol (stdio). The MCP server is a thin layer over the REST API — it never touches the database.

## Setup

```bash
# mcp is an optional dependency group (not needed for the backend)
poetry install --with mcp
# or: pip install "mcp>=1.10,<2"
```

Required env (see `mcp_server/.env.example`):

| Var | Default | Purpose |
|---|---|---|
| `SPECTER_BASE_URL` | `http://localhost:8000` | Backend API base URL |
| `SPECTER_USERNAME` | `admin` | SpecterDefence account |
| `SPECTER_PASSWORD` | — (required) | Account password |
| `SPECTER_TIMEOUT` | `30` | Request timeout (s) |

The server logs in via `POST /api/v1/auth/local/login`, caches the JWT, and re-authenticates transparently on 401. Use a dedicated non-admin account for agents — the tools below are read-only except `run_mfa_scan` and `tenant_health_check`.

## Registering with an MCP client

Claude Desktop / Claude Code (`claude_desktop_config.json` / `.mcp.json`):

```json
{
  "mcpServers": {
    "specterdefence": {
      "command": "poetry",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "cwd": "/path/to/specterdefence",
      "env": {
        "SPECTER_BASE_URL": "http://localhost:8000",
        "SPECTER_USERNAME": "agent",
        "SPECTER_PASSWORD": "<password>"
      }
    }
  }
}
```

Any MCP-compatible agent host works the same way: command `python -m mcp_server.server`, env vars above.

## Tools

| Tool | Endpoint | Notes |
|---|---|---|
| `list_tenants` | `GET /tenants/` | Gets tenant UUIDs — call first |
| `tenant_health_check` | `POST /tenants/{id}/health-check` | Tests Graph connectivity, updates status |
| `dashboard_summary` | `GET /dashboard/summary` | Overall posture stats |
| `top_risk_users` | `GET /dashboard/top-risk-users` | limit 1–50, `7d/30d/90d` |
| `anomaly_breakdown` | `GET /dashboard/anomaly-breakdown` | Anomaly counts by type |
| `login_timeline` | `GET /dashboard/login-timeline` | Success/failed over time |
| `alert_history` | `GET /alerts/history` | Filters: tenant, event type, severity, user, limit 1–1000 |
| `list_alert_rules` | `GET /alerts/rules` | Rules incl. cooldowns |
| `list_webhooks` | `GET /alerts/webhooks` | Discord destinations |
| `mfa_summary` | `GET /mfa-report/` | Coverage %, admin coverage, method mix |
| `users_without_mfa` | `GET /mfa-report/users-without-mfa` | |
| `admins_without_mfa` | `GET /mfa-report/admins-without-mfa` | |
| `run_mfa_scan` | `POST /mfa-report/scan` | Write action; takes Azure AD tenant ID |
| `list_ca_policies` | `GET /ca-policies/` | state: `enabled/disabled/reportOnly` |
| `ca_policy_changes` | `GET /ca-policies/changes` | Drift history per tenant |
| `suspicious_oauth_apps` | `GET /oauth-apps/tenants/{id}/suspicious` | |
| `oauth_app_summary` | `GET /oauth-apps/tenants/{id}/summary` | |
| `list_devices` | `GET /endpoints/devices` | Endpoint agent inventory |
| `device_events` | `GET /endpoints/devices/{id}/events` | 4688 / 4104 telemetry |

## Notes

- Tenant IDs in most tools are the **internal UUID** from `list_tenants`; `run_mfa_scan` takes the **Azure AD tenant ID** (matching the API design).
- Login rate limit: 5 failed attempts / 5 min blocks an IP for 15 min — wrong `SPECTER_PASSWORD` in a retry loop will lock the agent out.
- Adding a new tool: add a method to `SpecterClient` callers in `mcp_server/server.py` under the matching section; keep the endpoint path verified against `src/api/`.
- Tests: `pytest tests/unit/mcp/` (no `mcp` dependency needed — client only requires `httpx`).