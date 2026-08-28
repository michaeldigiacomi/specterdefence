# Office 365 Permissions Setup

Permissions SpecterDefence's tenant app registration actually needs, based on the endpoints the code calls. All are **Application** (app-only, client credentials) and **read-only**; none require delegated auth.

## Required permissions

| Permission (Graph) | Used for |
|--------------------|----------|
| `Organization.Read.All` | Tenant validation on registration (`/organization`) |
| `User.Read.All` | User listing + group/role membership for admin detection (`/users`, `/users/{id}/memberOf`) |
| `Directory.Read.All` | Robust directory/memberOf reads (add alongside User.Read.All) |
| `UserAuthenticationMethod.Read.All` | MFA methods per user (`/users/{id}/authentication/methods`) |
| `Policy.Read.All` | Conditional Access policies (`/identity/conditionalAccess/policies`) |
| `Application.Read.All` | OAuth apps, consent grants (`/servicePrincipals`, `/applications`, appRoleAssignments, oauth2PermissionGrants) |
| `AuditLog.Read.All` | Directory audit events (`/auditLogs/directoryAudits`) |
| `MailboxSettings.Read` (or `Mail.Read`) | Inbox message rules (`/users/{id}/mailFolders/inbox/messageRules`) |

Also grant (under **Office 365 Management APIs**, not Microsoft Graph):

| Permission | Used for |
|-----------|----------|
| `ActivityFeed.Read` | Core collector feed (Entra/Exchange/SharePoint/General audit events) |
| `ActivityFeed.ReadDlp` | DLP events — optional if you skip the `DLP.All` content type |

The code uses the scope `https://graph.microsoft.com/.default`, so any additional permissions you grant stay inert — grant exactly what's above.

## Setup

1. **Register the app**: Entra portal → App registrations → New registration (single tenant, no redirect URI).
2. **Grant permissions**: API permissions → add the Graph permissions above → repeat under Office 365 Management APIs for the ActivityFeed permissions → **Grant admin consent**.
3. **Client secret**: Certificates & secrets → New client secret; copy the value immediately.
4. **Add the tenant in SpecterDefence**: Tenants page → Add Tenant with Tenant ID, Client ID, Client Secret. SpecterDefence validates the connection on save (`/api/v1/tenants/validate`).

## Troubleshooting

- **"Insufficient privileges"** — admin consent not granted (Entra → Enterprise applications → your app → Permissions).
- **Collector returns nothing** — unified audit logging may be disabled in the tenant (M365 admin center → Audit); first enablement can take up to 24 h to produce logs.
- **Mailbox-rule scan failures only** — mailbox rules need `MailboxSettings.Read`/`Mail.Read`; verify that permission and consent specifically.
