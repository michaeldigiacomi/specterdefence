# SpecterDefence Modernization Guide

This document outlines the modernization improvements implemented for the SpecterDefence project.

## Phase 1: Dependency & Framework Updates ✅

### Backend (Python)
- **Python Version**: Bumped from 3.11 to 3.13 for better performance and language features
- **Dependency Management**: Unified on Poetry exclusively (removed requirements.txt)
  - All dependencies now managed through `pyproject.toml`
  - Use `poetry lock` to generate/update `poetry.lock` file
  - CI now uses Poetry for consistent dependency resolution
- **New Dependencies**:
  - `slowapi` (0.1.9): Rate limiting middleware for FastAPI

### Frontend (TypeScript/React)
- **Node LTS**: Updated CI from Node 20 to Node 22 LTS
- **TypeScript**: Bumped from 5.2.2 to 5.6.2 for improved strict mode and error reporting
- **ESLint**: Updated from 8.53.0 to 9.0.0 for latest linting rules
- **TypeScript ESLint**: Updated to 7.0.0 for compatibility with new ESLint
- **Removed Legacy Dependencies**: Eliminated `--legacy-peer-deps` flag from CI (use `npm ci` instead of `npm install`)

### Configuration
- **pyproject.toml**: Added Ruff and MyPy strict configuration
- **Pre-commit hooks**: Updated to latest versions of tools, fixed hardcoded paths

## Phase 2: CI/CD Pipeline Modernization ✅

### Backend CI/CD
- **Lint/Test Enforcement**: Removed `|| echo "..."` error suppression - failures now block commits
- **Python Version**: Updated to 3.13
- **Dependency Caching**: Added pip/Poetry caching in GitHub Actions
- **Security Scanning**: Added `pip-audit` for dependency vulnerability scanning
- **Blocking on Errors**: All linting, type checking, and tests now fail the build if issues occur

### Frontend CI/CD
- **Node Version**: Updated to 22 LTS
- **Lint/Test Enforcement**: Removed error suppression - failures now block commits
- **Npm Audit**: Added `npm audit --audit-level=moderate` to CI pipeline
- **Dependency Management**: Changed from `npm install --legacy-peer-deps` to `npm ci`
- **Type Checking**: Now runs and enforces TypeScript compilation

### Security Scanning Workflow
- **Added `.github/workflows/security.yml`**:
  - CodeQL analysis for Python and JavaScript/TypeScript
  - Bandit security scanning for Python
  - Pip-audit for Python dependencies
  - Npm audit for JavaScript dependencies
  - Runs on push to main, PRs, and daily schedule

### Container Security
- **SLSA Provenance**: Added `provenance: mode=max` to container builds
- **SBOM Generation**: Added `sbom: true` to container builds for supply chain security

## Phase 3: Docker & Deployment ✅

### Dockerfile Consolidation
- **Unified Dockerfile Structure**: Main `Dockerfile` supports multiple build targets:
  - `backend-production`: Backend API only
  - `backend-frontend-production`: Backend + frontend (static files)
  - `backend-development`: Backend with dev dependencies and reload support
  - Default target: `backend-production`
- **Locked Base Images**: Now using specific versions instead of floating tags:
  - Python: `python:3.13.1-slim` (was `3.12-slim`)
  - Node: `node:22.9-alpine` (was `20-slim`)
  - Nginx: `nginx:1.27-alpine` (was `nginx:alpine`)
- **Poetry in Dockerfiles**: All Python builds now use Poetry instead of pip
- **Improved Caching**: Dependency layers separated from code layers

### Individual Dockerfiles
- **Dockerfile.backend**: Updated to use Poetry and Python 3.13
- **Dockerfile.frontend**: Updated to use Node 22 Alpine

### Docker Compose
- **Added `docker-compose.yml`**:
  - PostgreSQL 16.1 with health checks
  - Redis 7.2 for caching
  - Backend API (Python/FastAPI)
  - Frontend dev server (Node/Vite)
  - PgAdmin for database management
  - All services networked and health-checked
  - Volumes for live code reloading
  - Port forwarding configured

### API Versioning
- **Already Implemented**: API routes prefixed with `/api/v1`
- **Future-Proof**: Allows migration to v2 without breaking existing clients

## Phase 4: Security Hardening ✅

### Rate Limiting
- **SlowAPI Integration**: Added to FastAPI for request rate limiting
- **Per-IP Limiting**: Default limiter configured with `get_remote_address`
- **Ready for Customization**: Can add specific rate limit decorators to endpoints

### Container Base Image Locking
- All Dockerfiles now use specific version tags (not `:latest` or `:alpine`)
- Ensures reproducible builds and security updates can be controlled

### Pre-commit Hook Improvements
- Removed hardcoded paths (was `/home/mdigiacomi/.openclaw/workspace/...`)
- Now uses relative paths for ESLint checking
- Updated all tool versions to latest stable

## Phase 5: Developer Experience ✅

### Docker Compose Setup
- **Zero-Config Local Development**: `docker-compose up` starts entire stack
- Services include:
  - PostgreSQL database
  - Redis cache
  - Backend API with hot-reload
  - Frontend dev server with hot-reload
  - PgAdmin for database management

### VS Code Dev Container
- **Added `.devcontainer/devcontainer.json`**:
  - Ubuntu 22.04 base image
  - Python 3.13
  - Node 22
  - Pre-configured VSCode extensions:
    - Python (Pylance, Ruff)
    - Prettier (formatting)
    - ESLint (linting)
    - Makefile tools
  - Port forwarding for all services
  - SSH mount for GitHub credentials

- **Added `.devcontainer/init.sh`**:
  - Automated setup script for dev environment
  - Installs Poetry and dependencies
  - Sets up pre-commit hooks
  - Generates local .env file with secrets
  - Runs on container creation

### Updated Makefile
- All commands now use Poetry:
  - `make install` → `poetry install`
  - `make test` → `poetry run pytest`
  - `make lint` → `poetry run ruff`
  - `make type-check` → `poetry run mypy`
- Added Docker Compose commands:
  - `make docker-compose-up`
  - `make docker-compose-down`
  - `make docker-compose-logs`

## Phase 6: Configuration Updates

### pyproject.toml
```toml
[tool.ruff]
line-length = 120
target-version = "py313"

[tool.mypy]
python_version = "3.13"
strict = true
```

### .pre-commit-config.yaml
- Black: 23.12.0 → 24.10.0
- Ruff: v0.1.9 → v0.8.0
- MyPy: v1.7.1 → v1.14.0
- Fixed ESLint path to use relative directories

## Migration Guide

### For Existing Development

1. **Update Local Environment**:
   ```bash
   poetry install
   poetry run pre-commit install
   cd frontend && npm ci && cd ..
   ```

2. **Start Local Stack**:
   ```bash
   docker-compose up -d
   make run              # Terminal 1: Backend
   cd frontend && npm run dev  # Terminal 2: Frontend
   ```

3. **Or Use Dev Container**:
   ```bash
   # In VS Code, click "Reopen in Container"
   # Will automatically run init.sh and set up everything
   ```

### For CI/CD

- The changes are backward compatible with existing workflows
- All lint/test failures will now properly fail builds
- New security scanning runs automatically on push and PRs
- Container builds now include SBOM and provenance

## Performance Improvements

- Faster CI builds with locked dependency versions
- Better caching in Docker layer
- Python 3.13 performance improvements
- Node 22 performance improvements
- Reduced Docker image sizes with Alpine and distroless where possible

## Security Improvements

- SBOM generation for supply chain security
- SLSA provenance attestation
- CodeQL scanning for vulnerabilities
- Pip-audit and npm audit in CI
- Rate limiting middleware
- Locked base image versions
- Stricter type checking with MyPy strict mode

## Breaking Changes

- **Python 3.13+ required** for local development
- **Node 22 required** for frontend development
- **Requirements.txt removed** - use Poetry exclusively
- **--legacy-peer-deps removed** from CI - resolve peer dependencies properly

## Next Steps (Future Improvements)

1. **Structured Logging**: Add JSON logging with python-json-logger
2. **E2E Testing**: Set up Playwright for critical user flows
3. **Observability**: Add OpenTelemetry instrumentation
4. **Monorepo Tooling**: Consider Turborepo/NX for coordinated builds
5. **Helm/Kustomize**: Migrate Kubernetes manifests for better templating
6. **Documentation**: Add ADRs and runbooks

## References

- [Poetry Documentation](https://python-poetry.org/docs/)
- [FastAPI Rate Limiting](https://fastapi-utils.davidmontague.xyz/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [SLSA Framework](https://slsa.dev/)
- [CodeQL Documentation](https://codeql.github.com/docs/)
