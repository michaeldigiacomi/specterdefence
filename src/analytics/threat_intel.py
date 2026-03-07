"""Threat Intelligence service for checking IP reputation."""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ThreatIntelClient(ABC):
    """Abstract interface for checking IP reputation against CTI sources."""

    @abstractmethod
    async def lookup_ip(self, ip_address: str) -> dict[str, Any]:
        """
        Check if an IP address is known to be malicious.

        Args:
            ip_address: IPv4 or IPv6 address to check

        Returns:
            Dictionary containing threat intelligence data
        """
        pass


class DefaultThreatIntelClient(ThreatIntelClient):
    """
    Default CTI client.
    For this initial version we are mocking a static subset of known bad IPs.
    Later this can be swapped out to hit AlienVault OTX, AbuseIPDB, etc.
    """

    # Mock database of malicious IPs for demonstration and testing purposes
    KNOWN_MALICIOUS_IPS = {
        "8.8.8.8": {  # Included purely for testing an alert easily
            "threat_score": 95,
            "tags": ["botnet", "scanner"],
            "source": "Mock CTI Database",
        },
        "185.156.73.14": {
            "threat_score": 90,
            "tags": ["brute_force", "tor_exit_node"],
            "source": "Mock CTI Database",
        },
        "45.134.144.156": {
            "threat_score": 85,
            "tags": ["malware", "phishing"],
            "source": "Mock CTI Database",
        },
    }

    async def lookup_ip(self, ip_address: str) -> dict[str, Any]:
        """Check IP against mock database."""
        if ip_address in self.KNOWN_MALICIOUS_IPS:
            data = self.KNOWN_MALICIOUS_IPS[ip_address]
            logger.info(f"Malicious IP detected by CTI: {ip_address} (Score: {data['threat_score']})")
            return {
                "is_malicious": True,
                "threat_score": data["threat_score"],
                "tags": data["tags"],
                "source": data["source"],
            }

        return {
            "is_malicious": False,
            "threat_score": 0,
            "tags": [],
            "source": "Local Mock CTI",
        }


# Singleton pattern matching geo_ip.py
_client_instance: ThreatIntelClient | None = None


def get_threat_intel_client() -> ThreatIntelClient:
    """Get the configured threat intel client."""
    global _client_instance
    if _client_instance is None:
        # In a real app, this would read from settings to decide which subclass to instantiate
        _client_instance = DefaultThreatIntelClient()
    return _client_instance
