"""Test main application."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_endpoint():
    """Test root endpoint - serves SPA if built, otherwise API info."""
    response = client.get("/")
    assert response.status_code == 200

    # If frontend is built, root serves HTML (SPA)
    # Otherwise, it serves JSON API info
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        # SPA mode - check for HTML content
        assert b"SpecterDefence" in response.content or b"<!doctype html>" in response.content.lower()
    else:
        # API-only mode - check for JSON
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


def test_api_v1_health():
    """Test API v1 health endpoint."""
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
