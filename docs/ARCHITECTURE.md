# SpecterDefence Architecture

> System design reference for the SpecterDefence Microsoft 365 security monitoring platform. Reflects the code as of 2026-08-28.

## 1. Overview

SpecterDefence is a single-binary FastAPI backend with a React SPA frontend, a scheduled data collector, and an optional Windows endpoint agent. It monitors Microsoft 365 tenants and raises deduplicated alerts via WebSocket and Discord webhooks.

| Capability | Where |
|------------|-------|
| Tenant registration & credential storage | `src/api/tenants.py`, `src/services/tenant.py`, `src/services/encryption.py` |
| MFA compliance | `src/services/mfa_report.py`, `src/clients/mfa_report.py` |
| Conditional Access monitoring | `src/services/ca_policies.py`, `src/clients/ca_policies.py` |
| OAuth app risk | `src/services/oauth_apps.py`, `src/clients/oauth_apps.py` |
| Mailbox rule monitoring | `src/services/mailbox_rules.py`, `src/clients/mailbox_rules.py` |
| Audit-log collection (Entra/Exchange/SharePoint/DLP) | `src/collector/o365_feed.py` (O365 Management Activity API) |
| Login analytics & anomalies | `src/analytics/logins.py`, `src/analytics/anomalies.py` |
| Threat intel (AbuseIPDB, AlienVault OTX) | `src/analytics/threat_intel.py` |
| GeoIP lookups | `src/analytics/geo_ip.py` (ip-api.com) |
| SharePoint / insider threat / DLP | `src/analytics/sharepoint.py`, `src/analytics/insider_threat.py`, `src/api/sharepoint.py`, `src/api/dlp.py` |
| Mailbox security (access, events) | `src/api/mailbox.py` |
| Alert engine (rules, dedup, Discord) | `src/alerts/engine.py`, `src/alerts/rules.py`, `src/alerts/discord.py` |
| Alert processing & WebSocket streaming | `src/services/alert_processor.py`, `src/services/alert_stream.py`, `src/api/websocket.py` |
| Website / SSL / domain monitoring | `src/api/monitoring/`, `src/services/monitoring/`, `src/collector/monitoring.py` |
| Endpoint agent backend | `src/api/endpoints.py` (enroll, heartbeat, events, devices) |
| Windows agent | `agent/SpecterAgent` (.NET 8) |

## 2. System diagram

```
Microsoft 365 tenant ──(Graph API, client credentials)──┐
Microsoft 365 tenant ──(O365 Mgmt Activity API)──┐      │
                                                 ▼      ▼
   CronJob: collector (*/5) ───► audit_logs ───► login analytics
                                                 + anomaly detection
                                                 + threat intel + geoIP
   CronJob: security_scans (every 4h) ───► MFA / CA / OAuth / mailbox-rule reports
                                                 │
   Windows agents ──(enroll / heartbeat / events)──► endpoint_devices, endpoint_events
                                                 │
                                   Alerts ──► rules + dedup ──► Discord webhooks
                                                 └──────────► WebSocket ──► React UI
   PostgreSQL (asyncpg) or SQLite stores everything. Tenant client secrets and
   webhook URLs are Fernet-encrypted at rest.
```

All HTTP traffic enters through Traefik ingress (`k8s/prod/ingress.yaml`): host `specterdefence.digitaladrenalin.net` serves the marketing site; host `app.specterdefence.digitaladrenalin.net` routes `/api` and `/ws` to the backend, everything else to the frontend.

## 3. Backend structure

```
src/
├── main.py        # FastAPI app: security headers + request-logging middleware, lifespan init_db()
├── config.py      # Pydantic Settings from env (see Configuration below)
├── database.py    # async SQLAlchemy engine/session
├── api/           # REST routers, aggregated in __init__.py, mounted at /api/v1
│   └── monitoring/  # websites.py, ssl.py, domains.py
├── services/      # business logic + services/monitoring/
├── clients/       # MSAL-backed Graph clients per data type
├── models/        # SQLAlchemy ORM + Pydantic schemas
├── alerts/        # engine, rules, discord
├── analytics/     # anomaly detection, threat intel, geoIP
└── collector/     # main.py (audit feed), security_scans.py, monitoring.py — run as CronJobs
```

**Auth (`src/api/auth_local.py`).** JWT-based local auth. Login endpoint: bcrypt verify, per-IP rate limit of 5 failures / 5 min window, then 15 min block; token lifetime 2 hours on login (`create_access_token` default is 24 h). Unprotected routes: `/health`, `/auth/local/*`, `/ws/*`, `/endpoints/*`. Everything else requires `get_current_user`.

**Agent auth.** Devices enroll with a one-time tenant-scoped token (`POST /api/v1/endpoints/enroll`) and then authenticate heartbeat/event calls with an `X-Device-Token` header validated against its stored hash.

### Configuration (`src/config.py`)

Required: `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `ENCRYPTION_KEY` (or falls back to `SECRET_KEY`), `DATABASE_URL`. Optional: `DEBUG`, `HOST`, `PORT`, `ADMIN_USERNAME`, `CORS_ORIGINS`, `TRUSTED_PROXIES`, `ENCRYPTION_SALT`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_EXPIRATION_HOURS`, `MS_GRAPH_API_URL`, `MS_LOGIN_URL`, `ABUSEIPDB_API_KEY`, `ALIENVAULT_OTX_API_KEY`, `KIMI_API_KEY` (reserved, unused). Collector tuning (env): `COLLECTION_LOOKBACK_MINUTES` (default 60), `COLLECTION_INTERVAL_MINUTES` (5), `COLLECTION_LATENCY_BUFFER_MINUTES` (15), `MAX_EVENTS_PER_BATCH` (1000).

### Encryption (`src/services/encryption.py`)

Fernet (AES-128-CBC + HMAC-SHA256). The Fernet key is derived via PBKDF2-SHA256, 600,000 iterations, from `ENCRYPTION_KEY` (fallback `SECRET_KEY`), with a 16-byte salt derived from `ENCRYPTION_SALT` (fallback: derived from the key itself). Used for `TenantModel.client_secret` and alert webhook URLs. **No key-versioning support**: rotating `ENCRYPTION_KEY` requires re-encrypting stored secrets (see `docs/secret-rotation.md`).

## 4. Detection logic

All rule-based; no ML.

**MFA report.** Fetches `authentication/methods` per user; strength tiers STRONG (FIDO2, Windows Hello, cert-based) > MODERATE (Authenticator) > WEAK (SMS, voice) > NONE. Admins without MFA → CRITICAL; weak admin MFA → HIGH.

**CA policies.** Alerts on policy disabled (HIGH), MFA removed (CRITICAL), scope broadened to all apps (HIGH), admin exclusions (CRITICAL). Score = 50 base +20 MFA required, +10 all users, +10 compliant device, +5 risk conditions, +5 location conditions.

**OAuth apps.** Risk score from unverified publisher (30), mail access (25), User.Read.All (20), Files.Read.All (20), admin consent (15), permission count (10). Buckets: CRITICAL 80+, HIGH 60+, MEDIUM 40+, LOW otherwise.

**Login anomalies** (`src/analytics/anomalies.py`, `AnomalyType`): `impossible_travel` (haversine distance vs. 900 km/h max speed; risk = 100 − actual/min time ×100), `new_country`, `new_ip`, `failed_login`, `multiple_failures`, `suspicious_location`, `malicious_ip`, plus `unapproved_country` check against the tenant's `approved_countries` list (risk +80). Failure classification of raw O365 sign-ins uses `FAILURE_ERROR_CODES` (50053, 50074, 50126, 50127, …); ErrorNumber 50140 (MFA required) is **not** counted as a failure. See `docs/cronjob-processing-flows.md` for the full pipeline.

**Alert deduplication.** SHA-256 hash of event type + user + tenant (+ locations / IP where relevant); suppressed if the same rule + hash fired within the rule's `cooldown_minutes` (default 30). Event types and severities are the enums in `src/models/alerts.py` (`EventType`, `SeverityLevel`, `WebhookType`).

## 5. Endpoint agent

.NET 8 Windows service (`agent/SpecterAgent`, ~560 lines). Subscribes via `EventLogWatcher` to Security 4688 (process creation) and PowerShell 4104 (script blocks); flags events suspicious on pattern match (`-enc`, `iex`, `downloadstring`, `certutil`, `curl`). Events are buffered in a local SQLite database and uploaded on a 30-second loop; heartbeat every 5 minutes, silent enrollment via `--enrollment-token` / `--backend-url` CLI flags. Details: `docs/ENDPOINT-AGENT.md`.

## 6. API map

Mounted at `/api/v1` (Swagger UI at `/docs`). Router prefixes from `src/api/__init__.py`:

| Prefix | Purpose | Notes |
|--------|---------|-------|
| `/health` | liveness/readiness | public; also top-level `/health`, `/ready` |
| `/auth/local` | login/logout/me/check/change-password | public, rate-limited |
| `/auth` | Graph auth helpers | protected |
| `/users` | user CRUD | protected |
| `/tenants` | tenant CRUD, validate, health-check; `approved_countries` set via `PATCH /tenants/{id}` | protected |
| `/analytics` | login analytics | protected |
| `/alerts` | rules, webhooks, history, webhook test | protected |
| `/mailbox-rules`, `/oauth-apps`, `/ca-policies`, `/mfa-report` | posture data + alerts + scan triggers | protected |
| `/dashboard` | aggregated dashboard data + export | protected |
| `/settings`, `/users` | settings & user management | protected |
| `/monitoring` | websites/ssl/domains monitoring CRUD + checks | protected |
| `/diagnostics` | ingestion diagnostics | protected |
| `/sharepoint`, `/dlp`, `/mailbox-security` | sharing, DLP, mailbox-access data | protected |
| `/endpoints` | device enroll/heartbeat/events/summary/generate-token | public (device-token authed) |
| `/ws/alerts` | WebSocket alert stream | public; message types: `ping`, `pong`, `connection`, `alert` |

## 7. Frontend

React 18 + TypeScript + Vite (`frontend/`), Tailwind, TanStack Query, Zustand (persisted store `specterdefence-storage`) for auth/session state. Pages: Dashboard, Login, Tenants, LoginAnalytics, Anomalies, MapPage, AlertFeed, Settings, CAPolicies, MailboxRules, MFAReport, OAuthApps, Monitoring, SharePoint, InsiderThreat, MailboxSecurity, Endpoints, Users (+ tests). API client in `src/services/api.ts`. JWT is stored via the Zustand persist middleware.

## 8. Deployment (Kubernetes)

Raw manifests in `k8s/prod/` (no Helm). Namespace `specterdefence`; deployments `specterdefence-backend` (FastAPI, 1 replica) and `specterdefence-frontend` (Nginx, 1 replica); marketing site; CronJobs `specterdefence-collector-prod` (`*/5 * * * *`, `python -m src.collector.main`) and `specterdefence-security-scans-prod` (`0 */4 * * *`, `python -m src.collector.security_scans`). Traefik ingress (no TLS block in the manifests — configure cert-manager/TLS at the ingress controller). Secrets come from `specterdefence-secrets`; images `ghcr.io/michaeldigiacomi/specterdefence-{backend,frontend}:latest` pulled via `ghcr-registry-secret`. Full guide: `docs/SECURE-DEPLOYMENT.md`, manifest reference: `k8s/README.md`.

Known limitations of the current manifests (single-node dev-grade): 1 replica each, no HPA/PDB/NetworkPolicy, no Pod Security Standards enforcement.

## 9. Future considerations

Not currently implemented (do not document as existing): remediation actions, ML/UEBA detection, multi-channel alert integrations (email/SMS/PagerDuty/Teams), RBAC roles beyond admin/user, long-term audit-log archiving, Prometheus metrics endpoint, multi-replica scaling (in-memory WebSocket fan-out), Vault/ESO secret management (optional ops pattern only — no Vault client code in the app).
