# SpecterDefence

[![CI](https://github.com/bluedigiacomi/specterdefence/actions/workflows/ci.yml/badge.svg)](https://github.com/bluedigiacomi/specterdefence/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)

> Microsoft 365 security posture monitoring and management platform

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
├── src/
│   ├── api/           # FastAPI routes and endpoints
│   ├── clients/       # Microsoft Graph API client
│   ├── models/        # Pydantic data models
│   ├── services/      # Business logic layer
│   └── config.py      # Application configuration
├── tests/
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── helm/              # Kubernetes deployment charts
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

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run the application
uvicorn src.main:app --reload
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
DATABASE_URL=sqlite:///./specterdefence.db
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

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- Helm 3.12+
- kubectl configured for your cluster

### Secret Management

SpecterDefence requires sensitive configuration (database credentials, encryption keys, OAuth secrets) to be provided securely. The Helm chart supports multiple secret management strategies.

#### Option 1: Existing Secret (Recommended for Production)

Create secrets manually before installing:

```bash
# Generate secure values
export SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create the Kubernetes secret
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=DATABASE_URL="postgresql://user:password@postgres:5432/specterdefence" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY"

# Deploy using the existing secret
helm upgrade --install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set secrets.existingSecret.enabled=true \
  --set secrets.existingSecret.name=specterdefence-secrets
```

#### Option 2: External Secrets Operator (Cloud-Native)

For integration with HashiCorp Vault, AWS Secrets Manager, Azure Key Vault:

```bash
# Ensure External Secrets Operator is installed in your cluster
# Deploy with external secrets enabled
helm upgrade --install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set secrets.externalSecrets.enabled=true \
  --set secrets.externalSecrets.secretStore.name=vault-backend \
  --set secrets.externalSecrets.secretStore.kind=ClusterSecretStore
```

#### Option 3: Helm-Managed Secrets (Development Only)

⚠️ **WARNING: Not recommended for production!** Secrets will be visible in Helm release values.

```bash
helm upgrade --install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set secrets.helmManaged.enabled=true \
  --set secrets.helmManaged.secretKey="$(openssl rand -hex 32)" \
  --set secrets.helmManaged.databaseUrl="sqlite:///./specterdefence.db" \
  --set secrets.helmManaged.encryptionKey="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

### Required Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `SECRET_KEY` | Application secret for sessions/CSRF protection | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `ENCRYPTION_KEY` | Fernet key for encrypting tenant credentials | Yes |
| `O365_CLIENT_SECRET` | Microsoft Graph API client secret | Optional |

### Security Documentation

- [Kubernetes Security Best Practices](./docs/k8s-security.md) - Comprehensive security hardening guide
- [Secret Rotation Guide](./docs/secret-rotation.md) - Procedures for rotating credentials
- [Helm Chart Documentation](./helm/README.md) - Detailed Helm configuration reference

### Basic Deployment

```bash
# Deploy to Kubernetes
helm upgrade --install specterdefence ./helm/
```

### With Ingress

```bash
helm upgrade --install specterdefence ./helm \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set 'ingress.hosts[0].host=specterdefence.example.com'
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
