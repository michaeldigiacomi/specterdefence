# SpecterDefence k3s Deployment Notes

**Date**: 2024-03-01
**Cluster**: k3s.digitaladrenalin.net (57.129.132.176)
**Namespace**: specterdefence
**Deployment URL**: http://specterdefence.k3s.digitaladrenalin.net

## Deployment Status

| Component | Status | Notes |
|-----------|--------|-------|
| Namespace | ✅ Created | `specterdefence` |
| Secrets | ✅ Created | Stored in `specterdefence-secrets` |
| Deployment | ✅ Running | 2 replicas |
| Service | ✅ Active | ClusterIP at 10.43.180.25 |
| Ingress | ✅ Active | Traefik ingress configured |
| PVC | ✅ Bound | 10GB local-path storage |

## Configuration

### Environment Variables

```
DATABASE_URL=sqlite+aiosqlite:////app/data/specterdefence.db
SECRET_KEY=<redacted>
ENCRYPTION_KEY=<redacted>
KIMI_API_KEY=placeholder-to-be-updated-by-mike
```

### Access Information

- **Internal Service**: `specterdefence.specterdefence.svc.cluster.local:80`
- **External URL**: http://specterdefence.k3s.digitaladrenalin.net
- **Health Endpoint**: `/health`

## Deployment Steps Performed

1. ✅ Created namespace `specterdefence`
2. ✅ Generated secure keys (SECRET_KEY, ENCRYPTION_KEY)
3. ✅ Created Kubernetes secrets
4. ✅ Copied application source to `/opt/specterdefence/src` on k3s node
5. ✅ Applied deployment manifest with persistent storage
6. ✅ Configured Traefik ingress
7. ✅ Verified health endpoint responding

## Scaling

```bash
# Scale to 2 replicas
kubectl scale deployment specterdefence --replicas=2 -n specterdefence

# Check status
kubectl get pods -n specterdefence
```

## Troubleshooting

### Check Pod Logs
```bash
kubectl logs -n specterdefence deployment/specterdefence
```

### Port Forward for Testing
```bash
kubectl port-forward -n specterdefence svc/specterdefence 8080:80
curl http://localhost:8080/health
```

### Restart Deployment
```bash
kubectl rollout restart deployment/specterdefence -n specterdefence
```

## Post-Deployment Tasks

- [ ] Update KIMI_API_KEY with actual API key from Mike
- [ ] Configure SSL/TLS certificates for HTTPS
- [ ] Set up monitoring and alerting
- [ ] Configure backup for SQLite database
- [ ] Add PostgreSQL for production database

## Notes

- Using SQLite for initial deployment (consider PostgreSQL for production)
- Dependencies are installed on first pod start (takes ~2 minutes)
- Application source is mounted via hostPath from `/opt/specterdefence/src`
- Data is persisted via PVC using local-path storage class
