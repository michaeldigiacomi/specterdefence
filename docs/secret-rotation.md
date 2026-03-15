# Secret Rotation Guide

This guide covers how to safely rotate secrets for SpecterDefence running on Kubernetes.

## Table of Contents

- [Overview](#overview)
- [Supported Secret Types](#supported-secret-types)
- [Rotation Strategies](#rotation-strategies)
- [Step-by-Step Procedures](#step-by-step-procedures)
- [Automated Rotation](#automated-rotation)
- [Troubleshooting](#troubleshooting)

## Overview

SpecterDefence handles sensitive data including:

- **Application Secret Key** - Used for session management and CSRF protection
- **Database Credentials** - Connection strings for PostgreSQL/SQLite
- **Encryption Key** - Fernet key for tenant credential encryption at rest
- **O365 Client Secret** - Microsoft Graph API authentication
- **Tenant OAuth Tokens** - Encrypted refresh tokens for tenant access

Regular rotation of these secrets is a security best practice.

## Supported Secret Types

### 1. Application Secret Key (SECRET_KEY)

**Impact:** Sessions will be invalidated, users will need to re-authenticate.

**Rotation Frequency:** Recommended every 90 days or after security incident.

### 2. Database Credentials (DATABASE_URL)

**Impact:** Application will lose database connectivity during rotation.

**Rotation Frequency:** Recommended every 90 days or per organizational policy.

**Prerequisites:**
- Database user with rotation privileges, OR
- Downtime window for manual credential update

### 3. Encryption Key (ENCRYPTION_KEY)

**Impact:** Existing encrypted data must be re-encrypted.

**Rotation Frequency:** Recommended every 180 days.

**Special Considerations:**
- SpecterDefence supports key versioning for seamless rotation
- Old keys are kept for decryption during transition period
- Automatic re-encryption happens on next tenant credential access

### 4. O365 Client Secret (O365_CLIENT_SECRET)

**Impact:** OAuth flows will fail until new secret is propagated.

**Rotation Frequency:** Per Microsoft recommendation (typically 6-24 months).

### 5. Tenant OAuth Tokens

**Impact:** Individual tenant scanning will pause until re-authentication.

**Rotation Frequency:** Triggered by Microsoft token expiry or security incident.

## Rotation Strategies

### Strategy 1: Zero-Downtime Rotation (Recommended)

Uses Kubernetes secret versioning and rolling updates:

```
1. Create new secret version
2. Update deployment to reference new secret
3. Rolling restart of pods
4. Verify new pods are healthy
5. Remove old secret version
```

### Strategy 2: Blue-Green Rotation

For critical production environments:

```
1. Deploy new "green" environment with rotated secrets
2. Verify green environment health
3. Switch traffic to green environment
4. Decommission "blue" environment
```

### Strategy 3: Maintenance Window Rotation

For simpler setups:

```
1. Schedule maintenance window
2. Scale deployment to 0 replicas
3. Rotate secrets
4. Scale deployment back up
5. Verify functionality
```

## Step-by-Step Procedures

### Rotating Application Secret Key

```bash
# 1. Generate a new secret key
NEW_SECRET_KEY=$(openssl rand -hex 32)

# 2. Create new secret version
kubectl create secret generic specterdefence-secrets-new \
  --from-literal=SECRET_KEY="$NEW_SECRET_KEY" \
  --from-literal=DATABASE_URL="$(kubectl get secret specterdefence-secrets -o jsonpath='{.data.DATABASE_URL}' | base64 -d)" \
  --from-literal=ENCRYPTION_KEY="$(kubectl get secret specterdefence-secrets -o jsonpath='{.data.ENCRYPTION_KEY}' | base64 -d)"

# 3. Update deployment to use new secret
kubectl patch deployment specterdefence -p '{"spec":{"template":{"spec":{"containers":[{"name":"specterdefence","env":[{"name":"SECRET_KEY","valueFrom":{"secretKeyRef":{"name":"specterdefence-secrets-new","key":"SECRET_KEY"}}}]}]}}}}'

# 4. Wait for rollout
kubectl rollout status deployment/specterdefence

# 5. Verify application is healthy
kubectl get pods -l app.kubernetes.io/name=specterdefence

# 6. Replace old secret and update references
kubectl delete secret specterdefence-secrets
kubectl create secret generic specterdefence-secrets --from-env-file=<(kubectl get secret specterdefence-secrets-new -o json | jq -r '.data | to_entries[] | "\(.key)=\(.value | @base64d)"')
kubectl delete secret specterdefence-secrets-new

# 7. Rolling restart to use original secret name
kubectl rollout restart deployment/specterdefence
```

### Rotating Database Credentials

**For PostgreSQL with a superuser:**

```bash
# 1. Create new database user (run against your database)
psql -c "CREATE USER specterdefence_new WITH PASSWORD 'new-secure-password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE specterdefence TO specterdefence_new;"

# 2. Build new connection string
NEW_DATABASE_URL="postgresql://specterdefence_new:new-secure-password@postgres:5432/specterdefence"

# 3. Update secret
kubectl patch secret specterdefence-secrets --type='json' -p='[{"op": "replace", "path": "/data/DATABASE_URL", "value":"'$(echo -n "$NEW_DATABASE_URL" | base64)'"}]'

# 4. Rolling restart
kubectl rollout restart deployment/specterdefence

# 5. Verify connectivity
kubectl logs -l app.kubernetes.io/name=specterdefence --tail=20

# 6. Remove old database user (after confirming all pods use new secret)
psql -c "REASSIGN OWNED BY specterdefence_old TO specterdefence_new;"
psql -c "DROP USER specterdefence_old;"
```

### Rotating Encryption Key

```bash
# 1. Generate new Fernet key
NEW_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Add new key to secret (keeping old key for decryption)
# SpecterDefence supports multiple keys separated by commas
OLD_KEY=$(kubectl get secret specterdefence-secrets -o jsonpath='{.data.ENCRYPTION_KEY}' | base64 -d)
COMBINED_KEYS="$NEW_ENCRYPTION_KEY,$OLD_KEY"

kubectl patch secret specterdefence-secrets --type='json' -p='[{"op": "replace", "path": "/data/ENCRYPTION_KEY", "value":"'$(echo -n "$COMBINED_KEYS" | base64)'"}]'

# 3. Rolling restart
kubectl rollout restart deployment/specterdefence

# 4. Trigger re-encryption of all tenant credentials
# This happens automatically when credentials are next accessed,
# or you can force it via the API:
curl -X POST http://specterdefence/api/v1/admin/reencrypt-credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 5. After confirming all data is re-encrypted, remove old key
kubectl patch secret specterdefence-secrets --type='json' -p='[{"op": "replace", "path": "/data/ENCRYPTION_KEY", "value":"'$(echo -n "$NEW_ENCRYPTION_KEY" | base64)'"}]'
```

### Rotating O365 Client Secret

```bash
# 1. Generate new client secret in Azure AD portal
# Go to: Azure AD > App registrations > Your App > Certificates & secrets

# 2. Get the new secret value
NEW_CLIENT_SECRET="your-new-secret-from-azure"

# 3. Update Kubernetes secret
kubectl patch secret specterdefence-secrets --type='json' -p='[{"op": "replace", "path": "/data/O365_CLIENT_SECRET", "value":"'$(echo -n "$NEW_CLIENT_SECRET" | base64)'"}]'

# 4. Rolling restart
kubectl rollout restart deployment/specterdefence

# 5. Verify Microsoft Graph connectivity
kubectl logs -l app.kubernetes.io/name=specterdefence | grep -i "microsoft\|graph\|oauth"

# 6. Remove old secret from Azure AD (after confirming new one works)
```

## Automated Rotation

### Using External Secrets Operator

If using External Secrets Operator with a secret management backend (HashiCorp Vault, AWS Secrets Manager, etc.), rotation can be fully automated:

```yaml
# ExternalSecret with automatic rotation
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: specterdefence-external
spec:
  refreshInterval: "1h"  # Check for updates every hour
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: specterdefence-secrets
    creationPolicy: Owner
    template:
      type: Opaque
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: specterdefence/secret-key
        version: "latest"
```

With this setup:
1. Rotate secrets in your secret management backend (Vault, AWS SM, etc.)
2. External Secrets Operator automatically syncs to Kubernetes
3. Pods using the secret are automatically restarted

### Using Kubernetes Reloader

Install [Reloader](https://github.com/stakater/Reloader) for automatic pod restarts when secrets change:

```bash
# Install Reloader
kubectl apply -f https://raw.githubusercontent.com/stakater/Reloader/master/deployments/kubernetes/reloader.yaml

# Annotate your deployment
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: specterdefence
  annotations:
    reloader.stakater.com/auto: "true"
spec:
  # ... rest of spec
EOF
```

Now any secret changes will trigger automatic rolling restart.

## Troubleshooting

### Pod fails after secret rotation

```bash
# Check pod events
kubectl describe pod -l app.kubernetes.io/name=specterdefence

# Check init container logs (secret validation)
kubectl logs -l app.kubernetes.io/name=specterdefence -c validate-secrets

# Verify secret exists and has required keys
kubectl get secret specterdefence-secrets -o yaml | yq '.data | keys'
```

### Database connection fails after rotation

```bash
# Check logs for connection errors
kubectl logs -l app.kubernetes.io/name=specterdefence | grep -i "database\|connection\|postgresql"

# Verify DATABASE_URL format
kubectl get secret specterdefence-secrets -o jsonpath='{.data.DATABASE_URL}' | base64 -d

# Test connectivity from within the cluster
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- psql $DATABASE_URL
```

### Encryption/decryption errors

```bash
# Check for encryption key issues
kubectl logs -l app.kubernetes.io/name=specterdefence | grep -i "fernet\|encryption\|decrypt"

# Verify Fernet key format (should be 32-byte base64-encoded)
kubectl get secret specterdefence-secrets -o jsonpath='{.data.ENCRYPTION_KEY}' | base64 -d | wc -c
# Should output: 44 (32 bytes base64-encoded = 44 chars)
```

### Rollback procedure

If rotation causes issues:

```bash
# 1. Scale down to prevent further issues
kubectl scale deployment specterdefence --replicas=0

# 2. Restore previous secret from backup
kubectl apply -f secret-backup-$(date +%Y%m%d).yaml

# 3. Scale back up
kubectl scale deployment specterdefence --replicas=1

# 4. Verify
kubectl get pods -l app.kubernetes.io/name=specterdefence
```

## Security Best Practices

1. **Never commit secrets to Git** - Use external secret management
2. **Rotate after security incidents** - Assume compromise, rotate everything
3. **Use short-lived tokens where possible** - Prefer managed identities
4. **Monitor rotation events** - Alert on failed rotations
5. **Test rotation in staging** - Before production
6. **Keep rotation runbooks updated** - Document your specific procedures
7. **Use RBAC** - Limit who can read/write secrets
8. **Enable audit logging** - Track secret access in Kubernetes

## Related Documentation

- [Kubernetes Security](./k8s-security.md)
- [Helm Deployment Guide](./deployment.md)
- [External Secrets Operator](https://external-secrets.io/)
