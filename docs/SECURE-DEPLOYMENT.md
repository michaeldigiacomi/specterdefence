# SpecterDefence Secure Deployment Guide

> Note: The current k8s manifests use raw YAML with a single replica and Traefik ingress. The deployment can be enhanced with HPA, PDB, and Network Policies as described in the recommendations below.

This guide provides step-by-step instructions for securely deploying SpecterDefence to production.

---

## Prerequisites

- Kubernetes cluster (1.24+) with kubectl configured
- Access to a secrets management system (HashiCorp Vault, AWS Secrets Manager, or manual)
- Domain name with DNS configured
- TLS certificate (Let's Encrypt recommended)
- Traefik ingress controller installed on the cluster

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
          class: traefik
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

### 3.1 Apply the Raw YAML Manifests

The repository contains raw Kubernetes YAML manifests in `k8s/prod/`. These include:

- `namespace.yaml` — Namespace definition
- `deployment.yaml` — Backend API deployment (1 replica) and Service
- `frontend.yaml` — Frontend deployment (1 replica) and Service
- `ingress.yaml` — Traefik ingress rules for app and marketing site
- `collector-cronjob.yaml` — CronJob running the data collector every 5 minutes
- `security-cronjob.yaml` — CronJob running security scans every 4 hours
- `marketing.yaml` — Marketing site deployment and Service

```bash
# Deploy all manifests
cd /path/to/specterdefence
kubectl apply -f k8s/prod/

# Verify deployment
kubectl get pods -n specterdefence
kubectl get ingress -n specterdefence
kubectl get cronjobs -n specterdefence
```

### 3.2 Verify the Deployment

```bash
# Check backend pod status
kubectl get pods -n specterdefence -l app.kubernetes.io/component=backend

# Check frontend pod status
kubectl get pods -n specterdefence -l app.kubernetes.io/component=frontend

# Check ingress routes
kubectl get ingress -n specterdefence

# Check cronjobs
kubectl get cronjobs -n specterdefence
```

---

## Step 4: Post-Deployment Verification

### 4.1 Verify Security Headers

```bash
curl -I https://app.specterdefence.digitaladrenalin.net
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
openssl s_client -connect app.specterdefence.digitaladrenalin.net:443 -servername app.specterdefence.digitaladrenalin.net </dev/null | openssl x509 -text

# Test SSL rating (requires ssllabs-scan or similar)
# ssllabs-scan app.specterdefence.digitaladrenalin.net
```

### 4.3 Verify Secrets Are Not Exposed

```bash
# Check environment variables don't contain secrets
kubectl exec -n specterdefence deployment/specterdefence-backend -- env | grep -i secret

# Should return nothing or masked values
```

### 4.4 Test Authentication

```bash
# Test with default password (should fail)
curl -X POST https://app.specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Should return 401

# Test with correct password
curl -X POST https://app.specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}"

# Should return token
```

### 4.5 Verify Rate Limiting

```bash
# Test rate limiting on login endpoint
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://app.specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
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
          sum(rate(http_requests_total{service="specterdefence-backend",status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="specterdefence-backend"}[5m]))
        ) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate on SpecterDefence API"

    - alert: SpecterDefenceUnauthenticatedAccess
      expr: increase(http_requests_total{service="specterdefence-backend",status="401"}[5m]) > 10
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
kubectl scale deployment specterdefence-backend -n specterdefence --replicas=0

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

kubectl scale deployment specterdefence-backend -n specterdefence --replicas=1

# 6. Verify
kubectl rollout status deployment specterdefence-backend -n specterdefence
```

---

## Recommendations for Production Hardening

The current manifests provide a functional deployment. For a production-grade setup, consider adding the following:

### Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: specterdefence-backend-hpa
  namespace: specterdefence
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: specterdefence-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

### Pod Disruption Budget (PDB)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: specterdefence-backend-pdb
  namespace: specterdefence
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: specterdefence
      app.kubernetes.io/component: backend
```

### Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: specterdefence-backend-netpol
  namespace: specterdefence
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: specterdefence
      app.kubernetes.io/component: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: ingress-nginx
  egress:
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: postgresql
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53
```

### Pod Security Standards

```bash
kubectl label namespace specterdefence \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### Topology Spread Constraints

Add to the deployment pod spec:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app.kubernetes.io/component: backend
```

---

## Troubleshooting

### Secret Validation Failures

```bash
# Verify secret exists
kubectl get secret specterdefence-secrets -n specterdefence

# Check pod events
kubectl describe pod -n specterdefence -l app.kubernetes.io/component=backend
```

### TLS Certificate Issues

```bash
# Check certificate status
kubectl describe certificate specterdefence-tls -n specterdefence

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

### Traefik Ingress Issues

```bash
# Check Traefik ingress controller
kubectl get pods -n traefik

# Check ingress resources
kubectl describe ingress -n specterdefence
```

---

## Security Contacts

- Security Issues: security@digitaladrenalin.net
- Emergency Response: +1-XXX-XXX-XXXX
- On-call Rotation: See PagerDuty

---

*Last Updated: 2026-08-28*