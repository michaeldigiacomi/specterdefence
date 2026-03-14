from unittest.mock import MagicMock
from fastapi import Request
from src.api.auth_local import get_client_ip
from src.config import settings

def test_get_client_ip_no_x_forwarded_for():
    # Setup mock request
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client.host = "1.2.3.4"

    assert get_client_ip(request) == "1.2.3.4"

def test_get_client_ip_with_x_forwarded_for_no_trusted_proxies():
    # Setup mock request
    request = MagicMock(spec=Request)
    request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
    request.client.host = "1.2.3.4"

    # Ensure no trusted proxies
    original_proxies = settings.TRUSTED_PROXIES
    settings.TRUSTED_PROXIES = []

    try:
        # Since 1.2.3.4 is not trusted, it should return 1.2.3.4
        assert get_client_ip(request) == "1.2.3.4"
    finally:
        settings.TRUSTED_PROXIES = original_proxies

def test_get_client_ip_with_x_forwarded_for_and_trusted_proxies():
    # Setup mock request
    # Client (10.0.0.1) -> Proxy 1 (10.0.0.2) -> Proxy 2 (1.2.3.4) -> App
    request = MagicMock(spec=Request)
    request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
    request.client.host = "1.2.3.4"

    # Trust Proxy 2 (1.2.3.4) and Proxy 1 (10.0.0.2)
    original_proxies = settings.TRUSTED_PROXIES
    settings.TRUSTED_PROXIES = ["1.2.3.4", "10.0.0.2"]

    try:
        # 1.2.3.4 is trusted -> look at 10.0.0.2
        # 10.0.0.2 is trusted -> look at 10.0.0.1
        # 10.0.0.1 is NOT trusted -> return 10.0.0.1
        assert get_client_ip(request) == "10.0.0.1"
    finally:
        settings.TRUSTED_PROXIES = original_proxies

def test_get_client_ip_spoofed_x_forwarded_for():
    # Setup mock request
    # Attacker (8.8.8.8) sends X-Forwarded-For: 1.1.1.1
    # Attacker connects via Proxy (1.2.3.4)
    request = MagicMock(spec=Request)
    request.headers = {"x-forwarded-for": "1.1.1.1, 8.8.8.8"}
    request.client.host = "1.2.3.4"

    # Only trust our Proxy (1.2.3.4)
    original_proxies = settings.TRUSTED_PROXIES
    settings.TRUSTED_PROXIES = ["1.2.3.4"]

    try:
        # 1.2.3.4 is trusted -> look at 8.8.8.8
        # 8.8.8.8 is NOT trusted -> return 8.8.8.8
        # Attacker cannot spoof being 1.1.1.1 because 8.8.8.8 is not a trusted proxy
        assert get_client_ip(request) == "8.8.8.8"
    finally:
        settings.TRUSTED_PROXIES = original_proxies
