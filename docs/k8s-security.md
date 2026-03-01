# Kubernetes Security Best Practices for SpecterDefence

This guide covers security considerations and best practices for deploying SpecterDefence on Kubernetes.

## Table of Contents

- [Overview](#overview)
- [Secret Management](#secret-management)
- [Pod Security](#pod-security)
- [Network Security](#network-security)
- [Encryption at Rest](#encryption-at-rest)
- [Encryption in Transit](#encryption-in-transit)
- [Access Control](#access-control)
- [Audit Logging](#audit-logging)
- [Security Hardening Checklist](#security-hardening-checklist)

## Overview

SpecterDefence handles sensitive security data including tenant credentials, OAuth tokens, and security configuration data. Proper security measures must be implemented to protect this data in a Kubernetes environment.

## Secret Management

### Recommended Approach: External Secret Management

**DO NOT** use Helm-managed secrets in production. Instead, use one of these approaches:

#### Option 1: Kubernetes Secrets with Manual Management (Simple)

Create secrets manually with `kubectl`:

```bash
# Create secret from command line
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL="postgresql://user:pass@host/db" \
  --from-literal=ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

#### Option 2: External Secrets Operator (Recommended)

Use [External Secrets Operator](https://external-secrets.io/) to sync secrets from external providers:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: specterdefence-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: specterdefence-secrets
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: secret/data/specterdefence
        property: secret_key
```

Supported backends:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- GCP Secret Manager
- GitLab CI/CD Variables
- And more...

#### Option 3: Sealed Secrets (GitOps-friendly)

Use [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) to encrypt secrets for Git storage:

```bash
# Install kubeseal CLI
# Create secret and seal it
kubectl create secret generic specterdefence-secrets \
  --from-literal=SECRET_KEY=xxx --dry-run=client -o yaml | \
  kubeseal --controller-namespace=kube-system --controller-name=sealed-secrets --format yaml > sealed-secret.yaml

# Apply sealed secret (safe to commit to Git)
kubectl apply -f sealed-secret.yaml
```

### Secret Access Patterns

#### Use environment variables for configuration

```yaml
env:
  - name: SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: specterdefence-secrets
        key: SECRET_KEY
```

#### Use volume mounts for files

```yaml
volumeMounts:
  - name: tls-certs
    mountPath: /app/certs
    readOnly: true

volumes:
  - name: tls-certs
    secret:
      secretName: specterdefence-tls
      defaultMode: 0400
```

### Secret RBAC

Limit who can access secrets:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: specterdefence-secret-reader
  namespace: specterdefence
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["specterdefence-secrets"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: specterdefence-secret-binding
  namespace: specterdefence
subjects:
  - kind: ServiceAccount
    name: specterdefence
    namespace: specterdefence
roleRef:
  kind: Role
  name: specterdefence-secret-reader
  apiGroup: rbac.authorization.k8s.io
```

## Pod Security

### Security Context

SpecterDefence Helm chart includes hardened security context:

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  fsGroupChangePolicy: "OnRootMismatch"
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
  runAsNonRoot: true
  runAsUser: 1000
  seccompProfile:
    type: RuntimeDefault
```

### Pod Security Standards

Apply Pod Security Standards:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: specterdefence
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Network Policies

Restrict pod-to-pod communication:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: specterdefence-network-policy
  namespace: specterdefence
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: specterdefence
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow ingress from ingress controller only
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  egress:
    # Allow DNS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
    # Allow database access
    - to:
        - podSelector:
            matchLabels:
              app: postgresql
      ports:
        - protocol: TCP
          port: 5432
    # Allow external HTTPS (Microsoft Graph API)
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
```

## Network Security

### Ingress Configuration

Use TLS termination at ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: specterdefence
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - specterdefence.example.com
      secretName: specterdefence-tls
  rules:
    - host: specterdefence.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: specterdefence
                port:
                  number: 8000
```

### Service Mesh (Optional)

For enhanced security, deploy with a service mesh like Istio:

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: specterdefence-mtls
  namespace: specterdefence
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: specterdefence
  mtls:
    mode: STRICT
```

## Encryption at Rest

### Kubernetes Secrets Encryption

Enable etcd encryption for secrets at the cluster level:

```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
spec:
  containers:
    - command:
        - kube-apiserver
        - --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
```

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

### Tenant Credential Encryption

SpecterDefence encrypts tenant OAuth credentials using Fernet symmetric encryption:

- **Encryption Key:** Stored in Kubernetes Secret as `ENCRYPTION_KEY`
- **Algorithm:** Fernet (AES-128-CBC + HMAC-SHA256)
- **Key Rotation:** Supports multiple keys for seamless rotation

```python
# Fernet key format (generated by application)
from cryptography.fernet import Fernet
key = Fernet.generate_key()  # 32-byte base64-encoded
```

### Database Encryption

For PostgreSQL, enable encryption:

```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create encrypted column for sensitive data
CREATE TABLE tenant_credentials (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    encrypted_data BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Encryption in Transit

### Service-to-Service mTLS

With Istio or Linkerd:

```yaml
apiVersion: security.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: specterdefence-mtls
spec:
  host: specterdefence.specterdefence.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

### Database TLS

Configure PostgreSQL with TLS:

```bash
# In values.yaml
secrets:
  existingSecret:
    enabled: true
    name: specterdefence-secrets

# Database URL with TLS
DATABASE_URL="postgresql://user:pass@postgres:5432/db?sslmode=require"
```

### External API TLS

All Microsoft Graph API calls use HTTPS with certificate verification:

```python
# Application ensures TLS verification
import httpx
async with httpx.AsyncClient(verify=True) as client:
    response = await client.get("https://graph.microsoft.com/v1.0/...")
```

## Access Control

### Kubernetes RBAC

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: specterdefence-role
  namespace: specterdefence
rules:
  # Allow reading own config
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["specterdefence-config"]
    verbs: ["get", "list"]
  # Allow reading own secrets
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["specterdefence-secrets", "specterdefence-tenant-credentials"]
    verbs: ["get"]
  # Allow updating tenant credentials
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["specterdefence-tenant-credentials"]
    verbs: ["get", "update", "patch"]
```

### Service Account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: specterdefence
  namespace: specterdefence
  annotations:
    # Disable automount if not needed
    # (SpecterDefence doesn't need K8s API access by default)
automountServiceAccountToken: false
```

### Pod Security Admission

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: specterdefence
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Audit Logging

### Kubernetes Audit Policy

```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Log secret access
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["secrets"]
    namespaces: ["specterdefence"]
  
  # Log pod creation/deletion
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["pods"]
    namespaces: ["specterdefence"]
  
  # Log RBAC changes
  - level: RequestResponse
    resources:
      - group: rbac.authorization.k8s.io
        resources: ["roles", "rolebindings"]
```

### Application Audit Logging

SpecterDefence logs security events:

```python
# Security event logging
{
    "timestamp": "2024-01-15T10:30:00Z",
    "event_type": "tenant_authenticated",
    "tenant_id": "xxx",
    "user": "admin@example.com",
    "ip_address": "10.0.0.1",
    "success": true
}
```

## Security Hardening Checklist

### Pre-Deployment

- [ ] Enable etcd encryption for secrets
- [ ] Configure Pod Security Standards (restricted)
- [ ] Set up Network Policies
- [ ] Enable audit logging
- [ ] Use non-root container user
- [ ] Configure resource limits
- [ ] Set up external secret management
- [ ] Enable TLS for all ingress
- [ ] Configure liveness/readiness probes

### Secrets

- [ ] Never commit secrets to Git
- [ ] Use external secret management (Vault, AWS SM, etc.)
- [ ] Enable automatic secret rotation
- [ ] Use separate secrets per environment
- [ ] Limit secret access with RBAC
- [ ] Encrypt tenant credentials at rest

### Pod Security

- [ ] Run as non-root user (UID 1000)
- [ ] Read-only root filesystem
- [ ] Drop all capabilities
- [ ] No privilege escalation
- [ ] Seccomp profile enabled
- [ ] Security contexts defined

### Network

- [ ] TLS 1.2+ for all external connections
- [ ] mTLS for service-to-service (optional)
- [ ] Network policies restrict traffic
- [ ] Ingress uses valid certificates
- [ ] No direct pod-to-internet access (use egress rules)

### Monitoring

- [ ] Enable Kubernetes audit logging
- [ ] Log all secret access attempts
- [ ] Monitor for privilege escalation
- [ ] Alert on failed authentication
- [ ] Track security policy violations

## Compliance Notes

### SOC 2 Requirements

- Encryption at rest and in transit ✓
- Access logging and monitoring ✓
- Regular secret rotation ✓
- Least privilege access ✓

### GDPR Considerations

- Tenant data encrypted at rest ✓
- Audit trail of data access ✓
- Right to erasure (tenant deletion) ✓

## Related Documentation

- [Secret Rotation Guide](./secret-rotation.md)
- [Helm Deployment Guide](./deployment.md)
- [Architecture Overview](./architecture.md)
