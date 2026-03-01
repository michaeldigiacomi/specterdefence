# SpecterDefence Helm Chart

A production-ready Helm chart for deploying SpecterDefence M365 Security Platform on Kubernetes.

## Features

- 🚀 **Separate API and Frontend deployments** with independent scaling
- 🔒 **Multiple secret management strategies** (Existing Secret, External Secrets Operator, Helm-managed)
- 📊 **Horizontal Pod Autoscaling** with configurable behavior
- 🛡️ **Network Policies** for pod-to-pod security
- 🔍 **Health checks and readiness probes** for all components
- 📈 **Prometheus monitoring** with ServiceMonitor and alerting rules
- 🗄️ **PostgreSQL and Redis** as optional subchart dependencies
- 🔄 **Pod Disruption Budgets** for high availability
- 🌍 **Environment-specific configurations** (dev/staging/prod)

## Prerequisites

- Kubernetes 1.24+
- Helm 3.12+
- kubectl configured for your cluster
- (Optional) cert-manager for TLS certificates
- (Optional) Prometheus Operator for monitoring
- (Optional) External Secrets Operator for cloud-native secret management

## Quick Start

### 1. Create Namespace

```bash
kubectl create namespace specterdefence
```

### 2. Create Secrets

```bash
# Generate secure values
export SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create the secret
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=DATABASE_URL="postgresql://specterdefence:changeme@specterdefence-postgresql:5432/specterdefence" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=O365_CLIENT_SECRET="your-azure-client-secret"
```

### 3. Install the Chart

```bash
# Add Bitnami repository for dependencies
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install dependencies
helm dependency update ./helm/specterdefence

# Install with development values
helm upgrade --install specterdefence ./helm/specterdefence \
  --namespace specterdefence \
  --values ./helm/specterdefence/values-development.yaml

# Or install with production values
helm upgrade --install specterdefence ./helm/specterdefence \
  --namespace specterdefence \
  --values ./helm/specterdefence/values-production.yaml
```

## Configuration

### Values Files

| File | Purpose |
|------|---------|
| `values.yaml` | Default values for all environments |
| `values-development.yaml` | Development environment overrides |
| `values-production.yaml` | Production environment overrides |

### Key Configuration Sections

#### Global Settings

```yaml
global:
  environment: production
  domain: specterdefence.example.com
  imagePullSecrets: []
```

#### API Server

```yaml
api:
  replicaCount: 3
  image:
    repository: ghcr.io/bluedigiacomi/specterdefence-api
    tag: latest
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
```

#### Frontend

```yaml
frontend:
  replicaCount: 2
  image:
    repository: ghcr.io/bluedigiacomi/specterdefence-frontend
    tag: latest
```

#### Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  tls:
    enabled: true
    secretName: specterdefence-tls
```

#### PostgreSQL (Subchart)

```yaml
postgresql:
  enabled: true
  auth:
    existingSecret: specterdefence-db-credentials
  primary:
    persistence:
      enabled: true
      size: 10Gi
```

#### Redis (Subchart)

```yaml
redis:
  enabled: true
  auth:
    existingSecret: specterdefence-redis-credentials
```

## Secret Management

### Option 1: Existing Secret (Recommended)

Create secrets manually before installing:

```bash
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db" \
  --from-literal=ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

### Option 2: External Secrets Operator

For integration with HashiCorp Vault, AWS Secrets Manager, Azure Key Vault:

```yaml
secrets:
  externalSecrets:
    enabled: true
    secretStore:
      name: vault-backend
      kind: ClusterSecretStore
```

### Option 3: Helm-Managed (Development Only)

⚠️ **WARNING: Not recommended for production!**

```yaml
secrets:
  helmManaged:
    enabled: true
    secretKey: "dev-secret"
    databaseUrl: "sqlite:///./dev.db"
```

## Health Checks

All components include health checks:

- **API Server**: `/health` endpoint
- **Frontend**: Nginx root path
- **PostgreSQL**: Handled by subchart
- **Collector**: Init container validation

## Autoscaling

The API and Frontend support Horizontal Pod Autoscaling:

```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    behavior:
      scaleDown:
        stabilizationWindowSeconds: 300
```

## Monitoring

Enable Prometheus monitoring:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    namespace: monitoring
  prometheusRule:
    enabled: true
    rules:
      - alert: SpecterDefenceHighErrorRate
        expr: ...
```

## Network Policies

Restrict pod-to-pod communication:

```yaml
networkPolicy:
  enabled: true
  ingress:
    allowedNamespaces:
      - ingress-nginx
      - monitoring
```

## Upgrading

```bash
# Update dependencies
helm dependency update ./helm/specterdefence

# Upgrade the release
helm upgrade specterdefence ./helm/specterdefence \
  --namespace specterdefence \
  --values ./helm/specterdefence/values-production.yaml

# Rolling restart to pick up new secrets
kubectl rollout restart deployment/specterdefence-api -n specterdefence
kubectl rollout restart deployment/specterdefence-frontend -n specterdefence
```

## Uninstalling

```bash
helm uninstall specterdefence -n specterdefence

# Optionally remove PVCs (⚠️ data loss)
kubectl delete pvc -l app.kubernetes.io/name=specterdefence -n specterdefence
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n specterdefence
kubectl describe pod -l app.kubernetes.io/component=api -n specterdefence
```

### View Logs

```bash
# API logs
kubectl logs -l app.kubernetes.io/component=api -n specterdefence

# Frontend logs
kubectl logs -l app.kubernetes.io/component=frontend -n specterdefence

# Collector logs
kubectl logs -l app.kubernetes.io/component=collector -n specterdefence
```

### Check Secrets

```bash
kubectl get secrets -n specterdefence
kubectl describe secret specterdefence-secrets -n specterdefence
```

### Validate Configuration

```bash
# Template rendering (dry run)
helm template specterdefence ./helm/specterdefence \
  --values ./helm/specterdefence/values-development.yaml \
  --debug

# Lint the chart
helm lint ./helm/specterdefence
```

## Chart Structure

```
helm/specterdefence/
├── Chart.yaml                  # Chart metadata and dependencies
├── values.yaml                 # Default values
├── values-development.yaml     # Development overrides
├── values-production.yaml      # Production overrides
├── README.md                   # This file
└── templates/
    ├── _helpers.tpl            # Common templates
    ├── configmap.yaml          # Non-sensitive config
    ├── configmap-nginx.yaml    # Nginx configuration
    ├── secrets.yaml            # Secret management
    ├── serviceaccount.yaml     # Service account
    ├── api-deployment.yaml     # API server deployment
    ├── api-service.yaml        # API service
    ├── api-hpa.yaml            # API HPA
    ├── pdb-api.yaml            # API Pod Disruption Budget
    ├── frontend-deployment.yaml # Frontend deployment
    ├── frontend-service.yaml    # Frontend service
    ├── frontend-hpa.yaml       # Frontend HPA
    ├── pdb-frontend.yaml       # Frontend Pod Disruption Budget
    ├── ingress.yaml            # Combined ingress
    ├── cronjob-collector.yaml  # O365 collector CronJob
    ├── networkpolicy.yaml      # Network security
    ├── servicemonitor.yaml     # Prometheus ServiceMonitor
    └── prometheusrules.yaml    # Prometheus alerting rules
```

## Support

For issues and feature requests, please visit:
https://github.com/bluedigiacomi/specterdefence

## License

MIT License
