# SpecterDefence Documentation

Welcome to the SpecterDefence documentation.

## Table of Contents

### Getting Started
- [Main README](../README.md) - Quick start and overview
- [Deployment Guide](./DEPLOYMENT.md) - Kubernetes deployment notes
- [Secure Deployment](./SECURE-DEPLOYMENT.md) - Production security hardening

### Configuration
- [Office 365 Permissions](./OFFICE365-PERMISSIONS.md) - Required Microsoft Graph API permissions
- [Secret Rotation](./secret-rotation.md) - Procedures for rotating credentials and keys

### Security Documentation
- [Security Audit](./SECURITY-AUDIT.md) - Security assessment findings
- [Security Audit Summary](./SECURITY-AUDIT-SUMMARY.md) - Executive summary
- [Security Hardening Checklist](./SECURITY-HARDENING-CHECKLIST.md) - Step-by-step hardening guide
- [Kubernetes Security](./k8s-security.md) - K8s-specific security practices

### Architecture & Planning
- [AI Architecture](./AI-ARCHITECTURE.md) - AI/ML component design
- [AI Roadmap](./AI-ROADMAP.md) - Planned AI enhancements

---

## Quick Links

### For Administrators
1. Start with [Secure Deployment](./SECURE-DEPLOYMENT.md) for production setup
2. Configure [Office 365 Permissions](./OFFICE365-PERMISSIONS.md) for tenant monitoring
3. Follow [Secret Rotation](./secret-rotation.md) for credential management

### For Security Teams
1. Review [Security Audit](./SECURITY-AUDIT.md) for current security posture
2. Use [Security Hardening Checklist](./SECURITY-HARDENING-CHECKLIST.md) for improvements
3. Check [Kubernetes Security](./k8s-security.md) for infrastructure hardening

### For Developers
1. See [AI Roadmap](./AI-ROADMAP.md) for upcoming features
2. Review [AI Architecture](./AI-ARCHITECTURE.md) for implementation details

---

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

Then reference in deployment:
```yaml
envFrom:
  - secretRef:
      name: specterdefence-secrets
```

### 2. Manual Secret Management

For development or single-node deployments:

```bash
# Create namespace
kubectl create namespace specterdefence

# Create secrets
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="your-secret-key" \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=ENCRYPTION_KEY="your-encryption-key"
```

See [Kubernetes Security](./k8s-security.md) for detailed security configuration.

---

## Office 365 Integration

To monitor Office 365 tenants, SpecterDefence requires specific Microsoft Graph API permissions:

**Quick Summary:**
- 10 read-only permissions
- No write access to your tenant
- All data encrypted at rest
- Certificate-based auth recommended

👉 See [Office 365 Permissions Guide](./OFFICE365-PERMISSIONS.md) for complete details.

---

## Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| [Office 365 Permissions](./OFFICE365-PERMISSIONS.md) | ✅ Complete | 2026-03-05 |
| [Secure Deployment](./SECURE-DEPLOYMENT.md) | ✅ Complete | 2026-03-04 |
| [Secret Rotation](./secret-rotation.md) | ✅ Complete | 2026-03-01 |
| [Security Audit](./SECURITY-AUDIT.md) | ✅ Complete | 2026-03-04 |
| [Deployment Notes](./DEPLOYMENT.md) | ⚠️ Outdated (v1) | 2026-03-01 |
| [AI Roadmap](./AI-ROADMAP.md) | 🚧 Planning | 2026-03-04 |

---

## Contributing to Documentation

1. All docs are in Markdown format
2. Place new docs in `/docs/` folder
3. Update this README with links
4. Follow the existing format for consistency
5. Include date and status in document headers

---

## Support

- 📧 Email: support@specterdefence.io
- 🐛 GitHub Issues: https://github.com/DiGiacomi-Shared/specterdefence/issues
- 📖 Full Docs: https://docs.specterdefence.io
