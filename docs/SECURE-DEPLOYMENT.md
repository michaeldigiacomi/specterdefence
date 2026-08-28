# Secure Deployment Guide

Production deployment checklist for Kubernetes. The repo manifests (`k8s/prod/`) provide a working single-replica setup; hardening options are listed at the end.

## Prerequisites

- Kubernetes 1.24+, `kubectl` configured, Traefik ingress controller
- DNS for the app and marketing hosts
- cert-manager (or equivalent) for TLS — the manifests do not declare TLS
- GHCR pull access and a secrets storage location (password manager / Vault for offline copies)

## 1. Generate secrets

Run all generation from the repo root with a venv containing the backend deps:

```bash
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export ENCRYPTION_SALT=$(openssl rand -hex 16)
ADMIN_PASSWORD=$(openssl rand -base64 24)
export ADMIN_PASSWORD_HASH=$(python -c "from src.api.auth_local import get_password_hash; print(get_password_hash('$ADMIN_PASSWORD'))")
```

Store these (especially `ENCRYPTION_KEY`/`ENCRYPTION_SALT`) in a password manager now — losing the encryption key means tenant secrets in the database can never be decrypted.

## 2. Namespace and secrets

```bash
kubectl create namespace specterdefence

kubectl create secret docker-registry ghcr-registry-secret \
  -n specterdefence --docker-server=ghcr.io \
  --docker-username=YOU --docker-password=GHCR_TOKEN

kubectl create secret generic specterdefence-secrets -n specterdefence \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=ENCRYPTION_SALT="$ENCRYPTION_SALT" \
  --from-literal=ADMIN_PASSWORD_HASH="$ADMIN_PASSWORD_HASH" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST:5432/specterdefence" \
  --from-literal=KIMI_API_KEY="" \
  --from-literal=ABUSEIPDB_API_KEY="" \
  --from-literal=ALIENVAULT_OTX_API_KEY=""
```

The manifests reference all of these keys, so create them even when empty. For a dev/small setup, `DATABASE_URL=sqlite+aiosqlite:////app/data/specterdefence.db` works if you add storage — Postgres is the production default.

## 3. TLS

```bash
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: you@yourdomain.test
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
EOF
```

Then add a `tls:` block (and the cert-manager issuer annotation) to the ingresses in `k8s/prod/ingress.yaml`, or configure Traefik's built-in ACME resolver cluster-wide.

## 4. Deploy and verify

```bash
kubectl apply -f k8s/prod/
kubectl get pods,ingress,cronjobs -n specterdefence
```

Verification:

```bash
# Security headers from the backend middleware (HSTS/CSP only appear in non-debug mode)
curl -sI https://app.<your-domain> | grep -Ei 'strict-transport|x-frame|x-content|content-security'

# Login rate limiting: after 5 bad attempts per 5-minute window you should get 429s
for i in {1..7}; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST https://app.<your-domain>/api/v1/auth/local/login \
    -H "Content-Type: application/json" -d '{"username":"admin","password":"wrong"}'
done

# Valid login returns a JWT
curl -s -X POST https://app.<your-domain>/api/v1/auth/local/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}"
```

Collector and security-scan CronJobs run on their schedules (`*/5 * * * *`, `0 */4 * * *`); check with `kubectl get jobs -n specterdefence`.

## 5. Backups

- **Postgres**: `pg_dump` on a schedule into secure object storage.
- **Keys**: encrypted offline copy of `ENCRYPTION_KEY`, `ENCRYPTION_SALT`, `SECRET_KEY`, `JWT_SECRET_KEY` (e.g. `gpg --symmetric`).

## 6. Hardening recommendations

Not in the shipped manifests — add according to your risk bar:

- HPA (2–10 replicas) + PodDisruptionBudget for the backend
- NetworkPolicy restricting backend egress to the DB and internet
- Pod Security Standards `restricted` enforcement on the namespace
- Topology spread constraints once multi-replica
- External Secrets Operator / stakater Reloader for managed secret sync and pod restarts

## Rotation and troubleshooting

See [secret-rotation.md](secret-rotation.md). Security contact: security@digitaladrenalin.net.
