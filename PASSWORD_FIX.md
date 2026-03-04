# Password Persistence Fix for SpecterDefence

## Root Cause

With 2 pods running and SQLite database:
1. Each pod has its own SQLite database file (or one can't write to the shared volume due to `ReadWriteOnce`)
2. When password is changed, only ONE pod gets the update
3. Load balancer routes requests to both pods randomly
4. User experiences inconsistent login behavior depending on which pod handles the request

## Solution

Migrate from SQLite to PostgreSQL which properly supports multiple concurrent connections from multiple pods.

## Files Modified

1. `k8s/postgres.yaml` - New PostgreSQL deployment
2. `k8s-deployment-container.yaml` - Updated to use PostgreSQL and reduce env var exposure
3. `src/config.py` - Added PostgreSQL URL validation

## Deployment Steps

1. Apply the PostgreSQL deployment:
   ```bash
   kubectl apply -f k8s/postgres.yaml
   ```

2. Wait for PostgreSQL to be ready:
   ```bash
   kubectl wait --for=condition=ready pod -l app=postgres -n specterdefence --timeout=60s
   ```

3. Update the DATABASE_URL secret:
   ```bash
   kubectl delete secret specterdefence-secrets -n specterdefence
   kubectl create secret generic specterdefence-secrets \
     --from-literal=DATABASE_URL='postgresql+asyncpg://specter:${POSTGRES_PASSWORD}@postgres:5432/specterdb' \
     --from-literal=SECRET_KEY='your-secret-key' \
     --from-literal=ENCRYPTION_KEY='your-encryption-key' \
     --from-literal=KIMI_API_KEY='your-kimi-key' \
     -n specterdefence
   ```

4. Remove ADMIN_PASSWORD_HASH from secrets (no longer needed - password stored in DB only):
   ```bash
   # Make sure ADMIN_PASSWORD_HASH is NOT in the secret anymore
   ```

5. Apply the updated deployment:
   ```bash
   kubectl apply -f k8s-deployment-container.yaml
   ```

6. Restart the deployment to pick up new database:
   ```bash
   kubectl rollout restart deployment/specterdefence -n specterdefence
   ```

## Verification

1. Check both pods are running:
   ```bash
   kubectl get pods -n specterdefence
   ```

2. Change password in UI

3. Verify in PostgreSQL:
   ```bash
   kubectl exec -it postgres-0 -n specterdefence -- psql -U specter -d specterdb -c "SELECT username, updated_at FROM users;"
   ```

4. Test login multiple times - should work consistently

## Alternative: Quick Fix (Single Pod)

If you need a quick fix without PostgreSQL, reduce replicas to 1:

```yaml
spec:
  replicas: 1  # Changed from 2
```

This eliminates the consistency issue but removes high availability.
