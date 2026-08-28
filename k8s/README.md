# SpecterDefence Kubernetes Manifests

Plain Kubernetes YAML (no Helm, no Kustomize). Deploy with `kubectl apply -f k8s/prod/`.

## Manifests

| File | Contents |
|------|----------|
| `prod/namespace.yaml` | `specterdefence` namespace |
| `prod/deployment.yaml` | Backend `specterdefence-backend`: FastAPI, 1 replica, port 8000, `/health` liveness/readiness probes |
| `prod/frontend.yaml` | Frontend `specterdefence-frontend`: Nginx serving the React build, 1 replica, port 80 |
| `prod/marketing.yaml` | Marketing site `specterdefence-marketing`, port 80 |
| `prod/ingress.yaml` | Traefik ingress: `specterdefence.digitaladrenalin.net` → marketing; `app.specterdefence.digitaladrenalin.net` → `/api`,`/ws` → backend :8000, `/` → frontend :80 |
| `prod/collector-cronjob.yaml` | `specterdefence-collector-prod`, `*/5 * * * *`, `python -m src.collector.main` |
| `prod/security-cronjob.yaml` | `specterdefence-security-scans-prod`, `0 */4 * * *`, `python -m src.collector.security_scans` |
| `cronjob-monitoring.yaml` | `specterdefence-monitoring`, hourly, `python -m src.collector.monitoring` |

Images: `ghcr.io/michaeldigiacomi/specterdefence-[backend|frontend]:latest`. TLS is not declared in the manifests — terminate it at your ingress controller (e.g. cert-manager + Let's Encrypt).

## Prerequisites

1. **Image pull secret** (GHCR):

   ```bash
   kubectl create secret docker-registry ghcr-registry-secret \
     -n specterdefence \
     --docker-server=ghcr.io \
     --docker-username=YOUR_GITHUB_USERNAME \
     --docker-password=GHCR_READ_PACKAGE_TOKEN
   ```

2. **App secret** `specterdefence-secrets` with the keys the manifests reference: `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD_HASH`, `KIMI_API_KEY`, `ABUSEIPDB_API_KEY`, `ALIENVAULT_OTX_API_KEY`. The optional keys can hold empty values. See `docs/SECURE-DEPLOYMENT.md` for generation commands, and `docs/secret-rotation.md` for rotation.

## Deploy and verify

```bash
kubectl apply -f k8s/prod/
kubectl get pods,ingress,cronjobs -n specterdefence
kubectl logs -n specterdefence deployment/specterdefence-backend --tail=50
```

## Notes / limitations

- Single replica per deployment — no HPA, PDB, or NetworkPolicy. Recommendations live in `docs/SECURE-DEPLOYMENT.md`.
- `imagePullPolicy: Always` on `:latest` — every pod start pulls the newest main-branch image. For pinned releases, edit the image tag yourself.
- CronJobs use `concurrencyPolicy: Forbid` so overlapping collector runs do not happen.
