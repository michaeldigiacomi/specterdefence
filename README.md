# SpecterDefence

[![Backend CI/CD](https://github.com/michaeldigiacomi/specterdefence/actions/workflows/backend.yml/badge.svg)](https://github.com/michaeldigiacomi/specterdefence/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)

> Microsoft 365 security posture monitoring and management platform

![Dashboard](/docs/Dashboard.png)

## Overview

SpecterDefence continuously monitors Microsoft 365 tenants for security drift and threats: MFA compliance, Conditional Access policy changes, risky OAuth apps, suspicious mailbox rules, login anomalies (impossible travel, brute force, unapproved countries), SharePoint/DLP exposure, and Windows endpoint events. Alerts stream to the dashboard over WebSocket and to Discord webhooks, with rule-based deduplication.

## Features

- **Multi-tenant management** — register and monitor multiple M365 tenants
- **Security posture scans** — MFA enrollment/strength, CA policy drift, OAuth app risk, mailbox rules
- **Login anomaly detection** — impossible travel, new country/IP, brute force, malicious IP (AbuseIPDB/OTX), per-tenant approved countries
- **Insider threat & DLP** — SharePoint sharing and DLP event monitoring
- **Windows endpoint agent** — process creation (4688) and PowerShell script-block (4104) telemetry with local SQLite buffering
- **Website/SSL/domain monitoring** — availability, certificate expiry, domain registration
- **Real-time alerts** — WebSocket feed + Discord webhooks with cooldown deduplication

## Stack

- **Backend** — Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL/SQLite, MSAL → Graph API, O365 Management Activity API collector
- **Frontend** — React 18 + TypeScript + Vite, Tailwind, TanStack Query, Zustand
- **Agent** — C# / .NET 8 Windows service (`agent/SpecterAgent`)
- **Deploy** — Docker images, raw Kubernetes manifests in `k8s/prod/` (Traefik ingress + CronJobs)

## Repository layout

```
src/            # FastAPI backend (api/, services/, clients/, models/, alerts/, analytics/, collector/)
frontend/       # React dashboard (see frontend/README.md)
agent/          # Windows endpoint agent (see docs/ENDPOINT-AGENT.md)
k8s/            # Kubernetes manifests (see k8s/README.md)
marketing/      # Static marketing site
mcp_server/     # MCP server for AI agent access (see docs/MCP.md)
tests/          # unit/ and integration/ pytest suites
docs/           # Architecture, deployment, and permission guides
```

## Quick start

### Local development

```bash
git clone https://github.com/michaeldigiacomi/specterdefence.git
cd specterdefence
poetry install
cp frontend/.env.example frontend/.env   # for frontend, if needed
poetry run uvicorn src.main:app --reload
```

The API listens on `http://localhost:8000` with Swagger UI at `/docs`. For the frontend, `cd frontend && npm install && npm run dev` (dev server on port 3000; the Vite proxy target is configured in `frontend/vite.config.ts`).

### Docker

```bash
docker build -t specterdefence-backend -f Dockerfile.backend .
docker build -t specterdefence-frontend -f frontend/Dockerfile frontend/
```

## Configuration

Configuration is read from environment variables (see `src/config.py`). Minimum required for a dev run:

```bash
SECRET_KEY=                # 64-hex: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=            # same generation method
ADMIN_PASSWORD_HASH=       # bcrypt: python -c "from src.api.auth_local import get_password_hash; print(get_password_hash('pw'))"
ENCRYPTION_KEY=            # Fernet: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_SALT=           # openssl rand -hex 16
DATABASE_URL=sqlite:///./specterdefence.db
```

Optional: `ABUSEIPDB_API_KEY`, `ALIENVAULT_OTX_API_KEY` (threat intel), `CORS_ORIGINS`, `COLLECTION_*` tuning vars for the collector. Login geo-lookups use the free [ip-api.com](https://ip-api.com) tier (45 req/min, no key).

## Tests and quality

```bash
make test          # pytest with coverage (source: src/)
make lint          # ruff
make format-check  # black
make type-check    # mypy
make validate      # full suite before committing
pre-commit install # black, ruff, mypy, bandit, eslint, hadolint hooks
```

## Kubernetes deployment

Deploy with `kubectl apply -f k8s/prod/` after creating the `specterdefence` namespace and a `specterdefence-secrets` secret. See [k8s/README.md](k8s/README.md) for the manifest breakdown and [docs/SECURE-DEPLOYMENT.md](docs/SECURE-DEPLOYMENT.md) for the full production checklist, secret generation commands, and rotation notes ([docs/secret-rotation.md](docs/secret-rotation.md)).

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, components, detection logic, API map
- [docs/SECURE-DEPLOYMENT.md](docs/SECURE-DEPLOYMENT.md) — production deployment guide
- [docs/OFFICE365-PERMISSIONS.md](docs/OFFICE365-PERMISSIONS.md) — required tenant app permissions
- [docs/ENDPOINT-AGENT.md](docs/ENDPOINT-AGENT.md) — Windows agent build/install guide
- [docs/cronjob-processing-flows.md](docs/cronjob-processing-flows.md) — collector/scan pipeline diagrams
- [docs/MCP.md](docs/MCP.md) — MCP server setup for AI agent access

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open an issue or PR; CI runs on push to `main` (`.github/workflows/`).

## License / Security

MIT — see [LICENSE](LICENSE). Report vulnerabilities to security@digitaladrenalin.net.
