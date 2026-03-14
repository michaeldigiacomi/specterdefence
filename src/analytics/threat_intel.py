"""Threat Intelligence service for checking IP reputation."""

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.config import settings

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


class AbuseIPDBClient(ThreatIntelClient):
    """
    Client for AbuseIPDB API.
    Free tier: 1,000 API requests per day.
    API docs: https://www.abuseipdb.com/api
    """

    BASE_URL = "https://api.abuseipdb.com/api/v2/check"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def lookup_ip(self, ip_address: str) -> dict[str, Any]:
        """Check IP against AbuseIPDB."""
        if not self.api_key:
            return {
                "is_malicious": False,
                "threat_score": 0,
                "tags": [],
                "source": "AbuseIPDB",
                "error": "No API key configured",
            }

        try:
            client = await self._get_client()
            headers = {
                "Key": self.api_key,
                "Accept": "application/json",
            }
            params = {
                "ipAddress": ip_address,
                "maxAgeInDays": 90,
                "verbose": "",
            }

            response = await client.get(self.BASE_URL, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                abuse_report = data.get("data", {})

                abuse_score = abuse_report.get("abuseConfidenceScore", 0)
                is_malicious = abuse_score > 0

                # Get categories
                category_ids = abuse_report.get("categories", [])
                tags = self._map_categories(category_ids)

                logger.info(f"AbuseIPDB lookup for {ip_address}: score={abuse_score}, malicious={is_malicious}")

                return {
                    "is_malicious": is_malicious,
                    "threat_score": abuse_score,
                    "tags": tags,
                    "source": "AbuseIPDB",
                    "reported_count": abuse_report.get("numDistinctReports", 0),
                    "is_whitelisted": abuse_report.get("isWhitelisted", False),
                    "last_reported": abuse_report.get("lastReportedAt"),
                }
            else:
                logger.warning(f"AbuseIPDB API error: {response.status_code}")
                return {
                    "is_malicious": False,
                    "threat_score": 0,
                    "tags": [],
                    "source": "AbuseIPDB",
                    "error": f"API error: {response.status_code}",
                }

        except Exception as e:
            logger.error(f"Error looking up {ip_address} in AbuseIPDB: {e}")
            return {
                "is_malicious": False,
                "threat_score": 0,
                "tags": [],
                "source": "AbuseIPDB",
                "error": str(e),
            }

    def _map_categories(self, category_ids: list[int]) -> list[str]:
        """Map AbuseIPDB category IDs to human-readable tags."""
        # https://www.abuseipdb.com/categories
        category_map = {
            1: "dns_attack",
            2: "dns_compromise",
            3: "dns_poisoning",
            4: "dos_attack",
            5: "fp_dos",
            6: "web_attack",
            7: "brute_force",
            8: "spam",
            9: "port_scan",
            10: "hacking",
            11: "sql_injection",
            12: "xss_attack",
            13: "open_proxy",
            14: "web_spider",
            15: "web_probe",
            16: "fraud_click",
            17: "ad_fraud",
            18: "bot",
            19: "unknown",
            20: "tor_exit_node",
        }
        return [category_map.get(cat, f"category_{cat}") for cat in category_ids]

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class AlienVaultOTXClient(ThreatIntelClient):
    """
    Client for AlienVault OTX API.
    Free tier available.
    API docs: https://otx.alienvault.com/api
    """

    BASE_URL = "https://otx.alienvault.com/api/v3/indicators/IPv4"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def lookup_ip(self, ip_address: str) -> dict[str, Any]:
        """Check IP against AlienVault OTX."""
        if not self.api_key:
            return {
                "is_malicious": False,
                "threat_score": 0,
                "tags": [],
                "source": "AlienVault OTX",
                "error": "No API key configured",
            }

        try:
            client = await self._get_client()
            headers = {
                "X-OTX-API-KEY": self.api_key,
            }
            url = f"{self.BASE_URL}/{ip_address}/general"

            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()

                # Get pulse info (threat intelligence)
                pulses = data.get("pulse_info", {}).get("pulses", [])
                pulse_count = len(pulses)

                # Get malicious ratio
                malicious_count = data.get("count", {})

                # Determine threat score based on pulse count
                if pulse_count > 10:
                    threat_score = 95
                elif pulse_count > 5:
                    threat_score = 80
                elif pulse_count > 0:
                    threat_score = 60
                else:
                    threat_score = 0

                # Get tags from pulses
                tags = []
                for pulse in pulses[:5]:  # Limit to first 5 pulses
                    tags.extend(pulse.get("tags", []))

                is_malicious = pulse_count > 0

                logger.info(f"AlienVault OTX lookup for {ip_address}: pulses={pulse_count}, malicious={is_malicious}")

                return {
                    "is_malicious": is_malicious,
                    "threat_score": threat_score,
                    "tags": list(set(tags))[:10],  # Unique tags, max 10
                    "source": "AlienVault OTX",
                    "pulse_count": pulse_count,
                    "country": data.get("country_code"),
                    "asn": data.get("asn"),
                }
            else:
                logger.warning(f"AlienVault OTX API error: {response.status_code}")
                return {
                    "is_malicious": False,
                    "threat_score": 0,
                    "tags": [],
                    "source": "AlienVault OTX",
                    "error": f"API error: {response.status_code}",
                }

        except Exception as e:
            logger.error(f"Error looking up {ip_address} in AlienVault OTX: {e}")
            return {
                "is_malicious": False,
                "threat_score": 0,
                "tags": [],
                "source": "AlienVault OTX",
                "error": str(e),
            }

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class CombinedThreatIntelClient(ThreatIntelClient):
    """
    Combined threat intelligence client that queries multiple sources.
    Aggregates results from AbuseIPDB and AlienVault OTX.
    """

    def __init__(self, abuseipdb_client: AbuseIPDBClient | None = None, otx_client: AlienVaultOTXClient | None = None):
        self.abuseipdb = abuseipdb_client
        self.otx = otx_client

    async def lookup_ip(self, ip_address: str) -> dict[str, Any]:
        """Check IP against multiple threat intelligence sources."""
        results = []

        # Query AbuseIPDB
        if self.abuseipdb:
            abuse_result = await self.abuseipdb.lookup_ip(ip_address)
            results.append(abuse_result)

        # Query AlienVault OTX
        if self.otx:
            otx_result = await self.otx.lookup_ip(ip_address)
            results.append(otx_result)

        # Aggregate results
        return self._aggregate_results(results)

    def _aggregate_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate results from multiple sources."""
        if not results:
            return {
                "is_malicious": False,
                "threat_score": 0,
                "tags": [],
                "sources": [],
            }

        # Check if any source reports malicious
        is_malicious = any(r.get("is_malicious", False) for r in results)

        # Get max threat score
        threat_scores = [r.get("threat_score", 0) for r in results]
        max_threat_score = max(threat_scores) if threat_scores else 0

        # Collect all tags
        all_tags = []
        sources = []
        for r in results:
            source = r.get("source", "Unknown")
            if source and source != "Unknown":
                sources.append(source)
            all_tags.extend(r.get("tags", []))

        # Remove duplicates while preserving order
        unique_tags = list(dict.fromkeys(all_tags))

        return {
            "is_malicious": is_malicious,
            "threat_score": max_threat_score,
            "tags": unique_tags[:15],  # Limit to 15 tags
            "sources": sources,
            "details": results,
        }

    async def close(self):
        if self.abuseipdb:
            await self.abuseipdb.close()
        if self.otx:
            await self.otx.close()


# Singleton pattern
_client_instance: CombinedThreatIntelClient | None = None


def get_threat_intel_client() -> CombinedThreatIntelClient:
    """Get the configured threat intel client."""
    global _client_instance
    if _client_instance is None:
        # Create clients if API keys are configured
        abuseipdb = None
        otx = None

        if settings.ABUSEIPDB_API_KEY:
            abuseipdb = AbuseIPDBClient(settings.ABUSEIPDB_API_KEY)
            logger.info("AbuseIPDB threat intel client initialized")

        if settings.ALIENVAULT_OTX_API_KEY:
            otx = AlienVaultOTXClient(settings.ALIENVAULT_OTX_API_KEY)
            logger.info("AlienVault OTX threat intel client initialized")

        # Create combined client (works with empty clients too)
        _client_instance = CombinedThreatIntelClient(abuseipdb, otx)

    return _client_instance