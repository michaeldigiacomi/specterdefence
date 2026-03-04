# SpecterDefence Kubernetes Deployment

This directory contains plain Kubernetes YAML manifests for deploying SpecterDefence via ArgoCD.

## Files

| File | Purpose |
|------|---------|
| `namespace.yaml` | Creates the specterdefence namespace |
| `pvc.yaml` | Persistent volume for app data |
| `deployment.yaml` | Main application deployment (2 replicas) |
| `service.yaml` | ClusterIP service |
| `ingress.yaml` | HTTPS ingress with TLS |
| `kustomization.yaml` | Kustomize configuration |

## Prerequisites

### 1. GitHub Container Registry Access

The deployment pulls images from GHCR. You need to create a pull secret:

```bash
# Create a GitHub Personal Access Token with 'read:packages' scope
# https://github.com/settings/tokens

# Create the pull secret in Kubernetes
kubectl create secret docker-registry ghcr-registry-secret \
  --namespace specterdefence \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_TOKEN \
  --docker-email=YOUR_EMAIL
```

### 2. Required Secrets

The following secrets must exist in the `specterdefence` namespace:

**specterdefence-secrets:**
- `SECRET_KEY` - Django/FastAPI secret key
- `DATABASE_URL` - PostgreSQL connection string (with asyncpg)
- `ENCRYPTION_KEY` - Key for encrypting sensitive data
- `KIMI_API_KEY` - Kimi API key
- `ADMIN_PASSWORD_HASH` - Bcrypt hash of admin password

Create with:
```bash
kubectl create secret generic specterdefence-secrets \
  -n specterdefence \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=DATABASE_URL='postgresql+asyncpg://user:pass@host/db?ssl=require' \
  --from-literal=ENCRYPTION_KEY='your-encryption-key' \
  --from-literal=KIMI_API_KEY='your-kimi-key' \
  --from-literal=ADMIN_PASSWORD_HASH='your-bcrypt-hash'
```

### 3. Traefik Middleware (for HTTP→HTTPS redirect)

If not already created:

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: specterdefence-redirect
  namespace: specterdefence
spec:
  redirectScheme:
    scheme: https
    permanent: true
```

## Deployment

### Option 1: Direct kubectl apply
```bash
kubectl apply -k .
```

### Option 2: ArgoCD

The ArgoCD Application is defined in the repo root:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: specterdefence
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/michaeldigiacomi/specterdefence.git
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: specterdefence
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Apply with:
```bash
kubectl apply -f specterdefence-argocd-app.yaml
```

## Image Updates

The deployment uses `imagePullPolicy: Always` and tags images as:
- `latest` - Latest main branch build
- `v1.2.3` - Semantic version tags
- `abc1234` - Short commit SHA

To update the deployment to a specific version:

```bash
# Update image tag
kubectl set image deployment/specterdefence \
  specterdefence=ghcr.io/michaeldigiacomi/specterdefence:v1.2.3 \
  -n specterdefence
```

Or edit `kustomization.yaml`:
```yaml
images:
  - name: ghcr.io/michaeldigiacomi/specterdefence
    newTag: v1.2.3
```

## Scaling

```bash
# Scale to 3 replicas
kubectl scale deployment specterdefence --replicas=3 -n specterdefence

# Or edit deployment.yaml and let ArgoCD sync
```

## Monitoring

The deployment includes:
- Liveness probe on `/health`
- Readiness probe on `/health`
- Prometheus scraping annotations (if needed, add to pod template)

## Troubleshooting

Check pod status:
```bash
kubectl get pods -n specterdefence
kubectl logs -n specterdefence deployment/specterdefence
```

Check events:
```bash
kubectl get events -n specterdefence --sort-by='.lastTimestamp'
```

Verify image pull:
```bash
kubectl describe pod -n specterdefence -l app.kubernetes.io/name=specterdefence
```
