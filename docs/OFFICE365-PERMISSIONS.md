# Office 365 Tenant Permissions Guide

This document details the Microsoft Graph API permissions required for SpecterDefence to monitor your Office 365 tenant security posture.

## Overview

SpecterDefence connects to your Office 365 tenant via the Microsoft Graph API to collect security-relevant data. This guide explains each permission, why it's needed, and the minimum level of access required.

---

## Required Permissions

### Audit Logs

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **AuditLog.Read.All** | Application | Core functionality - Reads audit logs for sign-ins, admin actions, and security events | All audit log entries including failed logins, MFA events, admin operations |

**Justification:** This is the primary permission for security monitoring. Without it, SpecterDefence cannot detect suspicious activities like impossible travel, brute force attempts, or unauthorized admin actions.

---

### User Management

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **User.Read.All** | Application | Lists all users to identify accounts without MFA, disabled accounts, admin roles | User profiles, sign-in activity, license status, role assignments |

**Justification:** Required to identify high-risk users (admins without MFA, stale accounts) and correlate audit events with user identities.

---

### Group Management

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **Group.Read.All** | Application | Identifies privileged groups (Global Admins, etc.) and membership changes | Group memberships, owners, member lists |

**Justification:** Privileged groups are high-value targets. This permission detects unauthorized additions to admin groups.

---

### Directory Management

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **Directory.Read.All** | Application | Reads tenant-wide security settings, conditional access policies, and organization info | Conditional access policies, security defaults, organizational settings |

**Justification:** Needed to assess baseline security posture (e.g., is Security Defaults enabled?) and detect policy changes.

---

### Role Management

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **RoleManagement.Read.Directory** | Application | Identifies who has administrative privileges and tracks role assignments | Directory roles (Global Admin, Exchange Admin, etc.), role assignments |

**Justification:** Tracks privilege escalation attempts and identifies over-privileged accounts.

---

### Application Management

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **Application.Read.All** | Application | Detects malicious app registrations and consent grants | App registrations, service principals, OAuth2 permission grants |

**Justification:** Malicious app registrations are a common attack vector. This permission detects unauthorized apps with tenant-wide access.

---

### Sign-In Activity

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **SignInActivity.Read.All** | Application | Extended sign-in analytics for impossible travel detection | Sign-in locations, IP addresses, device info, authentication methods used |

**Justification:** Provides detailed sign-in context for anomaly detection (impossible travel, new device locations).

---

### Policy Management

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **Policy.Read.All** | Application | Reads conditional access and authentication policies | CA policies, MFA requirements, device compliance policies |

**Justification:** Identifies policy gaps and tracks unauthorized policy changes.

---

### Identity Risk Events

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **IdentityRiskEvent.Read.All** | Application | Reads Identity Protection risk detections | Risky sign-ins, risky users, anonymous IP usage, leaked credentials |

**Justification:** Integrates with Microsoft's AI-powered risk detection for enhanced threat intelligence.

---

---

### Audit & Security Logs (Management Activity API)

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **ActivityFeed.Read** | Application | **Primary Collector Permission** - Fetches raw audit logs for Entra, Exchange, and SharePoint | Real-time stream of all user and admin activity logs |
| **ActivityFeed.ReadDlp** | Application | Optional - Required for Data Loss Prevention (DLP) event monitoring | DLP policy matches and sensitive data alerts |

**Justification:** The collector uses the high-performance Management Activity API instead of Graph for log ingestion. This permission is found under "Office 365 Management APIs" in Azure, not "Microsoft Graph".

---

### Mailbox Management (Microsoft Graph)

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **Mail.Read.All** | Application | Scans inbox rules for suspicious forwarding, redirects, or hidden rules | Mailbox rules, forwarding settings, auto-reply configurations |

**Justification:** Mailbox rules are frequently used by attackers to hide their activity (e.g., auto-deleting alerts) or exfiltrate data.

---

### Authentication & MFA

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **UserAuthenticationMethod.Read.All** | Application | Tracks MFA enrollment status and identifies weak authentication methods | Registered MFA methods (SMS, App, FIDO2), enrollment dates |

**Justification:** Essential for identifying users without MFA or those using insecure methods like SMS.

---

### Reports

| Permission | Type | Why It's Needed | Data Accessed |
|------------|------|-----------------|---------------|
| **Reports.Read.All** | Application | Accesses security reports and compliance data | Security score, secure score history, credential usage reports |

**Justification:** Provides historical data for trend analysis and compliance reporting.

---

## Permission Summary Table

| Permission | Access Level | Risk Level | Justification |
|------------|-------------|------------|---------------|
| AuditLog.Read.All | Read | Medium | Core monitoring capability |
| User.Read.All | Read | Low | User context and risk assessment |
| Group.Read.All | Read | Low | Privileged group monitoring |
| Directory.Read.All | Read | Medium | Security posture assessment |
| RoleManagement.Read.Directory | Read | Low | Admin role tracking |
| Application.Read.All | Read | Medium | Malicious app detection |
| SignInActivity.Read.All | Read | Medium | Anomaly detection |
| Policy.Read.All | Read | Low | Security policy monitoring |
| IdentityRiskEvent.Read.All | Read | Low | Risk event correlation |
| Mail.Read.All | Read | High | Mailbox rule security monitoring |
| UserAuthenticationMethod.Read.All | Read | Medium | MFA compliance tracking |
| Reports.Read.All | Read | Low | Compliance and reporting |
| **ActivityFeed.Read** | Read | Medium | **Required for Collector** (Office 365 Management API) |

**Total Permissions:** 13 (all Read-Only)
**Write Permissions:** None (Optional: Mail.ReadWrite.All for remediation)
**Admin Consent Required:** Yes (all are Application permissions)

---

## Data Flow Diagram

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│  SpecterDefence │────────▶│ Microsoft Graph  │────────▶│   Office    │
│    (Your K8s)   │  HTTPS  │      API         │  HTTPS  │   365 Tenant│
└─────────────────┘         └──────────────────┘         └─────────────┘
         │                             │
         │                             │
         ▼                             ▼
┌─────────────────┐         ┌──────────────────┐
│  PostgreSQL DB  │         │  Audit Logs      │
│  (Encrypted)    │         │  User Data       │
└─────────────────┘         │  Sign-in Events  │
                            └──────────────────┘
```

---

## Security Considerations

### 1. Principle of Least Privilege
- All permissions are **Read-Only**
- No write/delete permissions requested
- Cannot modify tenant settings or user data
- Cannot send emails or access mailboxes

### 2. Data Encryption
- All data encrypted at rest using Fernet (AES-128)
- All communications use TLS 1.2+
- Tenant credentials stored encrypted in PostgreSQL

### 3. Access Control
- Application uses client credentials flow (no user impersonation)
- Certificate-based authentication recommended for production
- Credentials rotated automatically via refresh tokens

### 4. Data Retention
- Audit logs retained per your configuration (default: 90 days)
- No user content (emails, files) accessed or stored
- Only metadata and security events collected

---

## Setting Up Permissions

### Step 1: Register Application in Azure AD

1. Navigate to **Azure AD** → **App registrations** → **New registration**
2. Name: `SpecterDefence Security Monitor`
3. Supported account types: **Accounts in this organizational directory only**
4. Redirect URI: None (client credentials flow)
5. Click **Register**

### Step 2: Add API Permissions

1. Go to **API permissions** → **Add a permission**
2. Select **Microsoft Graph** → **Application permissions**
3. Add each permission from the table above:
   - `AuditLog.Read.All`
   - `User.Read.All`
   - `Group.Read.All`
   - `Directory.Read.All`
   - `RoleManagement.Read.Directory`
   - `Application.Read.All`
   - `SignInActivity.Read.All`
   - `Policy.Read.All`
   - `IdentityRiskEvent.Read.All`
   - `Reports.Read.All`
4. Click **Grant admin consent for [Tenant]**

### Step 3: Create Client Secret

1. Go to **Certificates & secrets** → **New client secret**
2. Description: `SpecterDefence Production`
3. Expires: **24 months** (recommended)
4. Copy the secret value immediately

### Step 4: Configure SpecterDefence

1. In SpecterDefence UI, go to **Settings** → **Tenants** → **Add Tenant**
2. Enter:
   - **Tenant ID**: Your Azure AD tenant ID
   - **Client ID**: Application (client) ID from Step 1
   - **Client Secret**: Value from Step 3
   - **Tenant Name**: Friendly name for display
3. Click **Save**
4. SpecterDefence will validate connectivity and begin data collection

---

## Troubleshooting Permission Issues

### "Insufficient privileges" Error

**Cause:** Admin consent not granted

**Solution:**
```bash
# Azure CLI (run as Global Admin)
az ad app permission admin-consent --id <application-id>
```

Or via Portal:
1. Azure AD → Enterprise applications → [Your App] → Permissions
2. Click **Grant admin consent for [Tenant]**

### "Audit log not found" Error

**Cause:** Audit logging not enabled or retention policy expired

**Solution:**
1. Microsoft 365 admin center → Security & Compliance → Audit
2. Enable auditing if not already enabled
3. Note: First-time enablement can take 24 hours to generate logs

### "IdentityRiskEvent.Read.All not granted"

**Cause:** Requires Azure AD Premium P2 license

**Solution:** This permission is optional. SpecterDefence will work without it but with reduced threat intelligence.

---

## Compliance Notes

### GDPR
- SpecterDefence processes personal data (user names, IP addresses) for security purposes
- All data encrypted and access-logged
- Data retention configurable (default: 90 days)
- Right to erasure supported (tenant deletion removes all data)

### SOC 2
- All permissions are read-only (no data modification)
- Comprehensive audit logging of all data access
- Encryption at rest and in transit
- Regular security assessments

### ISO 27001
- Access controls documented
- Data classification applied
- Incident response procedures in place

---

## Alternative: Delegated Permissions (Not Recommended)

If your organization cannot grant Application permissions, SpecterDefence can use Delegated permissions with a service account:

| Permission | Type | Notes |
|------------|------|-------|
| AuditLog.Read.All | Delegated | Requires service account with Global Admin or Security Admin role |

**Disadvantages:**
- Requires privileged service account
- More complex setup
- Higher security risk (privileged account)
- Not supported in current SpecterDefence version

---

## References

- [Microsoft Graph Permissions Reference](https://docs.microsoft.com/en-us/graph/permissions-reference)
- [Office 365 Management API](https://docs.microsoft.com/en-us/office/office-365-management-api/)
- [Azure AD Security Best Practices](https://docs.microsoft.com/en-us/azure/active-directory/fundamentals/security-operations-privileged-accounts)

---

## Support

For questions about permissions or setup:
- Email: support@specterdefence.io
- Documentation: https://docs.specterdefence.io
- GitHub Issues: https://github.com/DiGiacomi-Shared/specterdefence/issues
