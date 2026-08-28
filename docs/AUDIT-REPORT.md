> **Internal Audit Report** — Generated 2026-08-28. This document records findings from a code-vs-docs comparison. The identified issues have been addressed in the updated documentation.

# SpecterDefence Code Audit Report

> **Audit Date:** 2026-08-28  
> **Auditor:** Automated code-vs-docs comparison  
> **Repository:** /tmp/specterdefence

---

## Executive Summary

This audit compares the documentation claims (README, ARCHITECTURE.md, 1-PAGER, ai-proposal, etc.) against the actual codebase. The platform is substantially implemented with a mature backend, functional frontend, and a working C# endpoint agent. However, there are notable gaps between doc claims and code reality — particularly around AI features, Slack integration, Helm charts, IPAPI_API_KEY config, and several undocumented API modules.

---

## 1. Application Setup (src/main.py)

### Docs Claim
- FastAPI app with lifespan, security headers middleware, CORS, TrustedHostMiddleware
- Security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS, CSP, Referrer-Policy
- SPA routing fallback for frontend
- Health/ready endpoints

### Code Actually Implements
- **All claimed middleware is present and implemented** (lines 42-95: SecurityHeadersMiddleware, RequestLoggingMiddleware)
- Lifespan handler initializes database on startup (lines 97-104)
- CORS middleware conditionally added only if `CORS_ORIGINS` is set (lines 115-121)
- TrustedHostMiddleware added in production, skipped in testing (lines 123-133)
- SPA routing with catch-all `/{path:path}` endpoint (lines 175-195)
- Health endpoint at `/health`, ready at `/ready`, version at `/api/v1/version`
- Static file serving for frontend dist

### Gaps
- None significant. Code matches docs well.

### Undocumented Features
- `RequestLoggingMiddleware` — logs all requests with method, path, status, duration. Not mentioned in docs.
- `/api/v1/version` endpoint — returns version and git SHA. Not documented in docs.
- `Permissions-Policy` header — set in code but not listed in the security headers table in ARCHITECTURE.md.
- Static file serving (frontend dist mounting) not documented in ARCHITECTURE.md.

### Inaccuracies
- ARCHITECTURE.md lists `Permissions-Policy` header value as `geolocation=(), microphone=(), camera=()` but code has a longer list: `geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=()`.

---

## 2. Configuration (src/config.py)

### Docs Claim
ARCHITECTURE.md §7.3 lists these env vars:
- `SECRET_KEY`, `DATABASE_URL`, `ENCRYPTION_KEY`, `ENCRYPTION_SALT`, `ADMIN_PASSWORD_HASH`, `JWT_SECRET_KEY`, `DEBUG`, `CORS_ORIGINS`, `KIMI_API_KEY`

README mentions: `SECRET_KEY`, `DEBUG`, `HOST`, `PORT`, `DATABASE_URL`, `ABUSEIPDB_API_KEY`, `ALIENVAULT_OTX_API_KEY`, `O365_CLIENT_SECRET`, `IPAPI_API_KEY`

### Code Actually Implements
All of the above plus:
- `APP_NAME`, `APP_VERSION`
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30)
- `TRUSTED_PROXIES` (list of trusted proxy IPs)
- `MS_GRAPH_API_URL`, `MS_LOGIN_URL`
- `ADMIN_USERNAME` (default "admin")
- `JWT_EXPIRATION_HOURS` (default 24)
- Field validators for `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `CORS_ORIGINS`

### Gaps
- **`IPAPI_API_KEY`** — claimed in README ("To use the pro version... set the `IPAPI_API_KEY` secret") but **does not exist in config.py**. The geo_ip.py client has no API key support at all; it only uses the free tier at `http://ip-api.com/json/`.
- **`O365_CLIENT_SECRET`** — listed in README as an optional secret but **does not exist in config.py**. Tenant secrets are stored per-tenant in the database (encrypted), not as a global env var.

### Undocumented Features
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_EXPIRATION_HOURS` — token expiration config not in docs
- `TRUSTED_PROXIES` — trusted proxy IP list for X-Forwarded-For handling, not documented
- `ADMIN_USERNAME` — configurable admin username, not documented
- `MS_GRAPH_API_URL`, `MS_LOGIN_URL` — Graph API base URLs, not documented
- `APP_NAME`, `APP_VERSION` — app metadata, not documented

### Inaccuracies
- **`KIMI_API_KEY`** — ai-proposal.md says "The config already includes a `KIMI_API_KEY` field, indicating some AI integration was planned." This is accurate — the field exists (config.py line ~120) with default `""`. However, **no code anywhere uses it**. It's a dead config field.
- Docs say `JWT_SECRET_KEY` is "required" but code auto-generates one if not provided (with validation against weak values in non-test mode).

---

## 3. Database Setup (src/database.py)

### Docs Claim
- SQLAlchemy async engine, session management, `init_db()` creates tables
- PostgreSQL (production) / SQLite (development) support

### Code Actually Implements
- Exactly as documented: async engine, session maker, `get_db()` dependency, `init_db()` with `Base.metadata.create_all`
- SQLite URL auto-conversion from `sqlite:///` to `sqlite+aiosqlite:///`

### Gaps
- None.

### Undocumented Features
- None.

### Inaccuracies
- None.

---

## 4. API Endpoints (src/api/*.py)

### Docs Claim
ARCHITECTURE.md §5 lists endpoints for: Auth, Tenants, MFA Reports, CA Policies, OAuth Apps, Mailbox Rules, Alerts, SharePoint & Insider Threat, Endpoint Agent, WebSocket, Health Checks.

### Code Actually Implements (full route inventory)

#### Documented & Implemented (matches docs):
| Area | Routes | Status |
|------|--------|--------|
| Auth (local) | POST `/auth/local/login`, POST `/auth/local/logout`, GET `/auth/local/me`, POST `/auth/local/change-password` | ✅ Matches |
| Tenants | GET `/tenants/`, POST `/tenants/`, GET `/tenants/{id}`, PATCH `/tenants/{id}`, DELETE `/tenants/{id}`, POST `/tenants/{id}/health-check`, POST `/tenants/{id}/validate` | ✅ Matches |
| MFA Report | GET `/mfa-report/` (summary), GET `/mfa-report/users`, GET `/mfa-report/admins-without-mfa`, GET `/mfa-report/trends`, POST `/mfa-report/scan` | ✅ Matches |
| CA Policies | GET `/ca-policies/`, GET `/ca-policies/{id}`, POST `/ca-policies/scan`, GET `/ca-policies/changes` | ✅ Matches |
| OAuth Apps | GET `/oauth-apps/`, GET `/oauth-apps/{id}`, POST `/oauth-apps/scan`, GET `/oauth-apps/high-risk` (via `/tenants/{id}/high-risk`) | ✅ Matches |
| Mailbox Rules | GET `/mailbox-rules/`, GET `/mailbox-rules/suspicious` (via `/tenants/{id}/suspicious`), POST `/mailbox-rules/scan` | ✅ Matches |
| Alerts | GET `/alerts/rules`, POST `/alerts/rules`, GET `/alerts/webhooks`, POST `/alerts/webhooks`, GET `/alerts/history`, POST `/alerts/webhooks/{id}/test` | ✅ Matches |
| WebSocket | WS `/ws/alerts`, GET `/ws/ws/stats` | ✅ Matches |
| Health | GET `/health`, GET `/ready` | ✅ Matches |
| Endpoint Agent | GET `/endpoints/devices`, POST `/endpoints/enroll`, POST `/endpoints/heartbeat`, POST `/endpoints/events`, GET `/endpoints/events` | ✅ Matches |

#### Gaps (doc claims but code doesn't implement):
| Claim | Reality |
|-------|--------|
| ARCHITECTURE.md §5.8: `GET /api/v1/sharepoint/stats` | Code implements `/api/v1/sharepoint/metrics` instead of `/stats` |
| ARCHITECTURE.md §5.8: `POST /api/v1/sharepoint/revoke/{id}` | **Not implemented** — no revoke endpoint exists in sharepoint.py |
| ARCHITECTURE.md §5.8: `GET /api/v1/insider-threat/summary` | **Not implemented** — no insider-threat API router exists. DLP events are at `/api/v1/dlp/` instead |
| ARCHITECTURE.md §5.8: `GET /api/v1/insider-threat/events` | **Not implemented** — DLP events are at `/api/v1/dlp/` |
| ARCHITECTURE.md §5.2: `POST /api/v1/tenants/{id}/validate` exists separately | Code has both `/validate` (pre-creation) and `/{tenant_id}/validate` (re-validate). Docs only list the latter. |

#### Undocumented API Endpoints (code exists, no doc mention):
| Route | File | Description |
|-------|------|-------------|
| GET `/api/v1/auth/local/check` | auth_local.py | Quick auth check endpoint |
| POST `/api/v1/tenants/validate` | tenants.py | Pre-creation validation endpoint |
| POST `/api/v1/tenants/health-check/all` | tenants.py | Health check all tenants at once |
| GET `/api/v1/mfa-report/users-without-mfa` | mfa_report.py | Users without MFA (separate from admins) |
| GET `/api/v1/mfa-report/method-distribution` | mfa_report.py | MFA method distribution |
| GET `/api/v1/mfa-report/strength-distribution` | mfa_report.py | MFA strength distribution |
| GET `/api/v1/mfa-report/compliance-report` | mfa_report.py | Full compliance report |
| POST `/api/v1/mfa-report/users/{id}/exemption` | mfa_report.py | Set MFA exemption |
| GET `/api/v1/mfa-report/alerts` | mfa_report.py | List MFA compliance alerts |
| POST `/api/v1/mfa-report/alerts/{id}/resolve` | mfa_report.py | Resolve MFA alert |
| GET `/api/v1/ca-policies/tenants/{id}/policies` | ca_policies.py | Tenant-specific CA policies |
| GET `/api/v1/ca-policies/tenants/{id}/disabled` | ca_policies.py | Disabled policies |
| GET `/api/v1/ca-policies/tenants/{id}/mfa` | ca_policies.py | MFA policies |
| GET `/api/v1/ca-policies/tenants/{id}/summary` | ca_policies.py | Policy summary |
| GET `/api/v1/ca-policies/alerts` | ca_policies.py | CA policy alerts |
| POST `/api/v1/ca-policies/alerts/{id}/acknowledge` | ca_policies.py | Acknowledge alert |
| GET/POST `/api/v1/ca-policies/tenants/{id}/baseline` | ca_policies.py | Baseline config |
| GET `/api/v1/oauth-apps/tenants/{id}/apps` | oauth_apps.py | Tenant OAuth apps |
| GET `/api/v1/oauth-apps/tenants/{id}/suspicious` | oauth_apps.py | Suspicious apps |
| GET `/api/v1/oauth-apps/tenants/{id}/summary` | oauth_apps.py | Apps summary |
| GET `/api/v1/oauth-apps/alerts` | oauth_apps.py | OAuth app alerts |
| POST `/api/v1/oauth-apps/alerts/{id}/acknowledge` | oauth_apps.py | Acknowledge alert |
| GET `/api/v1/oauth-apps/{id}/permissions` | oauth_apps.py | App permissions detail |
| POST `/api/v1/oauth-apps/{id}/revoke` | oauth_apps.py | Revoke app |
| GET `/api/v1/mailbox-rules/tenants/{id}/rules` | mailbox_rules.py | Tenant mailbox rules |
| GET `/api/v1/mailbox-rules/tenants/{id}/suspicious` | mailbox_rules.py | Suspicious rules |
| GET `/api/v1/mailbox-rules/alerts` | mailbox_rules.py | Mailbox rule alerts |
| POST `/api/v1/mailbox-rules/alerts/{id}/acknowledge` | mailbox_rules.py | Acknowledge alert |
| GET `/api/v1/mailbox-rules/tenants/{id}/summary` | mailbox_rules.py | Rules summary |
| PUT `/api/v1/alerts/rules/{id}` | alerts.py | PUT update rule (docs only mention POST/GET/DELETE) |
| PATCH `/api/v1/alerts/rules/{id}` | alerts.py | PATCH update rule |
| DELETE `/api/v1/alerts/webhooks/{id}` | alerts.py | Delete webhook |
| GET `/api/v1/alerts/rules/{id}` | alerts.py | Get specific rule |
| GET `/api/v1/dashboard/summary` | dashboard.py | Dashboard summary |
| GET `/api/v1/dashboard/login-timeline` | dashboard.py | Login activity timeline |
| GET `/api/v1/dashboard/geo-heatmap` | dashboard.py | Geo heatmap data |
| GET `/api/v1/dashboard/successful-login-locations` | dashboard.py | Successful login locations |
| GET `/api/v1/dashboard/anomaly-trend` | dashboard.py | Anomaly trend data |
| GET `/api/v1/dashboard/top-risk-users` | dashboard.py | Top risk users |
| GET `/api/v1/dashboard/alert-volume` | dashboard.py | Alert volume data |
| GET `/api/v1/dashboard/anomaly-breakdown` | dashboard.py | Anomaly type breakdown |
| GET `/api/v1/dashboard/full` | dashboard.py | All dashboard data in one request |
| POST `/api/v1/dashboard/export` | dashboard.py | Export dashboard data |
| GET `/api/v1/dashboard/export/download/{format}` | dashboard.py | Download export |
| GET `/api/v1/dlp/` | dlp.py | DLP events (undocumented, replaces claimed `insider-threat` routes) |
| GET `/api/v1/dlp/stats` | dlp.py | DLP statistics |
| GET `/api/v1/diagnostics/summary` | diagnostics.py | Data ingestion diagnostics |
| GET `/api/v1/diagnostics/audit-logs` | diagnostics.py | Recent audit logs |
| GET `/api/v1/diagnostics/login-analytics` | diagnostics.py | Recent login analytics |
| GET `/api/v1/health/` | health.py | Detailed health (separate from `/health`) |
| GET/POST/PATCH/DELETE `/api/v1/settings/*` | settings.py | Full settings CRUD (system, preferences, detection, API keys, webhook test, config import/export) |
| GET/POST/PATCH/DELETE `/api/v1/users/*` | users.py | User management CRUD (list, create, update, tenant assignment) |
| GET `/api/v1/mailbox-security/events` | mailbox.py | Mailbox rule events |
| GET `/api/v1/mailbox-security/access` | mailbox.py | Non-owner mailbox access |
| GET `/api/v1/mailbox-security/stats` | mailbox.py | Mailbox security stats |
| GET `/api/v1/sharepoint/debug` | sharepoint.py | Debug endpoint (should be removed in production) |
| GET `/api/v1/sharepoint/sharing-links` | sharepoint.py | Active sharing links |
| GET `/api/v1/monitoring/websites/*` | monitoring/websites.py | Website monitoring CRUD |
| GET `/api/v1/monitoring/ssl/*` | monitoring/ssl.py | SSL certificate monitoring |
| GET `/api/v1/monitoring/domains/*` | monitoring/domains.py | Domain monitoring |
| POST `/api/v1/endpoints/generate-token` | endpoints.py | Generate enrollment token |
| GET `/api/v1/endpoints/devices/{id}/events` | endpoints.py | Device-specific events |
| GET `/api/v1/endpoints/summary` | endpoints.py | Endpoint summary stats |

### Inaccuracies
- ARCHITECTURE.md §5.1 lists `POST /api/v1/auth/local/login` — correct but docs don't mention `GET /api/v1/auth/local/check`
- WebSocket path: docs say `WS /api/v1/ws/ws/alerts` — code implements this with double `/ws/ws` due to router prefix nesting. This is technically correct but awkward.

---

## 5. Services Layer (src/services/*.py)

### Docs Claim
ARCHITECTURE.md §3.1 lists services: tenant, encryption, mfa_report, ca_policies, oauth_apps, mailbox_rules, sharepoint, insider_threat, endpoints, dashboard, alert_processor, alert_stream, settings.

### Code Actually Implements
All of the above plus additional services:
- `credential_manager.py` — Credential management (undocumented)
- `enhanced_encryption.py` — Enhanced encryption service (undocumented)
- `k8s_secrets_storage.py` — K8s secrets storage service (undocumented)
- `monitoring/domain.py`, `monitoring/ssl.py`, `monitoring/website.py` — Monitoring services (undocumented)

### Gaps
- ARCHITECTURE.md mentions "Insider Threat Service" but there's no `src/services/insider_threat.py`. Instead, insider threat logic lives in `src/analytics/insider_threat.py`. The service layer pattern is inconsistent here.

### Undocumented Features
- `credential_manager.py`, `enhanced_encryption.py`, `k8s_secrets_storage.py` — three service files with no documentation
- Entire monitoring service suite (domain, SSL, website monitoring)

### Inaccuracies
- ARCHITECTURE.md shows `src/services/sharepoint.py` but the actual SharePoint service is at `src/analytics/sharepoint.py`. There is no `src/services/sharepoint.py`.

---

## 6. Clients Layer (src/clients/*.py)

### Docs Claim
ARCHITECTURE.md §3.1 lists: ms_graph.py, mfa_report.py, ca_policies.py, oauth_apps.py, mailbox_rules.py, sharepoint.py, endpoints.py

### Code Actually Implements
- `ms_graph.py` ✅
- `mfa_report.py` ✅
- `ca_policies.py` ✅
- `oauth_apps.py` ✅
- `mailbox_rules.py` ✅
- `__init__.py` ✅

### Gaps
- **`src/clients/sharepoint.py`** — listed in docs but **does not exist**. SharePoint queries are done via the O365 Management API in the collector, not via a dedicated Graph client.
- **`src/clients/endpoints.py`** — listed in docs but **does not exist**. Endpoint events come from the C# agent posting to the API; there's no Graph client for endpoints.

---

## 7. Models Layer (src/models/*.py)

### Docs Claim
ARCHITECTURE.md §3.1 lists: db.py, user.py, tenant.py, alerts.py, analytics.py, sharepoint.py, endpoint.py, mfa_report.py, ca_policies.py, oauth_apps.py, mailbox_rules.py, audit_log.py

### Code Actually Implements
All of the above plus:
- `dlp.py` — DLP event model (undocumented)
- `mailbox.py` — Mailbox security models (undocumented, separate from mailbox_rules.py)
- `monitoring.py` — Website/SSL/domain monitoring models (undocumented)
- `settings.py` — Settings models (undocumented)
- `dashboard.py` — Dashboard data models (undocumented)
- `types.py` — Custom SQLAlchemy types (undocumented)

### Gaps
- None — all documented models exist.

### Undocumented Features
- 6 additional model files not mentioned in docs (dlp.py, mailbox.py, monitoring.py, settings.py, dashboard.py, types.py)

---

## 8. Alerting System (src/alerts/*.py)

### Docs Claim
- Alert engine with rules, deduplication, cooldown logic
- Discord webhook client
- Slack webhook support mentioned in ARCHITECTURE.md and 1-PAGER

### Code Actually Implements
- `engine.py` — Alert processing engine with rule matching, dedup hash, cooldown ✅
- `rules.py` — Alert rule CRUD service ✅
- `discord.py` — Discord webhook client ✅
- `WebhookType` enum includes `SLACK` value in models/alerts.py

### Gaps
- **Slack webhook support**: `WebhookType.SLACK` exists as an enum value, but `src/alerts/discord.py` only implements Discord formatting. There is **no Slack webhook client**. The architecture diagram claims "Slack Webhooks" as an external integration, but no code sends to Slack.

### Undocumented Features
- None.

### Inaccuracies
- ARCHITECTURE.md §2.3 lists "Slack Webhooks" as a supported integration — **not implemented**. Only Discord is supported.
- 1-PAGER says "Slack, or Discord" — Slack is not implemented.

---

## 9. Analytics (src/analytics/*.py)

### Docs Claim
ARCHITECTURE.md §3.1 lists: anomalies.py, logins.py, failed_logins.py, sharepoint.py, insider_threat.py, threat_intel.py, geo_ip.py

### Code Actually Implements
- `anomalies.py` ✅
- `logins.py` ✅
- `failed_logins.py` ✅
- `sharepoint.py` ✅
- `insider_threat.py` ✅
- `threat_intel.py` ✅
- `geo_ip.py` ✅

### Gaps
- None — all documented analytics files exist.

### Undocumented Features
- None.

### Inaccuracies
- None.

---

## 10. Collector (src/collector/*.py)

### Docs Claim
- `main.py` — Collector entry point
- `o365_feed.py` — O365 audit log ingestion
- `security_scans.py` — Periodic security scans

### Code Actually Implements
- `main.py` ✅ — Full collector with O365 Management API, processes signins, SharePoint, DLP, mailbox, and general audit logs
- `o365_feed.py` ✅ — O365 Management Activity API client
- `security_scans.py` ✅ — Runs MFA, CA, OAuth, and mailbox rule scans
- `monitoring.py` — **Undocumented**: monitoring collector for website/SSL/domain checks
- `__init__.py` ✅

### Gaps
- None for documented features.

### Undocumented Features
- `monitoring.py` — monitoring data collector, not mentioned in any doc

### Inaccuracies
- cronjob-processing-flows.md mentions DLP processing as part of the collector — this is accurate and confirmed in code (main.py calls `insider_service.process_dlp_events`).

---

## 11. Frontend (frontend/src/)

### Docs Claim
ARCHITECTURE.md §6.2 lists pages: Dashboard, Login, Tenants, LoginAnalytics, Anomalies, MapPage, AlertFeed, Settings.

### Code Actually Implements
Pages in `frontend/src/pages/`:
- Dashboard.tsx ✅
- Login.tsx ✅
- Tenants.tsx ✅
- LoginAnalytics.tsx ✅
- Anomalies.tsx ✅
- MapPage.tsx ✅
- AlertFeed.tsx ✅
- Settings.tsx ✅
- **CAPolicies.tsx** — undocumented in page list
- **MailboxRules.tsx** — undocumented
- **MFAReport.tsx** — undocumented
- **OAuthApps.tsx** — undocumented
- **Monitoring.tsx** — undocumented
- **SharePoint.tsx** — undocumented
- **InsiderThreat.tsx** — undocumented
- **MailboxSecurity.tsx** — undocumented
- **Endpoints.tsx** — undocumented
- **Users.tsx** — undocumented

### Gaps
- None — all documented pages exist.

### Undocumented Features
- **10 additional pages** not listed in ARCHITECTURE.md: CAPolicies, MailboxRules, MFAReport, OAuthApps, Monitoring, SharePoint, InsiderThreat, MailboxSecurity, Endpoints, Users
- App.tsx routing confirms all these pages are wired up

### Inaccuracies
- ARCHITECTURE.md §6.2 is significantly out of date — it lists only 8 pages but 18 exist.

### Components
- ARCHITECTURE.md lists: Layout, ProtectedRoute, Sidebar, Header, StatCard, AlertCard, Map/
- Code has these plus many more: AlertFeed, AnomalyCard, ChangePasswordDialog, charts/ (5 chart components), FilterPanel, LoginMap, LoginTimeline, MobileAlertCard, MobileNav, Navigation, PageHeader, StatsCard, settings/ (7 settings components)

### Hooks
- ARCHITECTURE.md lists: useAuth, useWebSocket, useTenants
- Code has: useAuth ✅, useWebSocket ✅, **useApi** (not useTenants), **useDashboard**, **useOffline**, **useSettings**
- **GAP**: `useTenants.ts` listed in docs does not exist. Tenant data is fetched via `useApi.ts`.

### Store
- ARCHITECTURE.md shows Zustand store with `isAuthenticated`, `theme`, `user`
- Code has: `theme`, `sidebarOpen`, `user`, `token`, `isAuthenticated` — uses `persist` middleware
- **Inaccuracy**: docs show `theme` default as `'dark'` but code defaults to `'light'`

---

## 12. Endpoint Agent (agent/SpecterAgent/)

### Docs Claim
ENDPOINT-AGENT.md claims:
- .NET 8.0
- Process creation monitoring (Event 4688)
- PowerShell script block logging (Event 4104)
- Heartbeat every 5 minutes
- SQLite local buffering
- Enrollment via `--enrollment-token` and `--backend-url` CLI flags
- `EventLogWatcher` class for event subscription

ARCHITECTURE.md also claims:
- System Channel (7045) for new service installations
- Batch of 50 events every 30 seconds
- Events deleted after 200 OK response

### Code Actually Implements
- Program.cs: .NET 8.0, Windows Service, CLI args for enrollment ✅
- EventMonitorService.cs: EventLogWatcher for Security (4688) and PowerShell (4104) ✅
- HeartbeatService.cs: heartbeat reporting ✅
- TelemetryUploader.cs: telemetry upload with SQLite buffering ✅
- EnrollmentService.cs: enrollment flow ✅
- DatabaseContext.cs: SQLite EF Core context ✅
- Models: AgentConfig, EndpointEvent ✅

### Gaps
- **Event ID 7045 (Service Installation)**: ARCHITECTURE.md claims the agent watches for new service installations via System Channel (7045). **Code only subscribes to Security (4688) and PowerShell (4104)**. No System channel watcher exists.
- **Batch of 50 events every 30 seconds**: The TelemetryUploader may have different batching logic — the specific "50 events / 30 seconds" claim needs verification against TelemetryUploader.cs (the doc gives specific numbers that may not match code constants).

### Undocumented Features
- `IsSuspicious()` method checks for LOLBins: `-enc`, `iex`, `downloadstring`, `certutil`, `curl` — detection logic not detailed in docs

### Inaccuracies
- ARCHITECTURE.md §3.8 claims "System Channel (7045): Detects new service installations" — **not implemented**. Only 4688 and 4104 are watched.

---

## 13. Kubernetes Deployment (k8s/)

### Docs Claim
- ARCHITECTURE.md §7: Helm chart deployment, HPA, PodDisruptionBudget, topology spread constraints, NetworkPolicy, Traefik ingress
- SECURE-DEPLOYMENT.md: detailed Helm-based deployment with production-values.yaml
- README: `kubectl apply -f k8s/prod/`

### Code Actually Implements
- `k8s/prod/` directory with raw YAML manifests: namespace, deployment, frontend, ingress, collector-cronjob, security-cronjob, marketing
- `k8s/cronjob-monitoring.yaml`
- **No Helm chart exists** — there is no `helm/` directory

### Gaps
- **Helm chart does not exist**: SECURE-DEPLOYMENT.md and ARCHITECTURE.md both reference `helm upgrade --install specterdefence ./helm/specterdefence` but there is no Helm chart in the repository.
- **No HPA** (Horizontal Pod Autoscaler) manifests
- **No PodDisruptionBudget** manifests
- **No NetworkPolicy** manifests
- **No topology spread constraints** in the actual deployment YAML
- **No Pod Security Standards** labels on namespace
- The k8s deployment uses a single replica (replicas: 1), while docs claim 3 replicas with autoscaling

### Undocumented Features
- `k8s/prod/marketing.yaml` — marketing site deployment, not mentioned in docs
- `k8s/cronjob-monitoring.yaml` — monitoring cronjob, not mentioned in docs

### Inaccuracies
- SECURE-DEPLOYMENT.md describes a sophisticated Helm-based deployment with extensive values.yaml. The actual deployment uses simple raw YAML with 1 replica, no HPA, no PDB, no network policies.
- ARCHITECTURE.md shows "API Pod(s) with HPA: 2-10 replicas" — actual deployment has `replicas: 1` with no HPA.
- README claims `kubectl apply -f k8s/prod/` for deployment — this works but is much simpler than the Helm-based approach documented elsewhere.

---

## 14. CI/CD (.github/workflows/)

### Docs Claim
README mentions: Black, Ruff, MyPy, Bandit, Hadolint, ESLint pre-commit hooks

### Code Actually Implements
- `backend.yml` — lint (Ruff, Black, MyPy), tests, Docker build/push to GHCR, deploy to k8s via Tailscale
- `frontend.yml` — frontend build/test
- `agent.yml` — C# agent build
- `marketing.yml` — marketing site build
- `.github/dependabot.yml` — dependency updates

### Gaps
- **Bandit** security scanning: listed in README pre-commit hooks but **not in any CI workflow**
- **Hadolint**: listed in README but **not in any CI workflow**
- **ESLint**: listed in README for frontend linting, not verified in this audit but no workflow file shows it

### Undocumented Features
- `dependabot.yml` — automated dependency updates, not mentioned in docs
- `marketing.yml` workflow — marketing site CI/CD, not mentioned

### Inaccuracies
- README claims pre-commit hooks for Bandit and Hadolint — no evidence of these in CI/CD workflows.

---

## 15. Tests (tests/)

### Docs Claim
README mentions `pytest` with coverage. ARCHITECTURE.md §1.1 references test suites.

### Code Actually Implements
- `tests/unit/` — comprehensive unit tests:
  - `alerts/` — test_discord, test_engine, test_models, test_processor, test_processor_extended, test_rules
  - `analytics/` — test_anomalies, test_geo_ip, test_logins
  - `api/` — test_alerts, test_api_ca_policies, test_api_dashboard, test_api_mailbox_rules, test_api_oauth_apps, test_mfa_report, test_settings, test_websocket
  - `clients/` — test_ca_policies, test_client_mailbox_rules, test_mfa_report, test_ms_graph, test_o365, test_oauth_apps
  - `collector/` — test_main, test_o365_feed, test_utils
  - `services/` — test_ca_policies, test_dashboard, test_mfa_report, test_oauth_apps, test_service_mailbox_rules
  - Root: test_anomalies, test_encryption, test_health_check, test_main, test_ms_graph, test_tenant_api, test_tenant_service
- `tests/integration/` — test_api_flows, test_end_to_end, test_log_collection
- `tests/factories.py`, `tests/conftest.py`

### Gaps
- No tests for: `src/api/endpoints.py`, `src/api/dlp.py`, `src/api/mailbox.py`, `src/api/sharepoint.py`, `src/api/diagnostics.py`, `src/api/users.py`, `src/api/monitoring/*`
- No tests for: `src/services/credential_manager.py`, `src/services/enhanced_encryption.py`, `src/services/k8s_secrets_storage.py`, `src/services/monitoring/*`
- No tests for: `src/collector/monitoring.py`
- No tests for: `src/analytics/insider_threat.py`, `src/analytics/sharepoint.py`, `src/analytics/failed_logins.py`

### Undocumented Features
- Test infrastructure is more extensive than docs suggest (factories, fixtures, integration tests)

---

## 16. Marketing Site (marketing/)

### Docs Claim
Not documented in any doc file.

### Code Actually Implements
- Full React + Vite marketing site with: Hero, Features, DashboardPreview, EndpointAgent, MultiTenant, Pricing, Navbar, Footer components
- Deployed via `k8s/prod/marketing.yaml`
- CI/CD via `.github/workflows/marketing.yml`

### Gaps
- Completely undocumented in all doc files.

### Undocumented Features
- Entire marketing site is undocumented.

---

## 17. AI Integration (docs/ai-proposal.md)

### Docs Claim
- Phase 1: Alert triage, security briefings, anomaly explanation, AI-suggested rules
- Phase 2: Remediation playbooks, assisted remediation
- `KIMI_API_KEY` config field exists
- "Alert pipeline supports metadata enrichment"
- "Frontend 'AI Analyst' UI components in development"

### Code Actually Implements
- `KIMI_API_KEY` exists in config.py (default: `""`) — **but is never used anywhere in the codebase**
- No `src/ai/` directory exists
- No AI-related service, client, or model files exist
- No frontend AI-related components exist
- Alert metadata enrichment IS implemented (alerts carry `alert_metadata` dict)

### Gaps
- **All AI features are entirely unimplemented**. The proposal describes a two-phase plan but nothing has been built:
  - No `src/ai/` module
  - No LLM client abstraction
  - No alert correlation service
  - No AI briefing generator
  - No AI Insights frontend panel
  - No playbook engine
- The "Current Status (v1.1.0)" section claims "LLM Webhook (In Progress)" — no code evidence of this

### Inaccuracies
- ai-proposal.md says "Frontend 'AI Analyst' UI components in development" — no such components exist in the frontend code
- ai-proposal.md says "Alert pipeline supports metadata enrichment" — this is partially true (metadata dict exists) but no AI enrichment occurs
- The version "v1.1.0" in ai-proposal.md doesn't match the actual app version "0.1.0" in main.py/config.py

---

## 18. Security & Encryption

### Docs Claim
- Fernet encryption (AES-128-CBC with HMAC-SHA256) with PBKDF2 key derivation
- 600,000 iterations for SHA256
- Encrypted fields: tenant client_secret, webhook URLs

### Code Actually Implements
- `src/services/encryption.py` — exactly as documented: PBKDF2HMAC with SHA256, 600,000 iterations, Fernet
- Encrypts `TenantModel.client_secret` and `AlertWebhookModel.webhook_url`
- `src/services/enhanced_encryption.py` — additional encryption service (undocumented)

### Gaps
- None for documented features.

### Undocumented Features
- `enhanced_encryption.py` — second encryption service not documented
- `k8s_secrets_storage.py` — K8s secrets storage service not documented
- `credential_manager.py` — credential management service not documented

---

## 19. Monitoring Module (Undocumented)

### Docs Claim
ai-proposal.md mentions "Domain, SSL, and website uptime checks" as an existing capability in a table, but no other doc describes this module.

### Code Actually Implements
- `src/api/monitoring/` — full monitoring API: websites, SSL certificates, domains
- `src/services/monitoring/` — monitoring services: domain, SSL, website
- `src/models/monitoring.py` — database models for WebsiteMonitor, SSLCertificate, DomainMonitor
- `src/collector/monitoring.py` — monitoring data collection
- `frontend/src/pages/Monitoring.tsx` — monitoring dashboard page
- `frontend/src/services/monitoring.ts` — frontend monitoring API client

### Gaps
- **Entire monitoring module is undocumented** in ARCHITECTURE.md, README, and 1-PAGER. It's only briefly mentioned in a table in ai-proposal.md.

### Undocumented Features
- Complete website availability monitoring with uptime tracking
- SSL certificate expiration monitoring
- Domain registration monitoring
- All API endpoints, services, models, frontend page, and collector for this module

---

## 20. SharePoint Revocation

### Docs Claim
ARCHITECTURE.md §5.8: `POST /api/v1/sharepoint/revoke/{id}` — "Revoke a sharing link"

### Code Actually Implements
- `src/api/sharepoint.py` has: `/metrics`, `/debug`, `/sharing-links`
- **No revoke endpoint exists**

### Gaps
- **SharePoint link revocation is not implemented** — claimed in docs but no endpoint exists.

---

## 21. Config-Code Mismatches

### IPAPI_API_KEY
- README claims `IPAPI_API_KEY` can be set for ip-api.com pro version
- **Not in config.py**, not referenced in geo_ip.py
- The GeoIPClient uses only the free tier URL with no API key parameter

### O365_CLIENT_SECRET
- README lists this as an optional secret
- **Not in config.py** — tenant secrets are per-tenant in the database

### ENCRYPTION_SALT
- ARCHITECTURE.md §7.3 lists this as required
- config.py has it with default `""` — not actually required at code level (encryption.py derives salt from SECRET_KEY if not provided)

### Redis
- ARCHITECTURE.md §2.1 diagram shows "Redis (Caching)" as part of the data layer
- **No Redis configuration, no Redis client, no Redis usage anywhere in the codebase**
- FULL-DOCUMENTATION.md §3.1 also claims "Uses Redis for stateful caching and rate-limiting"

---

## Summary of Major Findings

### Critical Gaps (docs claim features that don't exist):
1. **No Helm chart** — SECURE-DEPLOYMENT.md and ARCHITECTURE.md describe Helm-based deployment; actual repo uses raw YAML
2. **No Slack integration** — claimed in architecture diagram and 1-PAGER; only Discord is implemented
3. **No AI features** — ai-proposal.md describes AI capabilities as "in progress"; nothing is implemented
4. **No IPAPI_API_KEY support** — README claims pro version support; not in config or code
5. **No SharePoint revoke** — API endpoint claimed but not implemented
6. **No Insider Threat API routes** — docs claim `/api/v1/insider-threat/*`; actual routes are `/api/v1/dlp/*`
7. **No Redis** — architecture diagram shows Redis; no Redis in codebase
8. **No Event 7045 monitoring** — agent docs claim System channel monitoring; only 4688 and 4104 are implemented
9. **No HPA/PDB/NetworkPolicy** — deployment docs claim autoscaling and network policies; raw YAML has none

### Major Undocumented Features:
1. **Monitoring module** — complete website/SSL/domain monitoring (API, services, models, frontend, collector)
2. **Diagnostics API** — data ingestion diagnostics endpoints
3. **Users API** — user CRUD with tenant assignment
4. **Mailbox Security API** — separate from mailbox rules, includes non-owner access tracking
5. **Settings API** — extensive settings CRUD with detection thresholds, API keys, config import/export
6. **10 additional frontend pages** — CAPolicies, MailboxRules, MFAReport, OAuthApps, Monitoring, SharePoint, InsiderThreat, MailboxSecurity, Endpoints, Users
7. **Marketing site** — complete marketing website with CI/CD and k8s deployment
8. **Dashboard export** — CSV/JSON export functionality
9. **CA Policy baselines** — security baseline configuration per tenant
10. **MFA exemptions** — per-user MFA exemption with expiration

### Notable Inaccuracies:
1. Frontend pages list in ARCHITECTURE.md is 10 pages short (8 listed, 18 exist)
2. `useTenants.ts` hook listed in docs doesn't exist (it's `useApi.ts`)
3. Zustand store default theme is `'light'`, not `'dark'` as documented
4. `src/services/sharepoint.py` listed in docs but actual location is `src/analytics/sharepoint.py`
5. `src/clients/sharepoint.py` and `src/clients/endpoints.py` listed in docs don't exist
6. K8s deployment uses Traefik ingress (not Nginx as SECURE-DEPLOYMENT.md suggests)
7. App version is 0.1.0, not v1.1.0 as ai-proposal.md claims

---

*End of Audit Report*