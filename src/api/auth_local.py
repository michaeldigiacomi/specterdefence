"""Authentication module for local user authentication with JWT."""

import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

# Use bcrypt directly to avoid passlib compatibility issues with newer bcrypt versions
import bcrypt as bcrypt_lib
from src.api.auth_local import get_authorized_tenant
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select

from src.config import settings
from src.database import async_session_maker, get_db
from src.models.user import UserModel

router = APIRouter()

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
        ts for ts in _login_attempts[ip_address] if now - ts < _WINDOW_SECONDS
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


async def get_or_create_admin_user() -> UserModel:
    """Get the admin user from database, or create from env var if not exists."""
    async with async_session_maker() as session:
        # Try to get existing admin user
        result = await session.execute(
            select(UserModel).where(UserModel.username == settings.ADMIN_USERNAME)
        )
        user = result.scalar_one_or_none()

        if user:
            return user

        # Create admin user from environment variable if exists
        if settings.ADMIN_PASSWORD_HASH:
            user = UserModel(
                username=settings.ADMIN_USERNAME,
                password_hash=settings.ADMIN_PASSWORD_HASH,
                is_active=True,
                is_admin=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

        # No admin user exists and no env var set - this is an error condition
        raise RuntimeError(
            "No admin user exists and ADMIN_PASSWORD_HASH is not set. "
            "Please set ADMIN_PASSWORD_HASH environment variable."
        )


async def get_admin_password_hash() -> str:
    """Get the admin password hash from database or env var."""
    try:
        user = await get_or_create_admin_user()
        return user.password_hash
    except RuntimeError:
        # Fall back to env var if no database user exists
        return settings.ADMIN_PASSWORD_HASH


async def update_admin_password(new_password_hash: str) -> None:
    """Update the admin password in the database."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == settings.ADMIN_USERNAME)
        )
        user = result.scalar_one_or_none()

        if user:
            user.password_hash = new_password_hash
            user.updated_at = datetime.now()
        else:
            # Create new admin user with the password
            user = UserModel(
                username=settings.ADMIN_USERNAME,
                password_hash=new_password_hash,
                is_active=True,
                is_admin=True,
            )
            session.add(user)

        await session.commit()


async def update_last_login(username: str) -> None:
    """Update the last login timestamp for a user."""
    async with async_session_maker() as session:
        result = await session.execute(select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()

        if user:
            user.last_login = datetime.now()
            await session.commit()


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
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt_lib.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a hash from a plain password."""
    # Truncate password to 72 bytes (bcrypt limit)
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt_lib.gensalt()
    hashed = bcrypt_lib.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(hours=24)
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict | None:
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
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with async_session_maker() as session:
        result = await session.execute(select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return {"id": user.id, "username": user.username, "is_admin": user.is_admin}


async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires authentication."""
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires admin authentication."""
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def get_authorized_tenant(
    tenant_id: str | None = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db)
) -> str | list[str] | None:
    """Returns requested tenant_id if authorized, or list of authorized tenants."""
    if user.get("is_admin"):
        return tenant_id

    # For standard users, load their assigned tenants
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from src.models.user import UserModel
    
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.tenants)).where(UserModel.id == user["id"])
    )
    db_user = result.scalar()
    
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")
        
    allowed_ids = [str(t.id) for t in db_user.tenants]
    
    if tenant_id:
        if tenant_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Access denied to this tenant")
        return tenant_id
        
    if not allowed_ids:
        # Return a dummy string that won't match any tenant
        return "NONE"
        
    return allowed_ids


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

    async with async_session_maker() as session:
        # Check if first-time admin setup or get existing admin
        if request.username == settings.ADMIN_USERNAME:
            user = await get_or_create_admin_user()
        else:
            result = await session.execute(
                select(UserModel).where(UserModel.username == request.username)
            )
            user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clear failed attempts on successful login
    _login_attempts[client_ip] = []

    # Update last login timestamp
    await update_last_login(request.username)

    # Create access token (reduced to 2 hours for security)
    access_token_expires = timedelta(hours=2)
    access_token = create_access_token(
        data={"sub": request.username}, expires_delta=access_token_expires
    )

    return LoginResponse(
        access_token=access_token, token_type="bearer", expires_in=2 * 3600  # 2 hours in seconds
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(user: dict = Depends(get_current_user)):
    """Logout user (client should discard token)."""
    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(username=user["username"], is_authenticated=True)


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
async def change_password(request: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """Change the current user's password."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == user["username"])
        )
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Verify current password
    if not verify_password(request.current_password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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

    # Save to database
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == user["username"])
        )
        db_user_update = result.scalar_one()
        db_user_update.password_hash = new_hash
        db_user_update.updated_at = datetime.now()
        await session.commit()

    return ChangePasswordResponse(
        message="Password changed successfully. Please log in again with your new password.",
    )
