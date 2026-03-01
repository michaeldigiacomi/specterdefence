# SpecterDefence Documentation

Welcome to the SpecterDefence documentation.

## Table of Contents

- [API Documentation](./api.md)
- [Deployment Guide](./deployment.md)
- [Architecture Overview](./architecture.md)
- [Configuration Reference](./configuration.md)

## Security Documentation

- [Kubernetes Security Best Practices](./k8s-security.md) - Security hardening for K8s deployments
- [Secret Rotation Guide](./secret-rotation.md) - Procedures for rotating credentials and keys

## Getting Started

See the main [README.md](../README.md) for quick start instructions.

## Kubernetes Secret Management

SpecterDefence supports multiple secret management strategies:

### 1. Existing Secret (Recommended for Production)

Create and manage secrets outside of Helm:

```bash
kubectl create secret generic specterdefence-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL=postgresql://user:pass@host/db \
  --from-literal=ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

Then install with:

```bash
helm upgrade --install specterdefence ./helm \
  --set secrets.existingSecret.enabled=true \
  --set secrets.existingSecret.name=specterdefence-secrets
```

### 2. External Secrets Operator

For cloud-native secret management with Vault, AWS Secrets Manager, etc.:

```bash
helm upgrade --install specterdefence ./helm \
  --set secrets.externalSecrets.enabled=true \
  --set secrets.externalSecrets.secretStore.name=vault-backend
```

### 3. Helm-Managed Secrets (NOT for Production)

For development only:

```bash
helm upgrade --install specterdefence ./helm \
  --set secrets.helmManaged.enabled=true \
  --set secrets.helmManaged.secretKey=dev-secret-key \
  --set secrets.helmManaged.databaseUrl=sqlite:///./dev.db
```

See [Kubernetes Security](./k8s-security.md) for detailed security configuration.
