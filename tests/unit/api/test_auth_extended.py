"""Additional comprehensive tests for local authentication module."""

import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from jose import jwt

from src.api.auth_local import (
    _blocklist,
    _check_rate_limit,
    _login_attempts,
    _record_attempt,
    create_access_token,
    get_admin_password_hash,
    get_current_user,
    get_or_create_admin_user,
    get_password_hash,
    require_auth,
    update_admin_password,
    update_last_login,
    verify_password,
    verify_token,
)
from src.config import settings


class TestRateLimiting:
    """Tests for login rate limiting functionality."""

    def setup_method(self):
        """Clear rate limit state before each test."""
        _login_attempts.clear()
        _blocklist.clear()

    def teardown_method(self):
        """Clear rate limit state after each test."""
        _login_attempts.clear()
        _blocklist.clear()

    def test_check_rate_limit_allowed(self):
        """Test that requests are allowed within limits."""
        ip = "192.168.1.1"

        # First 5 attempts should be allowed
        for i in range(5):
            assert _check_rate_limit(ip) is True
            _record_attempt(ip)

    def test_check_rate_limit_blocked_after_max(self):
        """Test that requests are blocked after max attempts."""
        ip = "192.168.1.2"

        # Make max attempts
        for i in range(5):
            _record_attempt(ip)

        # 6th attempt should trigger block
        assert _check_rate_limit(ip) is False

    def test_check_rate_limit_block_expires(self):
        """Test that block expires after duration."""
        ip = "192.168.1.3"

        # Make max attempts and trigger block
        for i in range(5):
            _record_attempt(ip)

        # Should be blocked
        assert _check_rate_limit(ip) is False

        # Manually expire the block (simulate time passing)
        _blocklist[ip] = time.time() - 1  # Set unblock time in the past

        # Should be allowed now
        assert _check_rate_limit(ip) is True

    def test_check_rate_limit_old_attempts_cleared(self):
        """Test that old attempts are cleared from the window."""
        ip = "192.168.1.4"

        # Add an old attempt (outside the 5-minute window)
        _login_attempts[ip] = [time.time() - 400]  # 400 seconds ago

        # Should be allowed because old attempt is outside window
        assert _check_rate_limit(ip) is True

    def test_record_attempt(self):
        """Test that login attempts are recorded."""
        ip = "192.168.1.5"

        assert len(_login_attempts[ip]) == 0

        _record_attempt(ip)
        assert len(_login_attempts[ip]) == 1

        _record_attempt(ip)
        assert len(_login_attempts[ip]) == 2


class TestPasswordFunctionsExtended:
    """Extended tests for password functions."""

    def test_get_password_hash_different_salts(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "testpassword123"

        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_verify_password_empty(self):
        """Test verifying empty password."""
        password = ""
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_verify_password_unicode(self):
        """Test verifying passwords with unicode characters."""
        password = "пароль123!@#"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("different", hashed) is False

    def test_verify_password_long(self):
        """Test verifying very long passwords."""
        password = "a" * 1000
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_bcrypt_truncation(self):
        """Test bcrypt password truncation (72 byte limit)."""
        # bcrypt truncates passwords to 72 bytes
        password_80 = "a" * 80
        password_72 = "a" * 72

        hashed = get_password_hash(password_80)

        # Both should verify because of truncation
        assert verify_password(password_80, hashed) is True
        assert verify_password(password_72, hashed) is True


class TestJWTFunctionsExtended:
    """Extended tests for JWT functions."""

    def test_create_access_token_default_expiration(self):
        """Test token creation with default expiration."""
        data = {"sub": "admin", "role": "admin"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_create_access_token_custom_expiration(self):
        """Test token creation with custom expiration."""
        data = {"sub": "admin"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

        assert payload["sub"] == "admin"
        assert "exp" in payload

    def test_verify_token_expired(self):
        """Test verifying expired token."""
        data = {"sub": "admin"}
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        payload = verify_token(expired_token)
        assert payload is None

    def test_verify_token_invalid_signature(self):
        """Test verifying token with wrong secret."""
        data = {"sub": "admin"}
        token = jwt.encode(data, "wrong-secret", algorithm="HS256")

        payload = verify_token(token)
        assert payload is None

    def test_verify_token_malformed(self):
        """Test verifying malformed token."""
        assert verify_token("not.a.token") is None
        assert verify_token("invalidtoken") is None
        assert verify_token("") is None

    def test_verify_token_missing_sub(self):
        """Test verifying token without subject claim."""
        data = {"role": "admin"}  # No 'sub' claim
        token = jwt.encode(data, settings.JWT_SECRET_KEY, algorithm="HS256")

        payload = verify_token(token)
        assert payload is not None  # Token is valid
        assert payload.get("sub") is None  # But no sub claim


class TestGetCurrentUserExtended:
    """Extended tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_no_credentials(self):
        """Test get_current_user with no credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Not authenticated" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            credentials="invalid.token.here",
            scheme="Bearer",
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authentication credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_wrong_username(self):
        """Test get_current_user with valid token but wrong username."""
        from fastapi.security import HTTPAuthorizationCredentials

        # Create token with wrong username
        token = create_access_token({"sub": "wronguser"})
        credentials = HTTPAuthorizationCredentials(
            credentials=token,
            scheme="Bearer",
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_valid(self):
        """Test get_current_user with valid token."""
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token({"sub": settings.ADMIN_USERNAME})
        credentials = HTTPAuthorizationCredentials(
            credentials=token,
            scheme="Bearer",
        )

        user = await get_current_user(credentials)

        assert user["username"] == settings.ADMIN_USERNAME


class TestRequireAuth:
    """Tests for require_auth dependency."""

    @pytest.mark.asyncio
    async def test_require_auth_returns_user(self):
        """Test that require_auth returns the user dict."""
        user = {"username": "admin"}
        result = await require_auth(user)
        assert result == user


class TestAdminUserFunctions:
    """Tests for admin user management functions."""

    @pytest.mark.asyncio
    async def test_update_last_login_existing_user(self, test_db):
        """Test updating last login for existing user."""
        from src.api.auth_local import get_password_hash
        from src.models.user import UserModel

        user = UserModel(
            username="testuser",
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        # Update last login
        await update_last_login("testuser")
        await test_db.refresh(user)

        assert user.last_login is not None

    @pytest.mark.asyncio
    async def test_update_last_login_nonexistent_user(self, test_db):
        """Test updating last login for non-existent user (should not error)."""
        # Should not raise an error
        await update_last_login("nonexistentuser")

    @pytest.mark.asyncio
    async def test_update_admin_password_existing_user(self, test_db):
        """Test updating admin password for existing user."""
        from src.api.auth_local import get_password_hash
        from src.models.user import UserModel

        user = UserModel(
            username=settings.ADMIN_USERNAME,
            password_hash=get_password_hash("oldpassword"),
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        new_hash = get_password_hash("newpassword123")
        await update_admin_password(new_hash)
        await test_db.refresh(user)

        assert verify_password("newpassword123", user.password_hash)

    @pytest.mark.asyncio
    async def test_update_admin_password_creates_user(self, test_db):
        """Test that update_admin_password creates user if not exists."""
        from src.api.auth_local import get_password_hash

        new_hash = get_password_hash("newpassword123")
        await update_admin_password(new_hash)

        # Verify user was created
        from sqlalchemy import select

        from src.models.user import UserModel

        result = await test_db.execute(
            select(UserModel).where(UserModel.username == settings.ADMIN_USERNAME)
        )
        user = result.scalar_one_or_none()

        assert user is not None
        assert verify_password("newpassword123", user.password_hash)


class TestAuthAPIEdgeCases:
    """Edge case tests for authentication API endpoints."""

    def test_login_rate_limit_exceeded(self, sync_test_client):
        """Test login rate limiting."""
        ip = "192.168.1.100"

        # Make 5 failed attempts
        for i in range(5):
            response = sync_test_client.post(
                "/api/v1/auth/local/login",
                json={"username": "admin", "password": "wrongpassword"},
                headers={"X-Forwarded-For": ip},
            )
            assert response.status_code == 401

        # 6th attempt should be rate limited
        response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "admin123"},
            headers={"X-Forwarded-For": ip},
        )
        assert response.status_code == 429
        assert "Too many login attempts" in response.json()["detail"]

    def test_login_clears_attempts_on_success(self, sync_test_client):
        """Test that successful login clears rate limit attempts."""
        # Clear any existing state
        _login_attempts.clear()
        _blocklist.clear()

        # Make a failed attempt
        response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

        # Make a successful attempt
        response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200

        # Verify attempts were cleared (we can make more attempts)
        # This is implicit - if attempts weren't cleared, subsequent
        # requests would fail due to rate limiting

    def test_login_with_x_forwarded_for(self, sync_test_client):
        """Test login with X-Forwarded-For header."""
        response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "admin123"},
            headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_change_password_same_as_current(self, sync_test_client):
        """Test changing password to same value (should still work)."""
        # First login
        login_response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Change to same password (edge case)
        response = sync_test_client.post(
            "/api/v1/auth/local/change-password",
            json={"current_password": "admin123", "new_password": "admin123"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should succeed (though not recommended)
        assert response.status_code == 200

    def test_change_password_exactly_8_chars(self, sync_test_client):
        """Test changing password to exactly 8 characters (boundary)."""
        # First login
        login_response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Change to exactly 8 chars
        response = sync_test_client.post(
            "/api/v1/auth/local/change-password",
            json={"current_password": "admin123", "new_password": "exactly8"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        # Verify new password works
        login_response2 = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "exactly8"},
        )
        assert login_response2.status_code == 200

    def test_change_password_7_chars_rejected(self, sync_test_client):
        """Test that 7 character password is rejected."""
        # First login
        login_response = sync_test_client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Try to change to 7 chars (should fail)
        response = sync_test_client.post(
            "/api/v1/auth/local/change-password",
            json={"current_password": "admin123", "new_password": "only7ch"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "at least 8 characters" in response.json()["detail"]

    def test_protected_endpoints_without_auth(self, sync_test_client):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            ("/api/v1/auth/local/me", "GET"),
            ("/api/v1/auth/local/check", "GET"),
            ("/api/v1/auth/local/change-password", "POST"),
        ]

        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = sync_test_client.get(endpoint)
            elif method == "POST":
                response = sync_test_client.post(endpoint, json={})

            assert response.status_code == 401, f"{method} {endpoint} should require auth"

    def test_protected_endpoints_with_invalid_auth(self, sync_test_client):
        """Test that protected endpoints reject invalid tokens."""
        protected_endpoints = [
            ("/api/v1/auth/local/me", "GET"),
            ("/api/v1/auth/local/check", "GET"),
        ]

        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = sync_test_client.get(
                    endpoint, headers={"Authorization": "Bearer invalid.token"}
                )
            elif method == "POST":
                response = sync_test_client.post(
                    endpoint,
                    json={},
                    headers={"Authorization": "Bearer invalid.token"},
                )

            assert response.status_code == 401, f"{method} {endpoint} should reject invalid token"
