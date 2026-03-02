"""Tests for local authentication module."""

import pytest
from datetime import timedelta
from jose import jwt
from fastapi import HTTPException

from src.api.auth_local import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    LoginRequest,
)
from src.config import settings


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_get_password_hash(self):
        """Test that password hashing produces a valid hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert hashed.startswith("$2")  # bcrypt hashes start with $2

    def test_verify_password_correct(self):
        """Test verifying a correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying an incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWTToken:
    """Test JWT token functions."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": "admin"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiration(self):
        """Test creating an access token with custom expiration."""
        data = {"sub": "admin"}
        expires = timedelta(hours=1)
        token = create_access_token(data, expires)
        
        # Verify the token can be decoded
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == "admin"
        assert "exp" in decoded

    def test_verify_token_valid(self):
        """Test verifying a valid token."""
        data = {"sub": "admin"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "admin"

    def test_verify_token_invalid(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        
        assert payload is None

    def test_verify_token_expired(self):
        """Test verifying an expired token."""
        # Create a token that expired 1 hour ago
        data = {"sub": "admin"}
        expired_token = create_access_token(data, expires_delta=timedelta(hours=-1))
        
        payload = verify_token(expired_token)
        
        assert payload is None


class TestLoginEndpoint:
    """Test login endpoint."""

    def test_login_success(self, sync_test_client):
        """Test successful login with valid credentials."""
        # The default password hash is for "admin123"
        response = sync_test_client.post("/api/v1/auth/local/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_username(self, sync_test_client):
        """Test login with invalid username."""
        response = sync_test_client.post("/api/v1/auth/local/login", json={
            "username": "wronguser",
            "password": "admin123"
        })
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_invalid_password(self, sync_test_client):
        """Test login with invalid password."""
        response = sync_test_client.post("/api/v1/auth/local/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]


class TestAuthCheckEndpoint:
    """Test auth check endpoint."""

    def test_auth_check_with_valid_token(self, sync_test_client):
        """Test auth check with a valid token."""
        # First login to get a token
        login_response = sync_test_client.post("/api/v1/auth/local/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = login_response.json()["access_token"]
        
        # Then check auth
        response = sync_test_client.get("/api/v1/auth/local/check", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["username"] == "admin"

    def test_auth_check_without_token(self, sync_test_client):
        """Test auth check without a token."""
        response = sync_test_client.get("/api/v1/auth/local/check")
        
        assert response.status_code == 401

    def test_auth_check_with_invalid_token(self, sync_test_client):
        """Test auth check with an invalid token."""
        response = sync_test_client.get("/api/v1/auth/local/check", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        
        assert response.status_code == 401


class TestMeEndpoint:
    """Test current user endpoint."""

    def test_get_current_user_with_valid_token(self, sync_test_client):
        """Test getting current user with a valid token."""
        # First login to get a token
        login_response = sync_test_client.post("/api/v1/auth/local/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = login_response.json()["access_token"]
        
        # Then get current user
        response = sync_test_client.get("/api/v1/auth/local/me", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["is_authenticated"] is True

    def test_get_current_user_without_token(self, sync_test_client):
        """Test getting current user without a token."""
        response = sync_test_client.get("/api/v1/auth/local/me")
        
        assert response.status_code == 401


class TestLogoutEndpoint:
    """Test logout endpoint."""

    def test_logout(self, sync_test_client):
        """Test logout endpoint."""
        response = sync_test_client.post("/api/v1/auth/local/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert "Logged out successfully" in data["message"]
