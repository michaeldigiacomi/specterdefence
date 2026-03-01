"""Geo-IP lookup client for resolving IP addresses to geographic locations."""

import asyncio
import ipaddress
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Geographic location data for an IP address."""
    
    ip_address: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    is_private: bool = False
    lookup_success: bool = False
    error_message: Optional[str] = None


class GeoIPClient:
    """Client for Geo-IP lookups using ip-api.com (free tier: 45 req/min)."""
    
    BASE_URL = "http://ip-api.com/json/{ip}"
    FIELDS = "status,message,country,countryCode,regionName,city,lat,lon,timezone,isp,query"
    
    # Rate limiting: 45 requests per minute max
    MAX_REQUESTS_PER_MINUTE = 45
    REQUEST_INTERVAL = 60.0 / MAX_REQUESTS_PER_MINUTE  # ~1.33 seconds between requests
    
    def __init__(self):
        self._last_request_time: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, GeoLocation] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP address is private/local."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError:
            return False
    
    def _get_cache_key(self, ip: str) -> str:
        """Generate cache key for an IP address."""
        return ip.strip().lower()
    
    def _is_cache_valid(self, ip: str) -> bool:
        """Check if cached result is still valid."""
        cache_key = self._get_cache_key(ip)
        if cache_key not in self._cache_timestamps:
            return False
        
        cached_time = self._cache_timestamps[cache_key]
        return datetime.now() - cached_time < self._cache_ttl
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.REQUEST_INTERVAL:
                wait_time = self.REQUEST_INTERVAL - elapsed
                await asyncio.sleep(wait_time)
        
        self._last_request_time = datetime.now()
    
    async def lookup(self, ip_address: str) -> GeoLocation:
        """
        Look up geographic information for an IP address.
        
        Args:
            ip_address: IP address to look up
            
        Returns:
            GeoLocation object with geographic data
        """
        ip_address = ip_address.strip()
        cache_key = self._get_cache_key(ip_address)
        
        # Check cache first
        if cache_key in self._cache and self._is_cache_valid(ip_address):
            logger.debug(f"Cache hit for IP: {ip_address}")
            return self._cache[cache_key]
        
        # Handle private IPs
        if self._is_private_ip(ip_address):
            geo = GeoLocation(
                ip_address=ip_address,
                is_private=True,
                lookup_success=True,
                country="Private Network",
                city="Local"
            )
            self._cache[cache_key] = geo
            self._cache_timestamps[cache_key] = datetime.now()
            return geo
        
        # Make API request with rate limiting
        await self._rate_limit()
        
        try:
            client = await self._get_client()
            url = self.BASE_URL.format(ip=ip_address)
            params = {"fields": self.FIELDS}
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "success":
                geo = GeoLocation(
                    ip_address=data.get("query", ip_address),
                    country=data.get("country"),
                    country_code=data.get("countryCode"),
                    city=data.get("city"),
                    region=data.get("regionName"),
                    latitude=data.get("lat"),
                    longitude=data.get("lon"),
                    timezone=data.get("timezone"),
                    isp=data.get("isp"),
                    is_private=False,
                    lookup_success=True
                )
            else:
                error_msg = data.get("message", "Unknown error")
                logger.warning(f"Geo-IP lookup failed for {ip_address}: {error_msg}")
                geo = GeoLocation(
                    ip_address=ip_address,
                    lookup_success=False,
                    error_message=error_msg
                )
            
            # Cache the result
            self._cache[cache_key] = geo
            self._cache_timestamps[cache_key] = datetime.now()
            
            return geo
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error looking up IP {ip_address}: {e}")
            return GeoLocation(
                ip_address=ip_address,
                lookup_success=False,
                error_message=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error looking up IP {ip_address}: {e}")
            return GeoLocation(
                ip_address=ip_address,
                lookup_success=False,
                error_message=f"Error: {str(e)}"
            )
    
    async def lookup_batch(self, ip_addresses: list[str]) -> Dict[str, GeoLocation]:
        """
        Look up multiple IP addresses (with rate limiting).
        
        Args:
            ip_addresses: List of IP addresses to look up
            
        Returns:
            Dictionary mapping IP addresses to GeoLocation objects
        """
        results = {}
        
        for ip in ip_addresses:
            results[ip] = await self.lookup(ip)
        
        return results
    
    def clear_cache(self):
        """Clear the location cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global client instance
_geo_ip_client: Optional[GeoIPClient] = None


def get_geo_ip_client() -> GeoIPClient:
    """Get the global Geo-IP client instance."""
    global _geo_ip_client
    if _geo_ip_client is None:
        _geo_ip_client = GeoIPClient()
    return _geo_ip_client


async def lookup_ip(ip_address: str) -> GeoLocation:
    """
    Convenience function to look up an IP address.
    
    Args:
        ip_address: IP address to look up
        
    Returns:
        GeoLocation object
    """
    client = get_geo_ip_client()
    return await client.lookup(ip_address)
