# SpecterDefence Security Hardening Checklist

This checklist provides actionable security hardening steps for the SpecterDefence platform.

---

## 🔴 Immediate Actions (Before Production)

### 1. Fix Default Secret Keys
**Priority:** CRITICAL  
**File:** `src/config.py`

```python
import secrets
from pydantic import Field, field_validator

class Settings(BaseSettings):
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        min_length=32,
        description="Application secret key"
    )
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        min_length=32,
        description="JWT signing key"
    )
    
    @field_validator('SECRET_KEY', 'JWT_SECRET_KEY')
    @classmethod
    def validate_not_default(cls, v: str) -> str:
        defaults = [
            'change-me-in-production',
            'change-me-in-production-specterdefence-secret-key',
            'your-secret-key-here'
        ]
        if v in defaults or len(v) < 32:
            raise ValueError('Insecure secret key detected. Generate a cryptographically secure key.')
        return v
```

**Verification:**
```bash
python -c "from src.config import settings; print('Key length:', len(settings.SECRET_KEY))"
```

---

### 2. Remove Default Admin Password
**Priority:** CRITICAL  
**File:** `src/config.py`

```python
ADMIN_PASSWORD_HASH: str = Field(
    default="",
    description="bcrypt hash of admin password"
)

@field_validator('ADMIN_PASSWORD_HASH')
@classmethod
def validate_admin_password(cls, v: str) -> str:
    if not v:
        raise ValueError('ADMIN_PASSWORD_HASH must be set. Generate with: python -c "from src.api.auth_local import get_password_hash; print(get_password_hash(\'your-password\'))"')
    # Check against known weak hashes
    weak_hashes = [
        "$2b$12$qaI.IhS84lIGdfXRFU8aZOhLqJqsZbhJt1UFx8rWSjzlHynm53.kK",
    ]
    if v in weak_hashes:
        raise ValueError('Weak/default password hash detected. Generate a new secure password.')
    return v
```

**Generate new password hash:**
```bash
python -c "from src.api.auth_local import get_password_hash; print(get_password_hash('YourStrongPassword123!'))"
```

---

### 3. Enable HTTPS/TLS
**Priority:** CRITICAL  
**File:** `k8s-deployment.yaml`

Update the Ingress to use HTTPS:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: specterdefence
  namespace: specterdefence
  annotations:
    # Traefik v2
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    traefik.ingress.kubernetes.io/router.tls.certresolver: letsencrypt
    traefik.ingress.kubernetes.io/router.middlewares: default-security-headers@kubernetescrd
    
    # Security headers
    traefik.ingress.kubernetes.io/response-headers: |
      Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
      X-Frame-Options: DENY
      X-Content-Type-Options: nosniff
      X-XSS-Protection: 1; mode=block
      Referrer-Policy: strict-origin-when-cross-origin
spec:
  tls:
    - hosts:
        - specterdefence.digitaladrenalin.net
      secretName: specterdefence-tls
  rules:
    - host: specterdefence.digitaladrenalin.net
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: specterdefence
                port:
                  number: 80
```

---

### 4. Implement Rate Limiting
**Priority:** HIGH  
**File:** `src/main.py`, `src/api/auth_local.py`

```bash
# Add to requirements.txt
slowapi==0.1.9
```

```python
# src/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(...)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

```python
# src/api/auth_local.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest):
    """Authenticate user and return JWT token."""
    # ... existing code
```

---

### 5. Restrict CORS Origins
**Priority:** HIGH  
**File:** `src/config.py`

```python
from pydantic import Field, field_validator
from typing import List

class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["https://specterdefence.digitaladrenalin.net"],
        description="Allowed CORS origins"
    )
    
    @field_validator('CORS_ORIGINS')
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        if "*" in v:
            raise ValueError('CORS_ORIGINS cannot contain "*" in production')
        for origin in v:
            if not origin.startswith(('https://', 'http://localhost')):
                raise ValueError(f'CORS origin must use HTTPS: {origin}')
        return v
```

---

## 🟡 Short-term Improvements (1-2 Weeks)

### 6. Fix Encryption Salt
**Priority:** HIGH  
**File:** `src/services/encryption.py`

```python
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self) -> None:
        """Initialize encryption service with key derived from ENCRYPTION_KEY."""
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', settings.SECRET_KEY)
        
        # Use a dedicated encryption salt from environment
        salt_base = getattr(settings, 'ENCRYPTION_SALT', 'specterdefence-salt')
        salt = hashlib.sha256(salt_base.encode()).digest()[:16]
        
        # OWASP 2023 recommended iterations
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self.fernet = Fernet(key)
```

**Add to .env:**
```bash
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_SALT=$(openssl rand -hex 16)
```

---

### 7. Add Security Headers Middleware
**Priority:** MEDIUM  
**File:** `src/main.py` or new `src/middleware/security.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # HSTS (only if using HTTPS)
        if not settings.DEBUG:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'speaker=()'
        )
        
        return response

# Add to app
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["specterdefence.digitaladrenalin.net", "*.digitaladrenalin.net"]
)
```

---

### 8. Implement Audit Logging
**Priority:** MEDIUM  
**File:** `src/services/tenant.py`, new `src/audit/logger.py`

```python
# src/audit/logger.py
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class AuditLogger:
    """Structured audit logging for security events."""
    
    def __init__(self):
        self.logger = logging.getLogger('specterdefence.audit')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for audit logs
        handler = logging.FileHandler('/var/log/specterdefence/audit.log')
        handler.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
    
    def log(self, event_type: str, user: str, resource: str, 
            action: str, details: Optional[Dict[str, Any]] = None,
            result: str = "success"):
        """Log an audit event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user": user,
            "resource": resource,
            "action": action,
            "result": result,
            "details": details or {}
        }
        self.logger.info(json.dumps(event))
    
    def credential_access(self, tenant_id: str, user: str):
        """Log credential access."""
        self.log(
            event_type="CREDENTIAL_ACCESS",
            user=user,
            resource=f"tenant:{tenant_id}",
            action="decrypt_client_secret"
        )

audit_logger = AuditLogger()
```

---

### 9. Implement Token Refresh
**Priority:** MEDIUM  
**File:** `src/api/auth_local.py`

```python
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

REFRESH_TOKEN_EXPIRE_DAYS = 7
ACCESS_TOKEN_EXPIRE_MINUTES = 15

def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        username = payload.get("sub")
        if username != settings.ADMIN_USERNAME:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Issue new tokens
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        new_refresh_token = create_refresh_token(data={"sub": username})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
```

---

## 🟢 Long-term Improvements (1-3 Months)

### 10. Implement MFA
Consider adding TOTP-based MFA for admin authentication.

### 11. Add Database SSL
**File:** `src/database.py`

```python
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    ssl_require=True if not settings.DEBUG else False
)
```

### 12. Network Policies
**File:** `helm/specterdefence/values.yaml`

```yaml
networkPolicy:
  enabled: true
  ingress:
    allowedNamespaces:
      - ingress-nginx
    allowedCIDRs: []
  egress:
    enabled: true
    allowDNS: true
    allowedCIDRs:
      - 20.190.0.0/16  # Microsoft Graph API range
      - 40.126.0.0/18  # Microsoft login
```

### 13. Pod Security Standards
**File:** `helm/specterdefence/values.yaml`

```yaml
podSecurityStandard:
  enforce: "restricted"
  audit: "restricted"
  warn: "restricted"
```

---

## Verification Commands

### Test Security Headers
```bash
curl -I https://specterdefence.digitaladrenalin.net
```

### Test Rate Limiting
```bash
for i in {1..10}; do
  curl -X POST https://specterdefence.digitaladrenalin.net/api/v1/auth/local/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrong"}'
done
```

### Verify TLS Configuration
```bash
nmap --script ssl-enum-ciphers -p 443 specterdefence.digitaladrenalin.net
```

### Check for Default Secrets
```bash
grep -r "change-me-in-production" src/
grep -r "admin123" src/
```

---

## Compliance Checklist

### OWASP Top 10
- [ ] A01: Broken Access Control - Implement RBAC
- [x] A02: Cryptographic Failures - Credentials encrypted at rest
- [x] A03: Injection - SQLAlchemy ORM prevents SQLi
- [ ] A04: Insecure Design - Add rate limiting
- [ ] A05: Security Misconfiguration - Fix default configs
- [x] A06: Vulnerable Components - Dependencies scanned
- [ ] A07: Auth Failures - Add MFA
- [x] A08: Data Integrity - Authenticated encryption
- [ ] A09: Logging Failures - Add audit logging
- [x] A10: SSRF - No user-controlled URLs

### GDPR
- [x] Data Encryption at Rest
- [x] Data Encryption in Transit (with HTTPS fix)
- [ ] Audit Logging
- [ ] Data Retention Policy
- [ ] Right to Erasure Implementation

---

*Last Updated: 2026-03-02*
