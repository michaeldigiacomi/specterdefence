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
| **Login Anomaly Detection** | Identify impossible travel, new countries, and brute force attempts |
| **Real-Time Alerting** | WebSocket-based alert streaming with Discord/Slack webhook integration |
| **Audit Log Collection** | Continuous ingestion of M365 audit logs for analysis |

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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Microsoft  │  │   Discord    │  │    Slack     │  │   HashiCorp  │   │
│  │    Graph API │  │   Webhooks   │  │   Webhooks   │  │     Vault    │   │
│  └──────┬───────┘  └──────▲───────┘  └──────▲───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
└─────────┼─────────────────┼─────────────────┼─────────────────┼───────────┘
          │                 │                 │                 │
          │ HTTPS           │ HTTPS           │ HTTPS           │ HTTPS
          │                 │                 │                 │
┌─────────▼─────────────────┴─────────────────┴─────────────────┴───────────┐
│                            SPECTERDEFENCE PLATFORM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
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
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │   PostgreSQL    │  │     Redis       │  │   Encrypted Secrets │  │   │
│  │  │   (SQLAlchemy)  │  │   (Caching)     │  │   (Fernet + PBKDF2) │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
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
│  │   API Pod(s)    │  │  Frontend Pod(s)│  │   Collector CronJob         │ │
│  │   (FastAPI)     │  │    (Nginx)      │  │   (Data Collection)         │ │
│  │   Port: 8000    │  │   Port: 80      │  │   Schedule: */5 * * * *     │ │
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
│                │              │    │  (Cooldown)  │    │ (Discord/    │     │
│                └──────────────┘    └──────────────┘    │  Slack)      │     │
│                                                        └──────────────┘     │
│                                                                             │
│  4. REAL-TIME STREAMING                                                     │
│     ┌────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│     │  WebSocket │◀───│  Alert Feed  │◀───│   New Alert  │                  │
│     │  Clients   │    │  Manager     │    │   Detected   │                  │
│     └────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 External Integrations

| Integration | Protocol | Purpose |
|-------------|----------|---------|
| Microsoft Graph API | HTTPS / OAuth 2.0 | Read tenant data (users, policies, audit logs) |
| Discord Webhooks | HTTPS / JSON | Real-time security alerts |
| Slack Webhooks | HTTPS / JSON | Real-time security alerts |
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
│   ├── dashboard.py        # Dashboard data endpoints
│   └── settings.py         # System settings endpoints
│
├── services/               # Business Logic Layer
│   ├── tenant.py           # Tenant management service
│   ├── encryption.py       # Fernet encryption for secrets
│   ├── mfa_report.py       # MFA tracking and compliance
│   ├── ca_policies.py      # CA policy monitoring
│   ├── oauth_apps.py       # OAuth app risk assessment
│   ├── mailbox_rules.py    # Mailbox rule analysis
│   ├── dashboard.py        # Dashboard aggregation
│   ├── alert_processor.py  # Alert processing logic
│   ├── alert_stream.py     # WebSocket streaming service
│   └── settings.py         # Settings management
│
├── clients/                # External API Clients
│   ├── ms_graph.py         # MSAL + Graph API client
│   ├── mfa_report.py       # MFA-specific Graph queries
│   ├── ca_policies.py      # CA policy Graph queries
│   ├── oauth_apps.py       # OAuth app Graph queries
│   └── mailbox_rules.py    # Mailbox rule Graph queries
│
├── models/                 # Data Models (SQLAlchemy + Pydantic)
│   ├── db.py               # SQLAlchemy ORM models
│   ├── tenant.py           # Pydantic tenant schemas
│   ├── alerts.py           # Alert models and enums
│   ├── mfa_report.py       # MFA enrollment models
│   ├── ca_policies.py      # CA policy models
│   ├── oauth_apps.py       # OAuth app models
│   ├── mailbox_rules.py    # Mailbox rule models
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
│   └── geo_ip.py           # GeoIP lookup utilities
│
└── collector/              # Data Collection Jobs
    ├── main.py             # Collector entry point
    └── o365_feed.py        # Office 365 audit log ingestion
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
        return response

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

### 3.5 Microsoft Graph Integration

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
- `AlertWebhookModel.webhook_url` - Discord/Slack webhook URLs

#### Security Headers (Applied by Default)

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-Frame-Options | DENY | Prevent clickjacking |
| X-XSS-Protection | 1; mode=block | Legacy XSS protection |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | HSTS |
| Content-Security-Policy | default-src 'self'; ... | XSS mitigation |
| Referrer-Policy | strict-origin-when-cross-origin | Privacy |

---

## 4. Data Models

### 4.1 User Model (Local Authentication)

```python
class UserResponse(BaseModel):
    username: str
    is_authenticated: bool

# Stored as environment variables (not in database):
# ADMIN_USERNAME - admin username
# ADMIN_PASSWORD_HASH - bcrypt hash of password
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

### 4.4 OAuth App Models

```python
class OAuthAppModel(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    
    # App Info
    app_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Publisher
    publisher_name: Mapped[str | None] = mapped_column(String(500))
    publisher_type: Mapped[PublisherType] = mapped_column(SQLEnum(PublisherType), default=PublisherType.UNKNOWN)
    is_microsoft_publisher: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified_publisher: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Risk Analysis
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel), default=RiskLevel.LOW)
    status: Mapped[AppStatus] = mapped_column(SQLEnum(AppStatus), default=AppStatus.PENDING_REVIEW)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    
    # Permissions
    permission_count: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_permissions: Mapped[list[str]] = mapped_column(ARRAY(String(255)))
    has_mail_permissions: Mapped[bool] = mapped_column(Boolean, default=False)
    has_user_read_all: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Consent
    consent_count: Mapped[int] = mapped_column(Integer, default=0)
    admin_consented: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_scan_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
```

### 4.5 Audit Log Models

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
| POST | `/api/v1/auth/local/change-password` | Change password |

### 5.2 Tenants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tenants` | List all tenants |
| POST | `/api/v1/tenants` | Register new tenant |
| GET | `/api/v1/tenants/{id}` | Get tenant details |
| PATCH | `/api/v1/tenants/{id}` | Update tenant |
| DELETE | `/api/v1/tenants/{id}` | Delete tenant |
| POST | `/api/v1/tenants/{id}/health-check` | Run health check |
| POST | `/api/v1/tenants/{id}/validate` | Validate credentials |

### 5.3 MFA Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mfa-report/users` | List MFA users |
| GET | `/api/v1/mfa-report/summary` | Get enrollment summary |
| GET | `/api/v1/mfa-report/trends` | Get enrollment trends |
| GET | `/api/v1/mfa-report/admins-without-mfa` | Critical: Admins without MFA |
| POST | `/api/v1/mfa-report/scan` | Trigger MFA scan |

### 5.4 Conditional Access

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ca-policies` | List CA policies |
| GET | `/api/v1/ca-policies/{id}` | Get policy details |
| GET | `/api/v1/ca-policies/summary` | Get policy summary |
| GET | `/api/v1/ca-policies/changes` | List policy changes |
| POST | `/api/v1/ca-policies/scan` | Trigger policy scan |

### 5.5 OAuth Apps

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/oauth-apps` | List OAuth apps |
| GET | `/api/v1/oauth-apps/{id}` | Get app details |
| GET | `/api/v1/oauth-apps/high-risk` | High-risk apps |
| POST | `/api/v1/oauth-apps/scan` | Trigger app scan |

### 5.6 Mailbox Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mailbox-rules` | List mailbox rules |
| GET | `/api/v1/mailbox-rules/suspicious` | Suspicious rules |
| POST | `/api/v1/mailbox-rules/scan` | Trigger rule scan |

### 5.7 Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts/rules` | List alert rules |
| POST | `/api/v1/alerts/rules` | Create alert rule |
| GET | `/api/v1/alerts/webhooks` | List webhooks |
| POST | `/api/v1/alerts/webhooks` | Create webhook |
| GET | `/api/v1/alerts/history` | Alert history |
| POST | `/api/v1/alerts/webhooks/{id}/test` | Test webhook |

### 5.8 WebSocket

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

### 5.9 Health Checks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |

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
| Zustand | Client state management |
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
│   │   ├── Header.tsx        # Top header bar
│   │   ├── StatCard.tsx      # Dashboard stat cards
│   │   ├── AlertCard.tsx     # Alert display cards
│   │   └── Map/              # Map components
│   │
│   ├── pages/                # Route pages
│   │   ├── Dashboard.tsx     # Main dashboard
│   │   ├── Login.tsx         # Login page
│   │   ├── Tenants.tsx       # Tenant management
│   │   ├── LoginAnalytics.tsx # Login analysis
│   │   ├── Anomalies.tsx     # Anomaly detection view
│   │   ├── MapPage.tsx       # Geographic view
│   │   ├── AlertFeed.tsx     # Real-time alerts
│   │   └── Settings.tsx      # System settings
│   │
│   ├── store/                # State management
│   │   └── appStore.ts       # Zustand store (auth, theme)
│   │
│   ├── hooks/                # Custom hooks
│   │   ├── useAuth.ts        # Authentication hook
│   │   ├── useWebSocket.ts   # WebSocket connection
│   │   └── useTenants.ts     # Tenant data fetching
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
// store/appStore.ts
interface AppState {
  isAuthenticated: boolean;
  theme: 'light' | 'dark';
  user: User | null;
  setAuthenticated: (value: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setUser: (user: User | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  isAuthenticated: !!localStorage.getItem('token'),
  theme: localStorage.getItem('theme') as 'light' | 'dark' || 'dark',
  user: null,
  setAuthenticated: (value) => set({ isAuthenticated: value }),
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },
  setUser: (user) => set({ user }),
}));
```

---

## 7. Deployment Architecture

### 7.1 Kubernetes Setup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES CLUSTER (k3s)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Namespace: specterdefence                                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Ingress (Traefik)                              │  │
│  │    Host: specterdefence.digitaladrenalin.net                          │  │
│  │    TLS: Let's Encrypt (cert-manager)                                  │  │
│  │    Rate Limit: 100 req/min                                            │  │
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
│  │   API Pods      │  │  Frontend Pods   │           │                    │
│  │  (FastAPI)      │  │   (Nginx)        │           │                    │
│  │   Port: 8000    │  │   Port: 80       │           │                    │
│  │                 │  │                  │           │                    │
│  │  Resources:     │  │  Resources:      │  ┌────────▼────────┐           │
│  │  CPU: 250m-1    │  │  CPU: 100m-500m  │  │  Collector Pod  │           │
│  │  Mem: 512Mi-1Gi │  │  Mem: 128Mi-256Mi│  │  (Runs every    │           │
│  └─────────────────┘  └──────────────────┘  │   5 minutes)    │           │
│                                             └─────────────────┘           │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Persistent Volume Claims                           │ │
│  │  specterdefence-data (10Gi) - SQLite database storage                 │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Secrets (External)                                 │ │
│  │  specterdefence-secrets:                                              │ │
│  │    - SECRET_KEY                                                       │ │
│  │    - DATABASE_URL                                                     │ │
│  │    - ENCRYPTION_KEY                                                   │ │
│  │    - ENCRYPTION_SALT                                                  │ │
│  │    - ADMIN_PASSWORD_HASH                                              │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Database (PostgreSQL/SQLite)

**Development (SQLite):**
```yaml
# Single file, mounted via PVC
DATABASE_URL: sqlite+aiosqlite:////app/data/specterdefence.db
```

**Production (PostgreSQL):**
```yaml
# Bitnami PostgreSQL subchart
DATABASE_URL: postgresql://specterdefence:${PASSWORD}@postgresql:5432/specterdefence
```

### 7.3 Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SECRET_KEY` | Yes | App secret for sessions | `openssl rand -hex 32` |
| `DATABASE_URL` | Yes | Database connection string | `sqlite:///./data.db` |
| `ENCRYPTION_KEY` | Yes | Fernet key for credential encryption | `Fernet.generate_key()` |
| `ENCRYPTION_SALT` | Yes | Salt for key derivation | `openssl rand -hex 16` |
| `ADMIN_PASSWORD_HASH` | Yes | Bcrypt hash of admin password | `get_password_hash("...")` |
| `JWT_SECRET_KEY` | Yes | JWT signing key | `openssl rand -hex 32` |
| `DEBUG` | No | Enable debug mode | `false` |
| `CORS_ORIGINS` | No | Allowed CORS origins | `https://app.example.com` |
| `KIMI_API_KEY` | No | API key for AI features | `sk-...` |

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
            image: specterdefence-api:latest
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
| API Server | Single replica | HPA: 2-10 replicas based on CPU |
| Database | SQLite/PostgreSQL | Read replicas, connection pooling |
| Collector | Single CronJob | Distributed workers with Redis queue |
| WebSocket | In-memory | Redis Pub/Sub for multi-replica |
| Caching | None | Redis for tenant data, Graph API responses |

### 8.2 Potential Improvements

#### High Priority

1. **Remediate Actions**: Allow SpecterDefence to automatically fix issues:
   - Disable suspicious OAuth apps
   - Block compromised accounts
   - Enable MFA for users
   - Disable forwarding rules

2. **Machine Learning Anomaly Detection**:
   - Baseline user behavior patterns
   - ML-based impossible travel (learn typical travel patterns)
   - UEBA (User and Entity Behavior Analytics)

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

# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml

# View logs
kubectl logs -f deployment/specterdefence -n specterdefence
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
| `k8s-deployment.yaml` | Kubernetes manifests |

---

*Document Version: 1.0*
*Last Updated: 2024-03-04*
*SpecterDefence Version: 0.1.0*
