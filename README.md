# SpecterDefence

[![CI](https://github.com/bluedigiacomi/specterdefence/actions/workflows/ci.yml/badge.svg)](https://github.com/bluedigiacomi/specterdefence/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)

> Microsoft 365 security posture monitoring and management platform

![Dashboard](/docs/Dashboard.png)

## Overview

SpecterDefence provides automated security monitoring, alerting, and remediation for Microsoft 365 environments. It continuously monitors tenant configurations, security policies, and threat indicators to ensure your organization maintains a strong security posture.

## Features

- 🔐 **Multi-Tenant Management** - Register and manage multiple Office 365 tenants
- 📊 **Security Posture Monitoring** - Continuous assessment of security configurations
- 🚨 **Threat Detection** - Real-time security alerts and incident response
- 📈 **Compliance Reporting** - Track compliance against security frameworks
- 🔧 **Automated Remediation** - Auto-fix common security misconfigurations

## Architecture

```
specterdefence/
├── src/                # Backend API (FastAPI)
│   ├── api/           # Routes and endpoints
│   ├── alerts/        # Alert processing logic
│   ├── analytics/     # Security analytics
│   ├── clients/       # Microsoft Graph API client
│   ├── collector/     # Data collection services
│   ├── models/        # Pydantic data models
│   ├── services/      # Business logic layer
│   └── config.py      # Application configuration
├── frontend/           # React frontend (Vite/Tailwind)
├── tests/              # Test suites
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── k8s/               # Kubernetes deployment manifests
└── docs/              # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional)
- Microsoft 365 tenant with admin access

### Local Development

```bash
# Clone the repository
git clone https://github.com/bluedigiacomi/specterdefence.git
cd specterdefence

# Install dependencies with Poetry
poetry install

# Run the application
poetry run uvicorn src.main:app --reload
```

### Docker

```bash
# Build and run with Docker
docker build -t specterdefence .
docker run -p 8000:8000 specterdefence

# Or use docker-compose
docker-compose up -d
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
SECRET_KEY=your-secret-key-here

# Optional
DEBUG=false
HOST=0.0.0.0
PORT=8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/specterdefence
```

## API Documentation

Once running, access the interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

```bash
# Run linting
ruff check .
black --check .
mypy src/

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

Hooks configured:
- **Black** - Code formatting
- **Ruff** - Linting and import sorting
- **MyPy** - Type checking
- **Bandit** - Security scanning
- **Hadolint** - Dockerfile linting
- **ESLint** - Frontend linting

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured for your cluster

### Deployment (Production)

The application is deployed at:
- **URL**: http://specterdefence.digitaladrenalin.net
- **Cluster**: k3s @ k3s.digitaladrenalin.net (57.129.132.176)

#### Quick Deploy

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (refer to Secret Management section)
# Standard deployment
kubectl apply -f k8s/prod/
```

### Secret Management

SpecterDefence requires sensitive configuration (database credentials, encryption keys, OAuth secrets) to be provided securely.

#### Option 1: Manual Secret Creation (Recommended for Production)

Create secrets manually before deploying:

```bash
# Generate secure values
export SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export ADMIN_PASSWORD_HASH=$(python3 -c "from src.api.auth_local import get_password_hash; print(get_password_hash('your-password'))")

# Create the Kubernetes secret
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:password@postgres:5432/specterdefence" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=ADMIN_PASSWORD_HASH="$ADMIN_PASSWORD_HASH" \
  --from-literal=ABUSEIPDB_API_KEY="your-key" \
  --from-literal=ALIENVAULT_OTX_API_KEY="your-key"
```

### Required Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `SECRET_KEY` | Application secret for sessions/CSRF protection | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `ENCRYPTION_KEY` | Fernet key for encrypting tenant credentials | Yes |
| `ADMIN_PASSWORD_HASH` | Bcrypt hash for the local admin user | Yes |
| `ABUSEIPDB_API_KEY` | IP reputation check API key | Optional |
| `ALIENVAULT_OTX_API_KEY` | Threat intelligence feed API key | Optional |
| `O365_CLIENT_SECRET` | Microsoft Graph API client secret | Optional |

### IP Lookup Service

The IP lookup feature uses [ip-api.com](https://ip-api.com) for geographic IP lookups (used for login country detection and per-tenant approved countries feature).

- **Free tier**: 45 requests/minute, no API key required
- **Pro version**: Higher rate limits and commercial use requires an API key

To use the pro version for higher rate limits in production, set the `IPAPI_API_KEY` secret:

```bash
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=IPAPI_API_KEY="your-ipapi-api-key"
  # ... other secrets
```

Then update the Helm chart to use the API key by setting `env.IPAPI_API_KEY` or adding it to the secrets.

### Security Documentation

- [Kubernetes Security Best Practices](./docs/k8s-security.md) - Comprehensive security hardening guide
- [Secret Rotation Guide](./docs/secret-rotation.md) - Procedures for rotating credentials

### Deployment with Ingress

```bash
kubectl apply -f k8s/prod/ingress.yaml
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

For security concerns, please email security@digitaladrenalin.net
