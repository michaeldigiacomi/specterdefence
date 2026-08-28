# Secret Rotation

How to rotate each secret SpecterDefence uses. All app secrets live in the Kubernetes secret `specterdefence-secrets` (namespace `specterdefence`); apply changes with `kubectl patch secret ... -p='[{"op":"replace","path":"/data/<KEY>","value":"'"$(echo -n <NEW> | base64)"'"}]'` followed by `kubectl rollout restart deployment/specterdefence-backend -n specterdefence` (and the CronJobs pick it up on their next run).

## Secrets and impact

| Secret | Impact of rotation | Notes |
|--------|--------------------|-------|
| `SECRET_KEY` | Sessions invalidated; also used as fallback base for the encryption key when `ENCRYPTION_KEY` is unset | If it feeds encryption, treat like `ENCRYPTION_KEY` below |
| `JWT_SECRET_KEY` | All existing JWTs invalidated — users re-login | Safe, low impact |
| `DATABASE_URL` | Brief outage if DB credentials rotate; update the secret before or as DB credentials change | Ensure `postgresql+asyncpg://` format |
| `ENCRYPTION_KEY` (+ `ENCRYPTION_SALT`) | **Existing encrypted data (tenant client secrets, webhook URLs) becomes unreadable until re-encrypted** | There is no key versioning or multi-key support, and no re-encrypt API. Re-encrypt by deleting and re-registering tenants/webhooks, or decrypt with the old key and re-encrypt with the new one before switching |
| `ADMIN_PASSWORD_HASH` | None beyond the changed admin password | Generate: `python -c "from src.api.auth_local import get_password_hash; print(get_password_hash('new'))"` |
| `ABUSEIPDB_API_KEY`, `ALIENVAULT_OTX_API_KEY` | Threat-intel lookups fail until updated (login processing still completes) | Low impact |
| `KIMI_API_KEY` | None — reserved, unused by code | Can stay empty |

Per-tenant O365 app credentials (`tenant_id`/`client_id`/`client_secret`) are **not** Kubernetes secrets — they're stored Fernet-encrypted in the tenants table. Rotate them by creating a new client secret in Microsoft Entra, then updating the tenant via the UI or `PATCH /api/v1/tenants/{id}`.

## Recommended procedure (zero-downtime where possible)

1. Generate the new value (see table / `docs/SECURE-DEPLOYMENT.md` for generation commands).
2. Patch `specterdefence-secrets`; rolling-restart the backend deployment.
3. Verify: health endpoint `curl https://app.<domain>/api/v1/health`, dashboard login, and watch the next collector CronJob run (`kubectl logs -n specterdefence job/<name>`).
4. For `ENCRYPTION_KEY`: rotate tenant/webhook secrets under the old key first (decrypt + re-encrypt, or re-register), then switch keys.

## Automation (optional)

If you use the External Secrets Operator or stakater/Reloader on your cluster, syncing `specterdefence-secrets` from your secrets backend plus a rollout trigger automates the procedure above. These are cluster-level ops patterns — the app itself has no Vault/external-secrets integration.

## Troubleshooting

- Pods crash-loop after rotation → `kubectl get secret specterdefence-secrets -n specterdefence -o jsonpath='{.data}' | jq -r 'keys[]'` to confirm all keys exist; check `kubectl logs -n specterdefence deployment/specterdefence-backend`.
- Fernet errors in logs after key change → data was still encrypted with the old key; restore the old `ENCRYPTION_KEY`, re-encrypt, retry.
- Rollback: keep a sealed offline copy of the previous secret; `kubectl apply` it back and rolling-restart.
