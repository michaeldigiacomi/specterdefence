# Password Persistence Issue - Investigation Summary

## Problem Statement
1. User changes password in UI ✓
2. Gets kicked out to login (expected) ✓
3. New password doesn't work ✗
4. After a few minutes, old password (admin123) works again ✗

## Root Cause Found

**SQLite with Multiple Pods = Data Inconsistency**

The Kubernetes deployment had:
- `replicas: 2` (2 pods running)
- SQLite database with `ReadWriteOnce` PVC
- Each pod had its own SQLite database file

When a user changed their password:
- Only ONE pod received the update
- The other pod retained the old password
- Load balancer randomly routed requests to either pod
- Result: Intermittent authentication failures

## Files Changed

### 1. `k8s-deployment-container.yaml`
- Changed `replicas: 2` → `replicas: 1` (immediate fix)
- Added detailed comments warning about SQLite + multi-pod issues
- Added DATABASE_URL format documentation

### 2. `k8s/postgres.yaml` (NEW)
- Complete PostgreSQL deployment for multi-pod support
- StatefulSet with persistent storage
- Service for internal cluster communication
- Separate secret for PostgreSQL credentials

### 3. `scripts/quick-fix-password.sh` (NEW)
- One-command fix to scale down to 1 replica
- Immediate workaround for production

### 4. `scripts/migrate_to_postgres.py` (NEW)
- Data migration tool from SQLite to PostgreSQL
- Interactive script with verification steps

### 5. `PASSWORD_FIX.md` (NEW)
- Complete deployment guide for PostgreSQL migration
- Step-by-step instructions

## Immediate Fix (Apply Now)

Run the quick fix script to reduce to 1 replica:

```bash
./scripts/quick-fix-password.sh
```

Or manually:
```bash
kubectl scale deployment specterdefence --replicas=1 -n specterdefence
```

## Permanent Fix (PostgreSQL)

1. Deploy PostgreSQL:
   ```bash
   kubectl apply -f k8s/postgres.yaml
   ```

2. Update PostgreSQL secret with secure password:
   ```bash
   kubectl delete secret postgres-secrets -n specterdefence
   kubectl create secret generic postgres-secrets \
     --from-literal=POSTGRES_PASSWORD='$(openssl rand -base64 32)' \
     -n specterdefence
   ```

3. Migrate data:
   ```bash
   python scripts/migrate_to_postgres.py
   ```

4. Update DATABASE_URL secret:
   ```bash
   kubectl patch secret specterdefence-secrets -n specterdefence \
     --type='json' \
     -p='[{"op": "replace", "path": "/data/DATABASE_URL", "value":"'$(echo -n 'postgresql+asyncpg://specter:PASSWORD@postgres:5432/specterdb' | base64)'"}]'
   ```

5. Scale back up:
   ```bash
   kubectl scale deployment specterdefence --replicas=2 -n specterdefence
   ```

## Testing Checklist

After applying fixes, verify:

- [ ] Change password in UI
- [ ] Verify in database: `SELECT username, updated_at FROM users;`
- [ ] Login with new password (should work)
- [ ] Wait 5 minutes
- [ ] Login again with new password (should still work)
- [ ] Old password should NOT work
- [ ] Both pods show same password hash (if multi-pod)

## Code Verification

The authentication code itself is correct:
- `update_admin_password()` properly commits to database
- `get_admin_password_hash()` reads from database
- No caching of password hashes
- Proper session management with `expire_on_commit=False`

The issue was purely infrastructure-related (database type + pod scaling).
