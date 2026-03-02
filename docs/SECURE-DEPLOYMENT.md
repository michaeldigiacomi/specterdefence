# SpecterDefence Secure Deployment Guide

This guide provides step-by-step instructions for securely deploying SpecterDefence to production.

---

## Prerequisites

- Kubernetes cluster (1.24+) with kubectl configured
- Helm 3.12+ installed
- Access to a secrets management system (HashiCorp Vault, AWS Secrets Manager, or manual)
- Domain name with DNS configured
- TLS certificate (Let's Encrypt recommended)

---

## Step 1: Pre-Deployment Security Setup

### 1.1 Generate Secure Secrets

Create a secure environment for secret generation:

```bash
# Create a secure working directory
mkdir -p ~/specterdefence-secrets
cd ~/specterdefence-secrets

# Generate SECRET_KEY (256-bit)
export SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY: $SECRET_KEY"

# Generate ENCRYPTION_KEY (Fernet key)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "ENCRYPTION_KEY: $ENCRYPTION_KEY"

# Generate ENCRYPTION_SALT
export ENCRYPTION_SALT=$(openssl rand -hex 16)
echo "ENCRYPTION_SALT: $ENCRYPTION_SALT"

# Generate secure admin password
ADMIN_PASSWORD=$(openssl rand -base64 24)
echo "Admin Password: $ADMIN_PASSWORD"

# Generate password hash (run from specterdefence directory)
cd /path/to/specterdefence
source venv/bin/activate
export ADMIN_PASSWORD_HASH=$(python -c "from src.api.auth_local import get_password_hash; print(get_password_hash('$ADMIN_PASSWORD'))")
echo "ADMIN_PASSWORD_HASH: $ADMIN_PASSWORD_HASH"

# Generate PostgreSQL credentials
export POSTGRES_PASSWORD=$(openssl rand -base64 24)
export POSTGRES_USER=specterdefence
export POSTGRES_DB=specterdefence
```

⚠️ **WARNING:** Store these values securely in a password manager. They cannot be recovered if lost.

---

### 1.2 Create Kubernetes Namespace

```bash
# Create namespace
kubectl create namespace specterdefence

# Label namespace for pod security standards
kubectl label namespace specterdefence \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

---

### 1.3 Create Secrets

#### Option A: Manual Secret Creation (Recommended for single-cluster)

```bash
# Create main application secrets
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=ENCRYPTION_SALT="$ENCRYPTION_SALT" \
  --from-literal=DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}" \
  --from-literal=ADMIN_PASSWORD_HASH="$ADMIN_PASSWORD_HASH"

# Create PostgreSQL secrets
kubectl create secret generic specterdefence-db-credentials \
  --namespace specterdefence \
  --from-literal=postgres-password="$(openssl rand -base64 24)" \
  --from-literal=password="$POSTGRES_PASSWORD"

# Verify secrets (keys only, not values)
kubectl get secret specterdefence-secrets -n specterdefence -o jsonpath='{.data}' | jq -r 'keys[]'
```

#### Option B: External Secrets Operator (Cloud-native)

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: specterdefence-secrets
  namespace: specterdefence
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: specterdefence-secrets
    creationPolicy: Owner
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: specterdefence/production/secret-key
    - secretKey: ENCRYPTION_KEY
      remoteRef:
        key: specterdefence/production/encryption-key
    - secretKey: DATABASE_URL
      remoteRef:
        key: specterdefence/production/database-url
```

```bash
kubectl apply -f external-secret.yaml
```

---

## Step 2: TLS Certificate Setup

### 2.1 Using Let's Encrypt with cert-manager

```bash
# Install cert-manager if not present
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=available --timeout=120s deployment/cert-manager -n cert-manager

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: security@digitaladrenalin.net
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 2.2 Using Existing Certificate

```bash
# Create TLS secret from existing certificates
kubectl create secret tls specterdefence-tls \
  --namespace specterdefence \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key
```

---

## Step 3: Deploy SpecterDefence

### 3.1 Create Production Values File

Create `production-values.yaml`:

```yaml
# production-values.yaml
global:
  environment: production
  domain: specterdefence.digitaladrenalin.net

api:
  replicaCount: 3
  
  image:
    repository: ghcr.io/bluedigiacomi/specterdefence-api
    pullPolicy: IfNotPresent
    tag: "stable"
  
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi
  
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60
    targetMemoryUtilizationPercentage: 75
  
  podDisruptionBudget:
    enabled: true
    minAvailable: 2
  
  config:
    debug: "false"
    logLevel: "info"
    corsOrigins: "https://specterdefence.digitaladrenalin.net"
  
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  
  containerSecurityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop:
        - ALL
    seccompProfile:
      type: RuntimeDefault
  
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: ScheduleAnyway
      labelSelector:
        matchLabels:
          app.kubernetes.io/component: api

frontend:
  replicaCount: 3
  
  image:
    repository: ghcr.io/bluedigiacomi/specterdefence-frontend
    pullPolicy: IfNotPresent
    tag: "stable"
  
  resources:
    limits:
      cpu: 1000m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi
  
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10

ingress:
  enabled: true
  className: nginx
  
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
    nginx.ingress.kubernetes.io/rate-limit: "1000"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/hsts: "true"
    nginx.ingress.kubernetes.io/hsts-max-age: "31536000"
    nginx.ingress.kubernetes.io/hsts-include-subdomains: "true"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      add_header X-Frame-Options "DENY" always;
      add_header X-Content-Type-Options "nosniff" always;
      add_header X-XSS-Protection "1; mode=block" always;
      add_header Referrer-Policy "strict-origin-when-cross-origin" always;
      add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
  
  tls:
    enabled: true
    secretName: specterdefence-tls

secrets:
  existingSecret:
    enabled: true
    name: specterdefence-secrets
  validation:
    enabled: true

networkPolicy:
  enabled: true
  ingress:
    allowedNamespaces:
      - ingress-nginx
  egress:
    enabled: true
    allowDNS: true

serviceAccount:
  create: true
  automountServiceAccountToken: false

podSecurityStandard:
  enforce: "restricted"
  audit: "restricted"
  warn: "restricted"

postgresql:
  enabled: true
  auth:
    existingSecret: specterdefence-db-credentials
  primary:
    persistence:
      enabled: true
      size: 50Gi
    resources:
      limits:
        cpu: 2000m
        memory: 4Gi
      requests:
        cpu: 1000m
        memory: 2Gi
```

### 3.2 Deploy with Helm

```bash
# Add Helm repo (if using)
# helm repo add specterdefence https://charts.specterdefence.io

# Deploy
cd /path/to/specterdefence
helm upgrade --install specterdefence ./helm/specterdefence \
  --namespace specterdefence \
  --values production-values.yaml \
  --wait \
  --timeout 10m

# Verify deployment
kubectl get pods -n specterdefence
kubectl get ingress -n specterdefence
```

---

## Step 4: Post-Deployment Verification

### 4.1 Verify Security Headers

```bash
curl -I https://specterdefence.digitaladrenalin.net
```

Expected headers:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

### 4.2 Verify TLS Configuration

```bash
# Check certificate
openssl s_client -connect specterdefence.digitaladrenalin.net:443 -servername specterdefence.digitaladrenalin.net </dev/null | openssl x509 -text

# Test SSL rating (requires ssllabs-scan or similar)
# ssllabs-scan specterdefence.digitaladrenalin.net
```

### 4.3 Verify Secrets Are Not Exposed

```bash
# Check environment variables don't contain secrets
kubectl exec -n specterdefence deployment/specterdefence-api -- env | grep -i secret

# Should return nothing or masked values
```

### 4.4 Test Authentication

```bash
# Test with default password (should fail)
curl -X POST https://specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Should return 401

# Test with correct password
curl -X POST https://specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}"

# Should return token
```

### 4.5 Verify Rate Limiting

```bash
# Test rate limiting on login endpoint
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrong"}'
done

# Should see 429 responses after limit exceeded
```

---

## Step 5: Monitoring Setup

### 5.1 Enable Prometheus Monitoring

```bash
# Apply ServiceMonitor
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: specterdefence-metrics
  namespace: specterdefence
  labels:
    app: specterdefence
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: specterdefence
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
EOF
```

### 5.2 Set Up Alerting Rules

```bash
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: specterdefence-alerts
  namespace: specterdefence
spec:
  groups:
  - name: specterdefence
    rules:
    - alert: SpecterDefenceHighErrorRate
      expr: |
        (
          sum(rate(http_requests_total{service="specterdefence-api",status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="specterdefence-api"}[5m]))
        ) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate on SpecterDefence API"
        
    - alert: SpecterDefenceUnauthenticatedAccess
      expr: increase(http_requests_total{service="specterdefence-api",status="401"}[5m]) > 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Multiple authentication failures detected"
EOF
```

---

## Step 6: Backup and Disaster Recovery

### 6.1 Database Backup

```bash
# Create backup CronJob
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: specterdefence-db-backup
  namespace: specterdefence
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump \
                --host=postgresql \
                --username=$POSTGRES_USER \
                --dbname=$POSTGRES_DB \
                --format=custom \
                --file=/backup/specterdefence-$(date +%Y%m%d-%H%M%S).dump
            env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: specterdefence-db-credentials
                  key: username
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: specterdefence-db-credentials
                  key: password
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: specterdefence-backups
          restartPolicy: OnFailure
EOF
```

### 6.2 Encryption Key Backup

```bash
# Export and encrypt backup of keys
gpg --symmetric --cipher-algo AES256 --output specterdefence-keys.gpg <<EOF
SECRET_KEY: $SECRET_KEY
ENCRYPTION_KEY: $ENCRYPTION_KEY
ENCRYPTION_SALT: $ENCRYPTION_SALT
EOF

# Store in secure location (e.g., encrypted S3, Vault)
aws s3 cp specterdefence-keys.gpg s3://secure-backup-bucket/specterdefence/
```

---

## Step 7: Secret Rotation

### 7.1 Regular Rotation Schedule

| Secret Type | Rotation Frequency | Process |
|-------------|-------------------|---------|
| JWT_SECRET_KEY | Every 90 days | Rolling rotation with grace period |
| ENCRYPTION_KEY | Every 180 days | Re-encrypt all data |
| Admin Password | Every 90 days | Force password change |
| Database Password | Every 180 days | Rolling update |
| TLS Certificates | Every 90 days (auto) | cert-manager handles |

### 7.2 Emergency Rotation

If secrets are compromised:

```bash
# 1. Scale down application
kubectl scale deployment specterdefence-api -n specterdefence --replicas=0

# 2. Generate new secrets
export NEW_SECRET_KEY=$(openssl rand -hex 32)
export NEW_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 3. Update Kubernetes secrets
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$NEW_SECRET_KEY" \
  --from-literal=ENCRYPTION_KEY="$NEW_ENCRYPTION_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Rotate admin password
export NEW_ADMIN_PASSWORD=$(openssl rand -base64 24)
export NEW_ADMIN_HASH=$(python -c "from src.api.auth_local import get_password_hash; print(get_password_hash('$NEW_ADMIN_PASSWORD'))")

# 5. Update secret and scale up
kubectl patch secret specterdefence-secrets -n specterdefence \
  --type='json' \
  -p='[{"op": "replace", "path": "/data/ADMIN_PASSWORD_HASH", "value":"'$(echo -n "$NEW_ADMIN_HASH" | base64)'"}]'

kubectl scale deployment specterdefence-api -n specterdefence --replicas=3

# 6. Verify
kubectl rollout status deployment/specterdefence-api -n specterdefence
```

---

## Troubleshooting

### Pod Security Standards Violations

```bash
# Check for violations
kubectl get events -n specterdefence --field-selector reason=FailedCreate

# Temporarily relax to debug
kubectl label namespace specterdefence \
  pod-security.kubernetes.io/enforce=baseline --overwrite
```

### Secret Validation Failures

```bash
# Check init container logs
kubectl logs -n specterdefence deployment/specterdefence-api -c validate-secrets

# Verify secret exists
kubectl get secret specterdefence-secrets -n specterdefence
```

### TLS Certificate Issues

```bash
# Check certificate status
kubectl describe certificate specterdefence-tls -n specterdefence

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

---

## Security Contacts

- Security Issues: security@digitaladrenalin.net
- Emergency Response: +1-XXX-XXX-XXXX
- On-call Rotation: See PagerDuty

---

*Last Updated: 2026-03-02*
