# SpecterDefence Helm Chart

This Helm chart deploys SpecterDefence on a Kubernetes cluster with comprehensive secret management support.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.12+
- kubectl configured for your cluster

## Secret Management

SpecterDefence supports three secret management strategies. **Choose one based on your security requirements:**

### Option 1: Existing Secret (Recommended for Production)

Create secrets manually before installing the chart:

```bash
# Generate secure values
export SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create the secret
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=DATABASE_URL="postgresql://user:password@postgres:5432/specterdefence" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=O365_CLIENT_SECRET="your-azure-client-secret"

# Verify the secret
kubectl get secret specterdefence-secrets -o jsonpath='{.data}' | jq
```

Install with existing secret:

```bash
helm upgrade --install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set secrets.existingSecret.enabled=true \
  --set secrets.existingSecret.name=specterdefence-secrets
```

### Option 2: External Secrets Operator (Cloud-Native)

For integration with HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, etc.

Prerequisites:
- [External Secrets Operator](https://external-secrets.io/) installed in your cluster

```bash
helm upgrade --install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set secrets.externalSecrets.enabled=true \
  --set secrets.externalSecrets.secretStore.name=vault-backend \
  --set secrets.externalSecrets.secretStore.kind=ClusterSecretStore
```

Required secrets in your external store:
- `specterdefence/secret-key` → SECRET_KEY
- `specterdefence/database` → DATABASE_URL
- `specterdefence/encryption` → ENCRYPTION_KEY
- `specterdefence/oauth` → O365_CLIENT_SECRET

### Option 3: Helm-Managed Secrets (Development Only)

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

## Installing the Chart

### Basic Installation

```bash
helm install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace
```

### With Ingress

```bash
helm install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set 'ingress.hosts[0].host=specterdefence.example.com' \
  --set 'ingress.hosts[0].paths[0].path=/' \
  --set 'ingress.hosts[0].paths[0].pathType=Prefix'
```

### With External Secrets

```bash
helm install specterdefence ./helm \
  --namespace specterdefence \
  --create-namespace \
  --set secrets.externalSecrets.enabled=true \
  --set secrets.externalSecrets.secretStore.name=aws-secrets-manager \
  --set secrets.externalSecrets.secretStore.kind=ClusterSecretStore
```

## Configuration

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `specterdefence` |
| `image.tag` | Image tag | `Chart.AppVersion` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### Secret Management Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.existingSecret.enabled` | Use existing secret | `true` |
| `secrets.existingSecret.name` | Name of existing secret | `specterdefence-secrets` |
| `secrets.externalSecrets.enabled` | Use External Secrets Operator | `false` |
| `secrets.externalSecrets.secretStore.name` | SecretStore/ClusterSecretStore name | `vault-backend` |
| `secrets.externalSecrets.secretStore.kind` | SecretStore kind | `SecretStore` |
| `secrets.externalSecrets.refreshInterval` | Sync interval | `1h` |
| `secrets.helmManaged.enabled` | Let Helm manage secrets | `false` |
| `secrets.validation.enabled` | Enable secret validation | `true` |
| `secrets.validation.initContainer.enabled` | Use init container for validation | `true` |

### Service Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `""` |
| `ingress.annotations` | Ingress annotations | `{}` |
| `ingress.hosts` | Ingress hosts | `[]` |
| `ingress.tls` | TLS configuration | `[]` |

### Security Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `podSecurityContext.runAsNonRoot` | Run as non-root | `true` |
| `podSecurityContext.runAsUser` | User ID | `1000` |
| `securityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `securityContext.readOnlyRootFilesystem` | Read-only root filesystem | `true` |
| `securityContext.capabilities.drop` | Capabilities to drop | `["ALL"]` |

### Resource Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `128Mi` |

## Required Secrets

The application requires the following secrets to be available:

| Secret Key | Description | Required |
|------------|-------------|----------|
| `SECRET_KEY` | Application secret for sessions/CSRF | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `ENCRYPTION_KEY` | Fernet key for credential encryption | Yes |
| `O365_CLIENT_SECRET` | Microsoft Graph API client secret | Optional |

### Generating Secrets

```bash
# SECRET_KEY (64 hex characters)
openssl rand -hex 32

# ENCRYPTION_KEY (Fernet format - base64-encoded 32-byte key)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Validation

The Helm chart includes an init container that validates secrets exist before the application starts:

```bash
# Check validation logs
kubectl logs -l app.kubernetes.io/name=specterdefence -c validate-secrets

# Expected output:
# 🔐 Validating SpecterDefence secrets...
# ✓ Secret specterdefence-secrets exists
# ✓ Key SECRET_KEY exists
# ✓ Key DATABASE_URL exists
# ✓ Key ENCRYPTION_KEY exists
# ✅ All secrets validated successfully!
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade specterdefence ./helm \
  --namespace specterdefence \
  --set image.tag=1.2.3

# Rolling restart to pick up new secrets
kubectl rollout restart deployment/specterdefence -n specterdefence
```

## Uninstalling

```bash
helm uninstall specterdefence -n specterdefence

# Optionally remove secrets
kubectl delete secret specterdefence-secrets -n specterdefence
kubectl delete secret specterdefence-tenant-credentials -n specterdefence
```

## Security Considerations

1. **Never use Helm-managed secrets in production** - Secrets are visible in Helm release values
2. **Use External Secrets Operator for production** - Integrates with enterprise secret management
3. **Enable secret rotation** - See [Secret Rotation Guide](../docs/secret-rotation.md)
4. **Enable encryption at rest** - Configure etcd encryption for your cluster
5. **Use Network Policies** - Restrict pod-to-pod communication
6. **Enable audit logging** - Track secret access

See [Kubernetes Security Best Practices](../docs/k8s-security.md) for detailed security configuration.

## Troubleshooting

### Pod fails to start with "Secret not found"

```bash
# Check if secret exists
kubectl get secrets -n specterdefence

# Create missing secret
kubectl create secret generic specterdefence-secrets \
  -n specterdefence \
  --from-literal=SECRET_KEY=xxx \
  --from-literal=DATABASE_URL=xxx \
  --from-literal=ENCRYPTION_KEY=xxx

# Restart deployment
kubectl rollout restart deployment/specterdefence -n specterdefence
```

### ExternalSecret not syncing

```bash
# Check ExternalSecret status
kubectl describe externalsecret specterdefence-external -n specterdefence

# Check External Secrets Operator logs
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets
```

### Secret validation fails

```bash
# Check init container logs
kubectl logs -l app.kubernetes.io/name=specterdefence -c validate-secrets

# Verify secret contents
kubectl get secret specterdefence-secrets -o jsonpath='{.data}' -n specterdefence | jq
```

## Development

### Testing the Chart

```bash
# Lint the chart
helm lint ./helm

# Template rendering (dry run)
helm template specterdefence ./helm \
  --set secrets.helmManaged.enabled=true \
  --debug

# Install in dry-run mode
helm install specterdefence ./helm \
  --dry-run \
  --debug
```

### Local Testing with Kind/Minikube

```bash
# Create secret
kubectl create secret generic specterdefence-secrets \
  --from-literal=SECRET_KEY=dev-secret \
  --from-literal=DATABASE_URL=sqlite:///./dev.db \
  --from-literal=ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# Install chart
helm install specterdefence ./helm \
  --set secrets.existingSecret.enabled=true

# Port forward
kubectl port-forward svc/specterdefence 8000:8000
```
