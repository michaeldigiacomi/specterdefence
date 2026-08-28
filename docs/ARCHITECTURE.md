# SpecterDefence Architecture Document

> A comprehensive guide to the SpecterDefence Microsoft 365 security monitoring platform.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Core Components](#3-core-components)
4. [Data Models](#4-data-models)
5. [API Endpoints](#5-api-endpoints)
6. [Frontend](#6-frontend)
7. [Deployment Architecture](#7-deployment-architecture)
8. [Future Considerations](#8-future-considerations)

---

## 1. System Overview

### 1.1 High-Level Purpose

**SpecterDefence** is an automated security posture monitoring and management platform for Microsoft 365 environments. It continuously monitors tenant configurations, security policies, and threat indicators to help organizations maintain a strong security posture.

### 1.2 Key Capabilities and Features

| Capability | Description |
|------------|-------------|
| **Multi-Tenant Management** | Register and manage multiple Office 365 tenants from a single dashboard |
| **MFA Compliance Tracking** | Monitor MFA enrollment across all users with strength analysis |
| **Conditional Access Monitoring** | Track CA policy changes, detect security drift, and alert on policy disables |
| **OAuth App Risk Assessment** | Analyze OAuth applications for high-risk permissions and unverified publishers |
| **Mailbox Rule Monitoring** | Detect suspicious forwarding rules and hidden redirects |
| **Login Anomaly Detection** | Identify impossible travel, new countries, and brute force attempts. |
| **Insider Threat & DLP** | Monitor SharePoint sharing events and sensitive data exposure alerts |
| **Endpoint Monitoring** | Track Windows endpoint health, heartbeats, and security events |
| **Real-Time Alerting** | WebSocket-based alert streaming with Discord webhook integration |
| **Audit Log Collection** | Continuous ingestion of M365 audit logs (Entra, Exchange, SharePoint) |
| **Website & SSL Monitoring** | Track website availability, SSL certificate expiration, and domain registration |
| **User Management** | Multi-user support with tenant assignment and role-based access |
| **Settings Management** | System-wide configuration with detection thresholds, API keys, and config import/export |
| **Diagnostics** | Data ingestion diagnostics, audit log review, and login analytics |

### 1.3 Target Users

- **Security Administrators** - Monitor tenant security posture and respond to alerts
- **IT Operations Teams** - Track configuration changes and compliance status
- **Security Operations Centers (SOC)** - Receive real-time security alerts via webhooks
- **Compliance Officers** - Generate reports on MFA enrollment and policy compliance

---

## 2. Architecture Diagram

### 2.1 Component Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │   Microsoft  │  │   Discord    │  │   HashiCorp  │                      │
│  │    Graph API │  │   Webhooks   │  │     Vault    │                      │
│  └──────┬───────┘  └──────▲───────┘  └──────┬───────┘                      │
│         │                 │                 │                               │
└─────────┼─────────────────┼─────────────────┼───────────────────────────────┘
          │                 │                 │
          │ HTTPS           │ HTTPS           │ HTTPS
          │                 │                 │
┌─────────▼─────────────────┴─────────────────┴───────────────────────────────┐
│                            SPECTERDEFENCE PLATFORM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                     WINDOWS ENDPOINT                          │          │
│  │  ┌─────────────────────────────────────────────────────────┐  │          │
│  │  │              SpecterDefence Agent (C#)                  │  │          │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │          │
│  │  │  │ Event Watcher│  │ SQLite Buffer│  │ Uploader     │   │  │          │
│  │  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │  │          │
│  │  └─────────┼─────────────────┼─────────────────┼───────────┘  │          │
│  └────────────┼─────────────────┼─────────────────┼──────────────┘          │
│               │                 │                 │                         │
│               │                 │ HTTPS           │                         │
│               ▼                 ▼                 ▼                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FASTAPI BACKEND                             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐  │   │
│  │  │   Auth      │ │  Tenants    │ │  Analytics  │ │   Alerts     │  │   │
│  │  │   Router    │ │   Router    │ │   Router    │ │   Router     │  │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬───────┘  │   │
│  │         │               │               │               │          │   │
│  │  ┌──────▼───────────────▼───────────────▼───────────────▼───────┐  │   │
│  │  │                      Services Layer                           │  │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐  │  │   │
│  │  │  │ MFAReport │ │  CAPolicies│ │OAuthApps │ │ MailboxRules │  │  │   │
│  │  │  │  Service  │ │  Service   │ │ Service  │ │   Service    │  │  │   │
│  │  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬───────┘  │  │   │
│  │  │  ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌──────▼───────┐  │  │   │
│  │  │  │ SharePoint│ │ DLP/Insider│ │ Endpoint  │ │   Threat    │  │  │   │
│  │  │  │  Service  │ │  Service   │ │ Service  │ │   Intel     │  │  │   │
│  │  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬───────┘  │  │   │
│  │  │        └─────────────┴─────────────┴──────────────┘           │  │   │
│  │  │                          │                                     │  │   │
│  │  │  ┌───────────────────────▼───────────────────────┐            │  │   │
│  │  │  │              Alert Engine                      │            │  │   │
│  │  │  │  ┌───────────┐ ┌───────────┐ ┌──────────────┐  │            │  │   │
│  │  │  │  │  Rules    │ │   Deduplication           │  │            │  │   │
│  │  │  │  │  Engine   │ │   & Cooldown Logic        │  │            │  │   │
│  │  │  │  └───────────┘ └───────────┘ └──────────────┘  │            │  │   │
│  │  │  └───────────────────────┬───────────────────────┘            │  │   │
│  │  └──────────────────────────┼────────────────────────────────────┘  │   │
│  │                             │                                         │   │
│  │  ┌──────────────────────────▼────────────────────────────────────┐   │   │
│  │  │              Microsoft Graph Client (MSAL)                      │   │   │
│  │  │         Token Management • Rate Limiting • Pagination           │   │   │
│  │  └──────────────────────────┬────────────────────────────────────┘   │   │
│  └─────────────────────────────┼────────────────────────────────────────┘   │
│                                │                                             │
│  ┌─────────────────────────────▼────────────────────────────────────────┐   │
│  │                        DATA LAYER                                     │   │
│  │  ┌─────────────────┐  ┌──────────────────────────────────────────┐    │   │
│  │  │   PostgreSQL    │  │   Encrypted Secrets                       │    │   │
│  │  │   (SQLAlchemy)  │  │   (Fernet + PBKDF2)                        │    │   │
│  │  └─────────────────┘  └──────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ API Calls (REST/WebSocket)
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                          REACT FRONTEND (Vite + TypeScript)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Dashboard  │  │   Tenants   │  │   Alerts    │  │   Analytics │       │
│  │    Page     │  │    Page     │  │    Page     │  │    Page     │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                │                │                │              │
│  ┌──────▼────────────────▼────────────────▼────────────────▼──────┐        │
│  │                    State Management (Zustand)                  │        │
│  └────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Ingress Traffic
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                         KUBERNETES DEPLOYMENT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   API Pod        │  │  Frontend Pod   │  │   Collector CronJob         │ │
│  │   (FastAPI)      │  │    (Nginx)      │  │   (Data Collection)         │ │
│  │   Port: 8000     │  │   Port: 80      │  │   Schedule: */5 * * * *     │ │
│   Replicas: 1       │  │   Replicas: 1   │  │                             │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────────────────┘ │
│           │                    │                                          │
│  ┌────────▼────────────────────▼────────────────────────────────────────┐ │
│  │                         Traefik Ingress                              │ │
│  │         TLS (Let's Encrypt) • Rate Limiting • Security Headers       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW SEQUENCE                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. TENANT REGISTRATION                                                     │
│     ┌────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐   │
│     │ Admin  │───▶│  Encrypt     │───▶│   Store in   │───▶│  Validate  │   │
│     │ UI     │    │  Credentials │    │   Database   │    │  Graph API │   │
│     └────────┘    └──────────────┘    └──────────────┘    └────────────┘   │
│                                                                             │
│  2. CONTINUOUS MONITORING (Every 5 minutes)                                 │
│     ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│     │ CronJob    │───▶│  Get Access  │───▶│  Fetch Data  │───▶│  Analyze │  │
│     │ Trigger    │    │  Token       │    │  via Graph   │    │  Results │  │
│     └────────────┘    └──────────────┘    └──────────────┘    └────┬─────┘  │
│                                                                    │        │
│                          ┌─────────────────────────────────────────┘        │
│                          ▼                                                  │
│     ┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌─────────────┐     │
│     │  Store   │◀───│  Detect  │◀───│   Compare    │◀───│   Process   │     │
│     │  in DB   │    │  Anomaly │    │   Changes    │    │   Rules     │     │
│     └────┬─────┘    └──────────┘    └──────────────┘    └─────────────┘     │
│          │                                                                  │
│  3. ALERT GENERATION                                                        │
│          │     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│          └────▶│ Match Rules  │───▶│  Deduplicate │───▶│ Send Webhook │     │
│                │              │    │  (Cooldown)  │    │ (Discord)    │     │
│                └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                             │
│  4. REAL-TIME STREAMING                                                     │
│     ┌────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│     │  WebSocket │◀───│  Alert Feed  │◀───│   New Alert  │                  │
│     │  Clients   │    │  Manager     │    │   Detected   │                  │
│     └────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                             │
│  5. ENDPOINT AGENT TELEMETRY                                                │
│     ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│     │  Windows   │───▶│  SQLite      │───▶│  Batch       │───▶│  FastAPI │  │
│     │  Events    │    │  Buffer      │    │  Upload      │    │  Backend │  │
│     └────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 External Integrations

| Integration | Protocol | Purpose |
|-------------|----------|---------|
| Microsoft Graph API | HTTPS / OAuth 2.0 | Read tenant data (users, policies, audit logs) |
| Discord Webhooks | HTTPS / JSON | Real-time security alerts |
| Azure AD (MSAL) | OAuth 2.0 Client Credentials | Authentication to Graph API |
| HashiCorp Vault (optional) | HTTPS | External secret management |

---

## 3. Core Components

### 3.1 Backend: FastAPI Application Structure

```
src/
├── main.py                 # FastAPI application factory, middleware, lifespan
├── config.py               # Pydantic Settings - environment variable validation
├── database.py             # SQLAlchemy engine, session management, init
│
├── api/                    # API Routes (REST Endpoints)
│   ├── __init__.py         # Router aggregation
│   ├── auth.py             # MS Graph auth routes
│   ├── auth_local.py       # JWT local authentication
│   ├── tenants.py          # Tenant CRUD operations
│   ├── alerts.py           # Alert management endpoints
│   ├── websocket.py        # WebSocket connection handling
│   ├── mfa_report.py       # MFA enrollment endpoints
│   ├── ca_policies.py      # Conditional Access endpoints
│   ├── oauth_apps.py       # OAuth application endpoints
│   ├── mailbox_rules.py    # Mailbox rule endpoints
│   ├── analytics.py        # Login analytics endpoints
│   ├── sharepoint.py       # SharePoint analytics endpoints
│   ├── dlp.py              # DLP (Data Loss Prevention) endpoints
│   ├── mailbox.py          # Mailbox security endpoints
│   ├── endpoints.py        # Endpoint agent endpoints
│   ├── dashboard.py        # Dashboard data endpoints
│   ├── diagnostics.py       # Data ingestion diagnostics endpoints
│   ├── settings.py         # System settings endpoints
│   ├── users.py            # User management endpoints
│   ├── health.py           # Detailed health check endpoint
│   └── monitoring/         # Monitoring module (websites, SSL, domains)
│       ├── __init__.py     # Monitoring router aggregation
│       ├── websites.py     # Website availability monitoring
│       ├── ssl.py          # SSL certificate expiration monitoring
│       └── domains.py      # Domain registration monitoring
│
├── services/               # Business Logic Layer
│   ├── tenant.py           # Tenant management service
│   ├── encryption.py       # Fernet encryption for secrets
│   ├── enhanced_encryption.py # Enhanced encryption service
│   ├── credential_manager.py # Credential management service
│   ├── k8s_secrets_storage.py # Kubernetes secrets storage service
│   ├── mfa_report.py       # MFA tracking and compliance
│   ├── ca_policies.py      # CA policy monitoring
│   ├── oauth_apps.py       # OAuth app risk assessment
│   ├── mailbox_rules.py    # Mailbox rule analysis
│   ├── endpoints.py        # Endpoint agent management
│   ├── dashboard.py        # Dashboard aggregation
│   ├── alert_processor.py  # Alert processing logic
│   ├── alert_stream.py     # WebSocket streaming service
│   ├── settings.py         # Settings management
│   └── monitoring/          # Monitoring services
│       ├── __init__.py     # Monitoring service aggregation
│       ├── domain.py       # Domain monitoring service
│       ├── ssl.py           # SSL certificate monitoring service
│       └── website.py       # Website monitoring service
│
├── clients/                # External API Clients
│   ├── __init__.py         # Client aggregation
│   ├── ms_graph.py         # MSAL + Graph API client
│   ├── mfa_report.py       # MFA-specific Graph queries
│   ├── ca_policies.py      # CA policy Graph queries
│   ├── oauth_apps.py       # OAuth app Graph queries
│   └── mailbox_rules.py    # Mailbox rule Graph queries
│
├── models/                 # Data Models (SQLAlchemy + Pydantic)
│   ├── db.py               # SQLAlchemy ORM models
│   ├── user.py             # Local user models
│   ├── tenant.py           # Pydantic tenant schemas
│   ├── alerts.py           # Alert models and enums
│   ├── analytics.py        # Login analytics models
│   ├── sharepoint.py       # SharePoint data models
│   ├── endpoint.py         # Endpoint agent models
│   ├── mfa_report.py       # MFA enrollment models
│   ├── ca_policies.py      # CA policy models
│   ├── oauth_apps.py       # OAuth app models
│   ├── mailbox_rules.py    # Mailbox rule models
│   ├── mailbox.py          # Mailbox security models
│   ├── dlp.py              # DLP event models
│   ├── monitoring.py       # Website/SSL/domain monitoring models
│   ├── settings.py         # Settings models
│   ├── dashboard.py        # Dashboard data models
│   ├── types.py            # Custom SQLAlchemy types
│   └── audit_log.py        # Audit log models
│
├── alerts/                 # Alerting System
│   ├── engine.py           # Core alert processing engine
│   ├── rules.py            # Alert rule matching logic
│   └── discord.py          # Discord webhook client
│
├── analytics/              # Anomaly Detection
│   ├── anomalies.py        # Impossible travel, new country detection
│   ├── logins.py           # Login pattern analysis
│   ├── failed_logins.py    # Brute force detection
│   ├── sharepoint.py       # SharePoint sharing analysis
│   ├── insider_threat.py   # Sensitive data exposure detection
│   ├── threat_intel.py     # IP reputation (AbuseIPDB, OTX)
│   └── geo_ip.py           # GeoIP lookup utilities
│
└── collector/              # Data Collection Jobs
    ├── __init__.py         # Collector module init
    ├── main.py             # Collector entry point
    ├── o365_feed.py        # Office 365 audit log ingestion
    ├── security_scans.py   # Periodic security configuration scans
    └── monitoring.py       # Website/SSL/domain monitoring collector
```

#### Key FastAPI Configuration (main.py)

```python
# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; ..."
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), "
            "gyroscope=(), speaker=()"
        )
        return response

# RequestLoggingMiddleware — logs all requests with method, path, status, duration
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    ...

# Application lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # Create tables
    yield
    # Cleanup
```

### 3.2 Database Models (SQLAlchemy)

#### Core Tenant Model

```python
class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # Azure AD tenant ID
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)  # App registration ID
    client_secret: Mapped[str] = mapped_column(String(500), nullable=False)  # ENCRYPTED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connection_status: Mapped[str] = mapped_column(String(20), default="unknown")
    last_health_check: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
```

### 3.3 Authentication System

#### Local Authentication (JWT)

```python
# Password hashing with bcrypt
def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]  # bcrypt limit
    salt = bcrypt_lib.gensalt()
    return bcrypt_lib.hashpw(password_bytes, salt).decode('utf-8')

# JWT token creation
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(hours=2))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")

# Rate limiting: 5 attempts per 5 minutes, block for 15 minutes after
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300
_BLOCK_DURATION = 900
```

#### Azure AD Integration (MSAL)

```python
# MSAL Confidential Client for app-only authentication
self.app = msal.ConfidentialClientApplication(
    client_id=client_id,
    client_credential=client_secret,
    authority=f"https://login.microsoftonline.com/{tenant_id}"
)

# Acquire token for Microsoft Graph
result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
access_token = result["access_token"]
```

### 3.4 Security Checks

#### 3.4.1 MFA Compliance Checking

**Algorithm:**

1. **Fetch all users** with `user.authentication.methods` from Graph API
2. **Analyze MFA methods** for each user:
   - **STRONG**: FIDO2 security key, Windows Hello, certificate-based
   - **MODERATE**: Microsoft Authenticator app
   - **WEAK**: SMS, Voice call
   - **NONE**: No MFA registered
3. **Check compliance rules**:
   - Admins MUST have MFA (STRONG or MODERATE)
   - Regular users target 95% MFA enrollment
4. **Generate compliance alerts**:
   - Admin without MFA → CRITICAL
   - Admin with weak MFA → HIGH
   - User without MFA → tracked, no alert

```python
STRENGTH_PRIORITY = {
    MFAStrengthLevel.STRONG: 3,      # FIDO2, Windows Hello
    MFAStrengthLevel.MODERATE: 2,    # Authenticator app
    MFAStrengthLevel.WEAK: 1,        # SMS/Voice
    MFAStrengthLevel.NONE: 0,
}
```

#### 3.4.2 Conditional Access Policy Analysis

**Detection Logic:**

| Check | Description | Severity |
|-------|-------------|----------|
| Policy Disabled | CA policy switched from enabled to disabled | HIGH |
| MFA Removed | Grant controls no longer require MFA | CRITICAL |
| Scope Broadened | Changed from specific apps to "All apps" | HIGH |
| Admin Bypass | Exclude directory roles from MFA | CRITICAL |
| Legacy Auth | No policy blocking legacy authentication | MEDIUM |
| Risk-Based | No sign-in risk conditions configured | LOW |

**Security Score Calculation:**

```python
def calculate_security_score(analysis: dict) -> int:
    score = 50  # Base score

    if analysis["is_mfa_required"]:
        score += 20
    if analysis["applies_to_all_users"]:
        score += 10
    if analysis["requires_compliant_device"]:
        score += 10
    if analysis["requires_high_risk_level"]:
        score += 5
    if analysis["has_location_conditions"]:
        score += 5

    return min(100, score)
```

#### 3.4.3 OAuth App Risk Assessment

**Risk Factors:**

```python
HIGH_RISK_PERMISSIONS = [
    "Mail.Read",           # Can read all user emails
    "Mail.ReadWrite",      # Can read/write all emails
    "User.Read.All",       # Can read all user profiles
    "Group.Read.All",      # Can read all groups
    "Files.Read.All",      # Can read all files
    "Calendars.Read",      # Can read calendars
]

RISK_SCORING = {
    "unverified_publisher": 30,
    "mail_access": 25,
    "user_read_all": 20,
    "files_read_all": 20,
    "admin_consented": 15,
    "high_permission_count": 10,
}
```

**Risk Levels:**
- **CRITICAL (80-100)**: Mail access + unverified publisher
- **HIGH (60-79)**: User.Read.All + unverified
- **MEDIUM (40-59)**: Some high-risk permissions
- **LOW (0-39)**: Standard permissions, verified publisher

#### 3.4.4 Mailbox Rule Monitoring

**Suspicious Patterns:**

```python
SUSPICIOUS_PATTERNS = {
    "external_forward": {
        "check": "forward_to contains external domain",
        "severity": "HIGH"
    },
    "hidden_redirect": {
        "check": "redirect_to + move to hidden folder",
        "severity": "CRITICAL"
    },
    "suspicious_auto_reply": {
        "check": "auto_reply contains external link",
        "severity": "MEDIUM"
    },
    "outside_hours": {
        "check": "created outside 6 AM - 10 PM",
        "severity": "LOW"
    }
}
```

#### 3.4.5 Login Anomaly Detection

**Impossible Travel Detection:**

```python
def detect_impossible_travel(prev_loc, prev_time, curr_loc, curr_time):
    # Haversine formula for distance
    distance_km = haversine_distance(prev_loc, curr_loc)

    # Minimum travel time at 900 km/h (flight speed)
    min_travel_time_min = (distance_km / 900) * 60

    # Actual time difference
    actual_time_min = (curr_time - prev_time).total_seconds() / 60

    # Detection
    is_impossible = actual_time_min < min_travel_time_min

    # Risk score: 100 - (actual_time / min_time * 100)
    risk_score = 100 - (actual_time_min / min_travel_time_min * 100)

    return is_impossible, risk_score
```

**Brute Force Detection:**

```python
BRUTE_FORCE_THRESHOLDS = {
    "warning": 3,      # 3+ failures in 24h → MEDIUM
    "alert": 5,        # 5+ failures in 24h → HIGH
    "critical": 10,    # 10+ failures in 24h → CRITICAL
}
```

**Per-Tenant Approved Countries:**

Organizations can configure a list of approved country codes for each tenant. When a login occurs from a country not in the approved list, an alert is generated. This feature allows organizations to restrict logins to specific geographic regions, providing an additional layer of security.

- Configuration: Tenants can set `approved_countries` as a JSON list of country codes (e.g., `["US", "CA", "GB"]`)
- Alerting: Logins from non-approved countries trigger an `UNAPPROVED_COUNTRY` alert type
- UI: Users can configure approved countries in the Tenants settings page (comma-separated country codes)
- API: Accessible via `/api/v1/tenants/{id}/approved-countries`

### 3.8 Endpoint Agent Architecture

The SpecterDefence Windows Agent (C#/.NET 8) provides granular visibility into endpoint activity without requiring a kernel driver or third-party dependencies like Sysmon.

#### 1. Enrollment & Authentication
- **Initial Enrollment**: The agent uses a one-time, tenant-scoped **Enrollment Token** to register via `POST /endpoints/enroll`.
- **Identity**: On successful enrollment, the server returns a unique `DeviceId` and a secure `DeviceToken`.
- **Authorization**: All subsequent calls (heartbeat, events) require the `X-Device-Token` header. The backend validates this token against the hashed version in the database.

#### 2. Event Monitoring (Native Windows APIs)
The agent uses the `EventLogWatcher` class to subscribe to specific event channels:
- **Security Channel (4688)**: Captures process creation events, including command lines.
- **PowerShell Channel (4104)**: Captures de-obfuscated script block content.

#### 3. Local Buffering & Ingestion
To prevent data loss during network instability:
- All detected events are immediately serialized and stored in a local **SQLite** database (`agent.db`).
- A background **Telemetry Uploader** service pulls batches of events periodically.
- Events are deleted from the local buffer only after a `200 OK` response from the backend.

#### 4. Heartbeat logic
- The agent reports its health, OS version, and agent version every 5 minutes.
- The backend updates the `last_heartbeat` timestamp in the `endpoint_devices` table.
- Devices that haven't reported in over 10 minutes are flagged as "Offline" in the dashboard.


#### Connection Flow

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  SpecterDef  │───▶│  MSAL Auth       │───▶│  Microsoft Graph │
│  ence        │    │  (Client Creds)  │    │  API             │
└──────────────┘    └──────────────────┘    └──────────────────┘
       │                                            │
       │ 1. POST /token                             │
       │    client_id, client_secret, scope=.default │
       │◀─────────────access_token──────────────────┤
       │                                            │
       │ 2. GET /users?$select=...                  │
       │    Authorization: Bearer {token}           │
       │◀─────────────user data─────────────────────┤
```

#### API Endpoints Used

| Endpoint | Purpose | Permission Required |
|----------|---------|---------------------|
| `GET /organization` | Validate tenant info | Organization.Read.All |
| `GET /users` | List all users | User.Read.All |
| `GET /users/{id}/authentication/methods` | MFA status | UserAuthenticationMethod.Read.All |
| `GET /identity/conditionalAccess/policies` | CA policies | Policy.Read.All |
| `GET /servicePrincipals` | OAuth apps | Application.Read.All |
| `GET /users/{id}/mailFolders/inbox/messageRules` | Mailbox rules | MailboxSettings.Read |
| `GET /auditLogs/signIns` | Sign-in logs | AuditLog.Read.All |
| `GET /auditLogs/directoryAudits` | Directory changes | AuditLog.Read.All |

#### Rate Limiting and Pagination

```python
# Rate limiting handling
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    await asyncio.sleep(retry_after)

# Pagination with @odata.nextLink
async def fetch_all_pages(url, headers):
    results = []
    while url:
        response = await client.get(url, headers=headers)
        data = response.json()
        results.extend(data.get("value", []))
        url = data.get("@odata.nextLink")  # Continue if more pages
    return results

# Default timeout and limits
TIMEOUT = 30.0  # seconds
MAX_EVENTS_PER_BATCH = 1000
```

### 3.6 Alerting System

#### Alert Rules Engine

```python
class AlertRuleModel(Base):
    event_types: Mapped[list[str]]  # ["impossible_travel", "brute_force"]
    min_severity: Mapped[SeverityLevel]  # LOW, MEDIUM, HIGH, CRITICAL
    cooldown_minutes: Mapped[int]  # Deduplication window
    is_active: Mapped[bool]
```

**Rule Matching:**

```python
def find_matching_rules(event_type, severity, tenant_id):
    query = select(AlertRuleModel).where(
        AlertRuleModel.is_active == True,
        AlertRuleModel.event_types.contains([event_type]),
        AlertRuleModel.min_severity <= severity,
        or_(
            AlertRuleModel.tenant_id == tenant_id,
            AlertRuleModel.tenant_id.is_(None)  # Global rules
        )
    )
    return db.execute(query).scalars().all()
```

#### Deduplication Logic

```python
def generate_dedup_hash(event_type, user_email, tenant_id, metadata):
    key_parts = [
        event_type,
        user_email or "",
        tenant_id or "",
    ]

    # Include location for travel alerts
    if "previous_location" in metadata and "current_location" in metadata:
        key_parts.extend([
            str(metadata["previous_location"].get("country", "")),
            str(metadata["current_location"].get("country", "")),
        ])

    # Include IP for IP-related alerts
    if "ip_address" in metadata:
        key_parts.append(str(metadata["ip_address"]))

    return hashlib.sha256("|".join(key_parts).encode()).hexdigest()

# Check for duplicate within cooldown period
async def is_duplicate(dedup_hash, rule, tenant_id):
    cooldown_until = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
    existing = await db.execute(
        select(AlertHistoryModel).where(
            AlertHistoryModel.dedup_hash == dedup_hash,
            AlertHistoryModel.sent_at >= cooldown_until,
            AlertHistoryModel.rule_id == rule.id
        )
    )
    return existing.scalar_one_or_none() is not None
```

#### Notification Channels

**Discord Webhook Format:**

```python
embed = {
    "title": f"🚨 Impossible Travel Detected",
    "description": "User logged in from USA and China within 10 minutes",
    "color": 16711680,  # Red for CRITICAL
    "fields": [
        {"name": "👤 User", "value": "admin@company.com", "inline": True},
        {"name": "⚡ Severity", "value": "CRITICAL", "inline": True},
        {"name": "📏 Distance", "value": "11,500 km", "inline": True},
        {"name": "⏱️ Time", "value": "10 min (need 766 min)", "inline": True},
    ],
    "timestamp": "2024-01-15T10:30:00Z",
    "footer": {"text": "SpecterDefence • Impossible Travel"}
}
```

#### Alert History Tracking

```python
class AlertHistoryModel(Base):
    rule_id: Mapped[UUID]           # Which rule triggered
    webhook_id: Mapped[UUID]        # Where it was sent
    tenant_id: Mapped[str]          # Affected tenant
    severity: Mapped[SeverityLevel]
    event_type: Mapped[str]
    user_email: Mapped[str]
    title: Mapped[str]
    message: Mapped[str]
    dedup_hash: Mapped[str]         # For deduplication lookup
    sent_at: Mapped[datetime]
```

### 3.7 Encryption and Security

#### Credential Encryption

**Algorithm**: Fernet (AES-128-CBC with HMAC-SHA256) with PBKDF2 key derivation

```python
class EncryptionService:
    def __init__(self):
        # OWASP 2023: 600,000 iterations for SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,  # 16 bytes, derived from ENCRYPTION_SALT
            iterations=600000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        return self.fernet.decrypt(encrypted).decode()
```

**Encrypted Fields:**
- `TenantModel.client_secret` - Azure AD app secret
- `AlertWebhookModel.webhook_url` - Discord webhook URLs

#### Security Headers (Applied by Default)

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-Frame-Options | DENY | Prevent clickjacking |
| X-XSS-Protection | 1; mode=block | Legacy XSS protection |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | HSTS |
| Content-Security-Policy | default-src 'self'; ... | XSS mitigation |
| Referrer-Policy | strict-origin-when-cross-origin | Privacy |
| Permissions-Policy | geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=() | Disable browser features |

Additionally, `RequestLoggingMiddleware` is active by default, logging all HTTP requests with method, path, status code, and duration.

---

## 4. Data Models

### 4.1 User Model (Local Authentication)

```python
class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
```

### 4.2 Tenant Model

```python
class TenantModel(Base):
    __tablename__ = "tenants"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Display Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Azure AD Credentials (ENCRYPTED client_secret)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(500), nullable=False)

    # Security Configuration
    approved_countries: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connection_status: Mapped[str] = mapped_column(String(20), default="unknown")
    connection_error: Mapped[str] = mapped_column(String(500), nullable=True)
    last_health_check: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
```

### 4.3 Alert Models

#### Alert Rule

```python
class AlertRuleModel(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(ARRAY(String(50)))  # ["impossible_travel", "brute_force"]
    min_severity: Mapped[SeverityLevel] = mapped_column(SQLEnum(SeverityLevel), default=SeverityLevel.MEDIUM)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

#### Alert Webhook

```python
class AlertWebhookModel(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)  # ENCRYPTED
    webhook_type: Mapped[WebhookType] = mapped_column(SQLEnum(WebhookType), default=WebhookType.DISCORD)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

#### Alert History

```python
class AlertHistoryModel(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_rules.id"))
    webhook_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_webhooks.id"))
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"))
    severity: Mapped[SeverityLevel] = mapped_column(SQLEnum(SeverityLevel))
    event_type: Mapped[str] = mapped_column(String(50))
    user_email: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text)
    alert_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    dedup_hash: Mapped[str] = mapped_column(String(64), index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
```

### 4.4 SharePoint Models

```python
class SharePointSharingModel(Base):
    __tablename__ = "sharepoint_sharing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    audit_log_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Event Info
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Resource Info
    site_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Actor Info
    user_email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    
    # Sharing Details
    sharing_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    share_link_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
```

### 4.5 Endpoint Models

```python
class EndpointDeviceModel(Base):
    __tablename__ = "endpoint_devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    os_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[DeviceStatus] = mapped_column(SQLEnum(DeviceStatus), nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class EndpointEventModel(Base):
    __tablename__ = "endpoint_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("endpoint_devices.id"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    event_type: Mapped[EndpointEventType] = mapped_column(SQLEnum(EndpointEventType))
    severity: Mapped[EndpointEventSeverity] = mapped_column(SQLEnum(EndpointEventSeverity))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    process_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    command_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### 4.6 Audit Log Models

```python
class AuditLogModel(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)

    # Event Info
    activity_display_name: Mapped[str] = mapped_column(String(255))
    activity_datetime: Mapped[datetime] = mapped_column(DateTime, index=True)
    activity_type: Mapped[str] = mapped_column(String(100))

    # Actor
    actor_type: Mapped[str] = mapped_column(String(50))
    actor_name: Mapped[str] = mapped_column(String(255))
    actor_id: Mapped[str] = mapped_column(String(255))

    # Target
    target_name: Mapped[str | None] = mapped_column(String(255))
    target_id: Mapped[str | None] = mapped_column(String(255))
    target_type: Mapped[str | None] = mapped_column(String(100))

    # Result
    result: Mapped[str] = mapped_column(String(50))
    result_reason: Mapped[str | None] = mapped_column(String(500))

    # Location
    ip_address: Mapped[str | None] = mapped_column(String(50))
    location_city: Mapped[str | None] = mapped_column(String(100))
    location_country: Mapped[str | None] = mapped_column(String(2))
    location_latitude: Mapped[float | None] = mapped_column(Float)
    location_longitude: Mapped[float | None] = mapped_column(Float)

    # Raw Data
    raw_data: Mapped[dict] = mapped_column(JSONB)
```

---

## 5. API Endpoints

### 5.1 Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/local/login` | Login with username/password, returns JWT |
| POST | `/api/v1/auth/local/logout` | Logout (client discards token) |
| GET | `/api/v1/auth/local/me` | Get current user info |
| GET | `/api/v1/auth/local/check` | Quick auth check |
| POST | `/api/v1/auth/local/change-password` | Change password |

### 5.2 Tenants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tenants` | List all tenants |
| POST | `/api/v1/tenants` | Register new tenant |
| POST | `/api/v1/tenants/validate` | Pre-creation validation |
| GET | `/api/v1/tenants/{id}` | Get tenant details |
| PATCH | `/api/v1/tenants/{id}` | Update tenant |
| DELETE | `/api/v1/tenants/{id}` | Delete tenant |
| POST | `/api/v1/tenants/{id}/health-check` | Run health check |
| POST | `/api/v1/tenants/{id}/validate` | Validate credentials |
| POST | `/api/v1/tenants/health-check/all` | Health check all tenants |

### 5.3 MFA Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mfa-report/` | Get enrollment summary |
| GET | `/api/v1/mfa-report/users` | List MFA users |
| GET | `/api/v1/mfa-report/users-without-mfa` | Users without MFA |
| GET | `/api/v1/mfa-report/admins-without-mfa` | Critical: Admins without MFA |
| GET | `/api/v1/mfa-report/method-distribution` | MFA method distribution |
| GET | `/api/v1/mfa-report/strength-distribution` | MFA strength distribution |
| GET | `/api/v1/mfa-report/compliance-report` | Full compliance report |
| GET | `/api/v1/mfa-report/trends` | Get enrollment trends |
| POST | `/api/v1/mfa-report/scan` | Trigger MFA scan |
| POST | `/api/v1/mfa-report/users/{id}/exemption` | Set MFA exemption for user |
| GET | `/api/v1/mfa-report/alerts` | List MFA compliance alerts |
| POST | `/api/v1/mfa-report/alerts/{id}/resolve` | Resolve MFA alert |

### 5.4 Conditional Access

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ca-policies/` | List CA policies |
| GET | `/api/v1/ca-policies/{id}` | Get policy details |
| GET | `/api/v1/ca-policies/changes` | List policy changes |
| POST | `/api/v1/ca-policies/scan` | Trigger policy scan |
| GET | `/api/v1/ca-policies/tenants/{id}/policies` | Tenant-specific CA policies |
| GET | `/api/v1/ca-policies/tenants/{id}/disabled` | Disabled policies for tenant |
| GET | `/api/v1/ca-policies/tenants/{id}/mfa` | MFA policies for tenant |
| GET | `/api/v1/ca-policies/tenants/{id}/summary` | Policy summary for tenant |
| GET | `/api/v1/ca-policies/alerts` | CA policy alerts |
| POST | `/api/v1/ca-policies/alerts/{id}/acknowledge` | Acknowledge alert |
| GET/POST | `/api/v1/ca-policies/tenants/{id}/baseline` | Baseline configuration |

### 5.5 OAuth Apps

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/oauth-apps/` | List OAuth apps |
| GET | `/api/v1/oauth-apps/{id}` | Get app details |
| POST | `/api/v1/oauth-apps/scan` | Trigger app scan |
| GET | `/api/v1/oauth-apps/tenants/{id}/apps` | Tenant OAuth apps |
| GET | `/api/v1/oauth-apps/tenants/{id}/suspicious` | Suspicious apps for tenant |
| GET | `/api/v1/oauth-apps/tenants/{id}/summary` | Apps summary for tenant |
| GET | `/api/v1/oauth-apps/alerts` | OAuth app alerts |
| POST | `/api/v1/oauth-apps/alerts/{id}/acknowledge` | Acknowledge alert |
| GET | `/api/v1/oauth-apps/{id}/permissions` | App permissions detail |
| POST | `/api/v1/oauth-apps/{id}/revoke` | Revoke app |

### 5.6 Mailbox Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mailbox-rules/` | List mailbox rules |
| GET | `/api/v1/mailbox-rules/suspicious` | Suspicious rules |
| POST | `/api/v1/mailbox-rules/scan` | Trigger rule scan |
| GET | `/api/v1/mailbox-rules/tenants/{id}/rules` | Tenant mailbox rules |
| GET | `/api/v1/mailbox-rules/tenants/{id}/suspicious` | Suspicious rules for tenant |
| GET | `/api/v1/mailbox-rules/tenants/{id}/summary` | Rules summary for tenant |
| GET | `/api/v1/mailbox-rules/alerts` | Mailbox rule alerts |
| POST | `/api/v1/mailbox-rules/alerts/{id}/acknowledge` | Acknowledge alert |

### 5.7 Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts/rules` | List alert rules |
| POST | `/api/v1/alerts/rules` | Create alert rule |
| GET | `/api/v1/alerts/rules/{id}` | Get specific rule |
| PUT | `/api/v1/alerts/rules/{id}` | Update alert rule |
| PATCH | `/api/v1/alerts/rules/{id}` | Patch alert rule |
| GET | `/api/v1/alerts/webhooks` | List webhooks |
| POST | `/api/v1/alerts/webhooks` | Create webhook |
| DELETE | `/api/v1/alerts/webhooks/{id}` | Delete webhook |
| GET | `/api/v1/alerts/history` | Alert history |
| POST | `/api/v1/alerts/webhooks/{id}/test` | Test webhook |

### 5.8 SharePoint & DLP

#### SharePoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/sharepoint/metrics` | Get SharePoint sharing metrics |
| GET | `/api/v1/sharepoint/sharing-links` | List active sharing links |
| GET | `/api/v1/sharepoint/debug` | Debug endpoint (remove in production) |

#### DLP / Insider Threat

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dlp/` | List DLP events |
| GET | `/api/v1/dlp/stats` | Get DLP statistics |

### 5.9 Endpoint Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/endpoints/devices` | List enrolled devices |
| POST | `/api/v1/endpoints/enroll` | Enroll a new device |
| POST | `/api/v1/endpoints/generate-token` | Generate enrollment token |
| POST | `/api/v1/endpoints/heartbeat` | Device heartbeat |
| POST | `/api/v1/endpoints/events` | Report endpoint events |
| GET | `/api/v1/endpoints/events` | List security events |
| GET | `/api/v1/endpoints/devices/{id}/events` | Device-specific events |
| GET | `/api/v1/endpoints/summary` | Endpoint summary stats |

### 5.10 WebSocket

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/api/v1/ws/ws/alerts` | Real-time alert stream |
| GET | `/api/v1/ws/ws/stats` | WebSocket connection stats |

**WebSocket Message Types:**

```json
// Client -> Server
{"type": "ping"}
{"type": "acknowledge", "alert_id": "uuid"}
{"type": "subscribe", "filters": {"severity": ["HIGH", "CRITICAL"]}}
{"type": "get_stats"}

// Server -> Client
{"type": "connection", "status": "connected", "client_id": "..."}
{"type": "pong", "timestamp": "2024-01-15T10:30:00Z"}
{"type": "alert", "severity": "CRITICAL", "title": "...", "metadata": {...}}
```

### 5.11 Health Checks & Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/api/v1/health/` | Detailed health info |
| GET | `/api/v1/dashboard/summary` | Dashboard summary |
| GET | `/api/v1/dashboard/login-timeline` | Login activity timeline |
| GET | `/api/v1/dashboard/geo-heatmap` | Geo heatmap data |
| GET | `/api/v1/dashboard/successful-login-locations` | Successful login locations |
| GET | `/api/v1/dashboard/anomaly-trend` | Anomaly trend data |
| GET | `/api/v1/dashboard/top-risk-users` | Top risk users |
| GET | `/api/v1/dashboard/alert-volume` | Alert volume data |
| GET | `/api/v1/dashboard/anomaly-breakdown` | Anomaly type breakdown |
| GET | `/api/v1/dashboard/full` | All dashboard data in one request |
| POST | `/api/v1/dashboard/export` | Export dashboard data |
| GET | `/api/v1/dashboard/export/download/{format}` | Download export |

### 5.12 Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/monitoring/websites/*` | Website monitoring CRUD |
| GET/POST | `/api/v1/monitoring/ssl/*` | SSL certificate monitoring |
| GET/POST | `/api/v1/monitoring/domains/*` | Domain registration monitoring |

### 5.13 Diagnostics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/diagnostics/summary` | Data ingestion diagnostics summary |
| GET | `/api/v1/diagnostics/audit-logs` | Recent audit logs |
| GET | `/api/v1/diagnostics/login-analytics` | Recent login analytics |

### 5.14 Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST/PATCH/DELETE | `/api/v1/settings/*` | Full settings CRUD (system, preferences, detection, API keys, config import/export) |

### 5.15 Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST/PATCH/DELETE | `/api/v1/users/*` | User management CRUD (list, create, update, tenant assignment) |

### 5.16 Mailbox Security

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mailbox-security/events` | Mailbox rule events |
| GET | `/api/v1/mailbox-security/access` | Non-owner mailbox access |
| GET | `/api/v1/mailbox-security/stats` | Mailbox security statistics |

---

## 6. Frontend (React)

### 6.1 Tech Stack

| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool |
| React Router | Client-side routing |
| TanStack Query | Server state management |
| Zustand | Client state management (with persist middleware) |
| Tailwind CSS | Styling |
| Recharts | Charts and visualizations |
| Leaflet | Map visualization |

### 6.2 Project Structure

```
frontend/
├── src/
│   ├── main.tsx              # Entry point, PWA service worker
│   ├── App.tsx               # Router and layout configuration
│   ├── index.css             # Global styles
│   │
│   ├── components/           # Reusable components
│   │   ├── Layout.tsx        # Main layout with sidebar
│   │   ├── ProtectedRoute.tsx # Auth guard
│   │   ├── Sidebar.tsx       # Navigation sidebar
│   │   ├── Navigation.tsx    # Navigation component
│   │   ├── PageHeader.tsx    # Page header component
│   │   ├── StatsCard.tsx     # Dashboard stat cards
│   │   ├── AlertCard.tsx     # Alert display cards
│   │   ├── AlertFeed.tsx     # Alert feed component
│   │   ├── AnomalyCard.tsx   # Anomaly display cards
│   │   ├── MobileAlertCard.tsx # Mobile alert cards
│   │   ├── MobileNav.tsx     # Mobile navigation
│   │   ├── LoginMap.tsx      # Login map visualization
│   │   ├── LoginTimeline.tsx # Login timeline component
│   │   ├── FilterPanel.tsx   # Filter panel
│   │   ├── ChangePasswordDialog.tsx # Password change dialog
│   │   ├── charts/          # Chart components
│   │   │   ├── AlertVolume.tsx
│   │   │   ├── AnomalyBreakdown.tsx
│   │   │   ├── AnomalyTrend.tsx
│   │   │   ├── GeoHeatmap.tsx
│   │   │   ├── LoginTimeline.tsx
│   │   │   ├── TopRiskUsers.tsx
│   │   │   └── index.ts
│   │   └── settings/        # Settings components
│   │       ├── AlertRuleBuilder.tsx
│   │       ├── ApiKeyManager.tsx
│   │       ├── ConfigImportExport.tsx
│   │       ├── DataDiagnostics.tsx
│   │       ├── DetectionSettings.tsx
│   │       ├── SystemSettings.tsx
│   │       ├── UserPreferences.tsx
│   │       ├── WebhookManager.tsx
│   │       └── index.ts
│   │
│   ├── pages/                # Route pages (18 total)
│   │   ├── Dashboard.tsx     # Main dashboard
│   │   ├── Login.tsx         # Login page
│   │   ├── Tenants.tsx       # Tenant management
│   │   ├── LoginAnalytics.tsx # Login analysis
│   │   ├── Anomalies.tsx     # Anomaly detection view
│   │   ├── MapPage.tsx       # Geographic view
│   │   ├── AlertFeed.tsx     # Real-time alerts
│   │   ├── Settings.tsx      # System settings
│   │   ├── CAPolicies.tsx    # Conditional Access policies
│   │   ├── MailboxRules.tsx  # Mailbox rule monitoring
│   │   ├── MFAReport.tsx     # MFA compliance report
│   │   ├── OAuthApps.tsx     # OAuth application risk
│   │   ├── Monitoring.tsx    # Website/SSL/domain monitoring
│   │   ├── SharePoint.tsx    # SharePoint sharing analytics
│   │   ├── InsiderThreat.tsx # DLP/insider threat view
│   │   ├── MailboxSecurity.tsx # Mailbox security monitoring
│   │   ├── Endpoints.tsx    # Endpoint agent management
│   │   └── Users.tsx        # User management
│   │
│   ├── store/                # State management
│   │   └── appStore.ts       # Zustand store (with persist middleware)
│   │
│   ├── hooks/                # Custom hooks
│   │   ├── useAuth.ts        # Authentication hook
│   │   ├── useWebSocket.ts   # WebSocket connection
│   │   ├── useApi.ts         # API data fetching (tenants, etc.)
│   │   ├── useDashboard.ts   # Dashboard data hook
│   │   ├── useOffline.ts     # Offline state hook
│   │   └── useSettings.ts    # Settings hook
│   │
│   ├── lib/                  # Utilities
│   │   ├── api.ts            # API client (axios/fetch)
│   │   ├── constants.ts      # App constants
│   │   └── utils.ts          # Helper functions
│   │
│   └── types/                # TypeScript types
│       └── index.ts          # Shared type definitions
│
├── public/                   # Static assets
│   ├── icons/                # PWA icons
│   ├── manifest.json         # PWA manifest
│   └── service-worker.js     # Service worker for PWA
│
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

### 6.3 Key Components

#### Authentication Flow

```typescript
// ProtectedRoute.tsx
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Login.tsx
async function handleLogin(username: string, password: string) {
  const response = await api.post('/auth/local/login', { username, password });
  const { access_token } = response.data;

  localStorage.setItem('token', access_token);
  useAppStore.getState().setAuthenticated(true);
}
```

#### WebSocket Alert Feed

```typescript
// useWebSocket.ts
export function useWebSocket(filters?: AlertFilters) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`wss://api.specterdefence/ws/alerts?severity=${filters?.severity}`);

    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'alert') {
        setAlerts(prev => [data, ...prev]);
      }
    };

    return () => ws.close();
  }, [filters]);

  return { alerts, connected };
}
```

#### State Management (Zustand)

```typescript
// store/appStore.ts — uses persist middleware for localStorage persistence
interface AppState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  login: (token: string) => void;
  logout: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'light',            // default theme is 'light'
      sidebarOpen: true,
      user: null,
      token: null,
      isAuthenticated: false,
      // ... actions
    }),
    {
      name: 'specterdefence-storage',
      partialize: (state) => ({
        theme: state.theme,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

---

## 7. Deployment Architecture

### 7.1 Kubernetes Setup

SpecterDefence is deployed using raw YAML manifests in the `k8s/prod/` directory. There is no Helm chart — the deployment uses straightforward Kubernetes manifests applied via `kubectl apply -f k8s/prod/`.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES CLUSTER (k3s)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Namespace: specterdefence                                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Ingress (Traefik)                              │  │
│  │    Host: specterdefence.digitaladrenalin.net (marketing site)         │  │
│  │    Host: app.specterdefence.digitaladrenalin.net (app)                │  │
│  │    TLS: Let's Encrypt (cert-manager)                                  │  │
│  └──────────────────────────────┬───────────────────────────────────────┘  │
│                                 │                                           │
│           ┌─────────────────────┼─────────────────────┐                    │
│           │                     │                     │                    │
│  ┌────────▼────────┐  ┌─────────▼────────┐  ┌────────▼────────┐           │
│  │   API Service   │  │ Frontend Service │  │  Collector Job  │           │
│  │   ClusterIP:80  │  │  ClusterIP:80    │  │   CronJob       │           │
│  └────────┬────────┘  └─────────┬────────┘  └────────┬────────┘           │
│           │                     │                     │                    │
│  ┌────────▼────────┐  ┌─────────▼────────┐           │                    │
│  │   API Pod        │  │  Frontend Pod   │           │                    │
│  │  (FastAPI)       │  │   (Nginx)       │           │                    │
│  │   Port: 8000    │  │   Port: 80      │           │                    │
│  │   Replicas: 1   │  │   Replicas: 1   │  ┌────────▼────────┐           │
│  │                 │  │                  │  │  Collector Pod  │           │
│  │  Resources:     │  │  Resources:      │  │  (Runs every    │           │
│  │  CPU: 250m-1    │  │  CPU: 100m-500m  │  │   5 minutes)   │           │
│  │  Mem: 512Mi-1Gi │  │  Mem: 128Mi-256Mi│  └─────────────────┘           │
│  └─────────────────┘  └──────────────────┘                                │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Secrets (External)                                 │ │
│  │  specterdefence-secrets:                                              │ │
│  │    - SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL                         │ │
│  │    - ENCRYPTION_KEY, ADMIN_PASSWORD_HASH                              │ │
│  │    - KIMI_API_KEY, ABUSEIPDB_API_KEY, ALIENVAULT_OTX_API_KEY          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key deployment characteristics:**
- **Single replica** for API and frontend pods (no HPA, no PodDisruptionBudget, no NetworkPolicy)
- **Traefik ingress** (not Nginx) with `ingressClassName: traefik`
- **Two ingress rules**: marketing site at `specterdefence.digitaladrenalin.net`, app at `app.specterdefence.digitaladrenalin.net`
- **App ingress** routes `/api` and `/ws` to backend, everything else to frontend
- **CronJobs** for collector (every 5 minutes) and security scans
- **No topology spread constraints** or Pod Security Standards labels

### 7.2 Database (PostgreSQL/SQLite)

**Development (SQLite):**
```yaml
# Single file, mounted via PVC
DATABASE_URL: sqlite+aiosqlite:////app/data/specterdefence.db
```

**Production (PostgreSQL):**
```yaml
# External PostgreSQL instance
DATABASE_URL: postgresql+asyncpg://specterdefence:${PASSWORD}@postgresql:5432/specterdefence
```

### 7.3 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes* | auto-generated | App secret for sessions (min 32 chars) |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | Database connection string |
| `ENCRYPTION_KEY` | No | `""` | Base64 Fernet key for credential encryption |
| `ENCRYPTION_SALT` | No | `""` | Salt for key derivation |
| `ADMIN_USERNAME` | No | `admin` | Configurable admin username |
| `ADMIN_PASSWORD_HASH` | Yes* | `""` | Bcrypt hash of admin password |
| `JWT_SECRET_KEY` | Yes* | auto-generated | JWT signing key (min 32 chars) |
| `JWT_EXPIRATION_HOURS` | No | `24` | JWT token expiration in hours |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token expiration in minutes |
| `DEBUG` | No | `false` | Enable debug mode |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |
| `CORS_ORIGINS` | No | defaults to known origins | Allowed CORS origins (no wildcard) |
| `TRUSTED_PROXIES` | No | `[]` | List of trusted proxy IP addresses |
| `APP_NAME` | No | `SpecterDefence` | Application name |
| `APP_VERSION` | No | `0.1.0` | Application version |
| `MS_GRAPH_API_URL` | No | `https://graph.microsoft.com/v1.0` | Microsoft Graph API base URL |
| `MS_LOGIN_URL` | No | `https://login.microsoftonline.com` | Microsoft login URL |
| `ABUSEIPDB_API_KEY` | No | `""` | AbuseIPDB API key for threat intelligence |
| `ALIENVAULT_OTX_API_KEY` | No | `""` | AlienVault OTX API key for threat intelligence |
| `KIMI_API_KEY` | No | `""` | Kimi (Moonshot AI) API key (unused in current code) |

\* Auto-generated with secure defaults if not provided, but validated against weak values in production mode.

### 7.4 Secrets Management

#### Option 1: Kubernetes Secrets (Default)

```bash
kubectl create secret generic specterdefence-secrets \
  --namespace specterdefence \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  --from-literal=ADMIN_PASSWORD_HASH="$(python3 -c 'from src.api.auth_local import get_password_hash; print(get_password_hash("your-password"))')"
```

#### Option 2: External Secrets Operator (Vault)

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: specterdefence-secrets
spec:
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: specterdefence-secrets
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: specterdefence/secret-key
```

### 7.5 CronJob Configuration

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: specterdefence-collector
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: collector
            image: ghcr.io/michaeldigiacomi/specterdefence-backend:latest
            command: ["python", "-m", "src.collector.main"]
            env:
            - name: LOOKBACK_MINUTES
              value: "10"
            - name: MAX_EVENTS_PER_BATCH
              value: "1000"
          restartPolicy: OnFailure
```

---

## 8. Future Considerations

### 8.1 Scalability Points

| Component | Current | Future Scaling |
|-----------|---------|----------------|
| API Server | Single replica (replicas: 1) | HPA: 2-10 replicas based on CPU |
| Database | SQLite/PostgreSQL | Read replicas, connection pooling |
| Collector | Single CronJob | Distributed workers with message queue |
| WebSocket | In-memory | Redis Pub/Sub for multi-replica alert fan-out |
| Caching | None | Consider caching for tenant data, Graph API responses |

### 8.2 Potential Improvements

#### High Priority

1. **Remediate Actions**: Allow SpecterDefence to automatically fix issues:
   - Disable suspicious OAuth apps
   - Block compromised accounts
   - Enable MFA for users
   - Disable forwarding rules

2. **Machine Learning Anomaly Detection**:
   - Baseline user behavior patterns with ML models
   - ML-based impossible travel (learn typical travel patterns per user)
   - UEBA (User and Entity Behavior Analytics)
   - Note: Rule-based anomaly detection (impossible travel, brute force, new country) is already implemented; ML-based detection would add adaptive, per-user baselining on top of the existing rules engine

3. **Threat Intelligence Integration**:
   - Check IPs against threat feeds (AbuseIPDB, VirusTotal)
   - Known-bad OAuth app signatures
   - Domain reputation checking

4. **Audit Log Storage**:
   - Long-term storage in S3/object storage
   - Athena/ClickHouse for query analytics

#### Medium Priority

5. **Multi-Factor Alert Channels**:
   - Email notifications (SendGrid/AWS SES)
   - SMS alerts (Twilio)
   - PagerDuty/Opsgenie integration
   - Microsoft Teams webhooks

6. **Role-Based Access Control (RBAC)**:
   - Multiple user accounts with different permissions
   - Tenant-level access control
   - Read-only analyst role

7. **Reporting and Compliance**:
   - PDF report generation
   - Scheduled email reports
   - Compliance dashboards (SOC2, ISO27001)

8. **API Rate Limiting**:
   - Per-tenant rate limits
   - Graph API quota management
   - Request queuing

### 8.3 Security Hardening Recommendations

| Recommendation | Priority | Implementation |
|----------------|----------|----------------|
| mTLS between services | High | Linkerd/Istio service mesh |
| Secrets rotation automation | High | Vault dynamic secrets |
| Audit logging for all API calls | High | Middleware logging to SIEM |
| Network policies | Medium | Restrict pod-to-pod traffic |
| Pod Security Standards | Medium | Enforce `restricted` profile |
| Vulnerability scanning | Medium | Trivy/Grype in CI/CD |
| SAST/DAST in CI/CD | Medium | SonarQube, OWASP ZAP |
| WAF in front of ingress | Low | ModSecurity/CloudFlare |
| Database encryption at rest | Low | PostgreSQL TDE |
| Field-level encryption for PII | Low | Encrypt email addresses in DB |

### 8.4 Monitoring and Observability

```yaml
# Prometheus metrics to add:
specterdefence_alerts_sent_total{severity, event_type}
specterdefence_graph_api_requests_total{tenant, endpoint, status}
specterdefence_tenant_scan_duration_seconds{tenant_id}
specterdefence_webhook_delivery_duration_seconds{webhook_id}
specterdefence_active_websocket_connections

# Distributed tracing:
- Jaeger/Tempo for request tracing
- Track Graph API call latency per tenant
- Alert processing pipeline tracing
```

---

## Appendix: Quick Reference

### Common Commands

```bash
# Run locally
uvicorn src.main:app --reload

# Run tests
pytest --cov=src --cov-report=html

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Build frontend
cd frontend && npm run build

# Deploy to Kubernetes (raw YAML manifests, no Helm)
kubectl apply -f k8s/prod/

# View logs
kubectl logs -f deployment/specterdefence-backend -n specterdefence
```

### Key Files Reference

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI app entry point |
| `src/config.py` | Environment configuration |
| `src/models/db.py` | SQLAlchemy models |
| `src/api/auth_local.py` | JWT authentication |
| `src/services/encryption.py` | Credential encryption |
| `src/alerts/engine.py` | Alert processing |
| `frontend/src/App.tsx` | React app root |
| `k8s/prod/deployment.yaml` | Kubernetes deployment manifests |
| `k8s/prod/ingress.yaml` | Traefik ingress configuration |

---

*Document Version: 2.0*
*Last Updated: 2026-08-28*
*SpecterDefence Version: 0.1.0*