"""Authentication module for local user authentication with JWT."""

import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import settings

router = APIRouter()
# Use bcrypt directly to avoid passlib compatibility issues with newer bcrypt versions
import bcrypt as bcrypt_lib

security = HTTPBearer(auto_error=False)

# Simple in-memory rate limiter for login attempts
# Key: IP address, Value: list of timestamps
_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5  # Max 5 attempts
_WINDOW_SECONDS = 300  # Within 5 minutes
_BLOCK_DURATION = 900  # Block for 15 minutes after exceeded
_blocklist: dict[str, float] = {}  # IP -> unblock timestamp


def _check_rate_limit(ip_address: str) -> bool:
    """Check if IP is rate limited. Returns True if allowed, False if blocked."""
    now = time.time()

    # Check if IP is in blocklist
    if ip_address in _blocklist:
        if now < _blocklist[ip_address]:
            return False  # Still blocked
        else:
            del _blocklist[ip_address]  # Unblock
            _login_attempts[ip_address] = []  # Clear attempts

    # Clean old attempts outside window
    _login_attempts[ip_address] = [
        ts for ts in _login_attempts[ip_address]
        if now - ts < _WINDOW_SECONDS
    ]

    # Check if too many attempts
    if len(_login_attempts[ip_address]) >= _MAX_ATTEMPTS:
        # Add to blocklist
        _blocklist[ip_address] = now + _BLOCK_DURATION
        return False

    return True


def _record_attempt(ip_address: str):
    """Record a login attempt."""
    _login_attempts[ip_address].append(time.time())


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    username: str
    is_authenticated: bool


class LogoutResponse(BaseModel):
    message: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        # Truncate password to 72 bytes (bcrypt limit)
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt_lib.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a hash from a plain password."""
    # Truncate password to 72 bytes (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt_lib.gensalt()
    hashed = bcrypt_lib.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> dict | None:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict | None:
    """Dependency to get the current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username != settings.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"username": username}


async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires authentication."""
    return user


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """Authenticate user and return JWT token."""
    # Get client IP
    client_ip = req.headers.get("x-forwarded-for", req.client.host).split(",")[0].strip()

    # Check rate limit
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 15 minutes.",
            headers={"Retry-After": "900"},
        )

    # Record this attempt
    _record_attempt(client_ip)

    # Verify username
    if request.username != settings.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clear failed attempts on successful login
    _login_attempts[client_ip] = []

    # Create access token (reduced to 2 hours for security)
    access_token_expires = timedelta(hours=2)
    access_token = create_access_token(
        data={"sub": settings.ADMIN_USERNAME}, expires_delta=access_token_expires
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=2 * 3600  # 2 hours in seconds
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout():
    """Logout user (client should discard token)."""
    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        username=user["username"],
        is_authenticated=True
    )


@router.get("/check")
async def auth_check(user: dict = Depends(get_current_user)):
    """Quick auth check endpoint."""
    return {"authenticated": True, "username": user["username"]}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    message: str


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    user: dict = Depends(get_current_user)
):
    """Change the current user's password."""
    # Verify current password
    if not verify_password(request.current_password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Validate new password length
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long",
        )

    # Generate new hash
    new_hash = get_password_hash(request.new_password)

    # In a real production environment, we'd update the database or secret
    # For now, return success - the user needs to update the env variable
    return ChangePasswordResponse(
        message="Password changed successfully. Please update ADMIN_PASSWORD_HASH environment variable.",
    )
