"""Office 365 Management Activity API client."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import httpx
import msal

from src.config import settings

logger = logging.getLogger(__name__)

# Office 365 Management API endpoints
MANAGEMENT_API_BASE = "https://manage.office.com/api/v1.0"
CONTENT_TYPES = [
    "Audit.AzureActiveDirectory",
    "Audit.Exchange",
    "Audit.SharePoint",
    "Audit.General",
    "DLP.All",
]


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


class O365ManagementAuthError(Exception):
    """Raised when authentication fails."""

    pass


class O365ManagementAPIError(Exception):
    """Raised when API call fails."""

    pass


class O365ManagementClient:
    """Client for Office 365 Management Activity API."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        """Initialize O365 Management API client.

        Args:
            tenant_id: Azure AD tenant ID (GUID)
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            max_retries: Maximum number of retry attempts for rate limited requests
            base_delay: Base delay in seconds for exponential backoff
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.max_retries = max_retries
        self.base_delay = base_delay

        # MSAL confidential client for token acquisition
        authority = f"{settings.MS_LOGIN_URL}/{tenant_id}"
        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _get_access_token(self) -> str:
        """Get access token for Management API.

        Returns:
            Access token string.

        Raises:
            O365ManagementAuthError: If authentication fails.
        """
        # Check if we have a valid cached token
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now(UTC) < self._token_expires_at - timedelta(minutes=5)
        ):
            return self._access_token

        # Try to get token silently from cache
        result = self.app.acquire_token_silent(["https://manage.office.com/.default"], account=None)

        if not result:
            # Fetch new token
            result = self.app.acquire_token_for_client(
                scopes=["https://manage.office.com/.default"]
            )

        if "access_token" not in result:
            error = result.get("error_description", "Unknown error")
            raise O365ManagementAuthError(f"Failed to get access token: {error}")

        self._access_token = result["access_token"]
        # Set expiry with buffer
        expires_in = result.get("expires_in", 3600)
        self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 300)

        return self._access_token

    async def _make_request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None, retry_count: int = 0
    ) -> dict[str, Any]:
        """Make authenticated request to Management API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Optional query parameters
            retry_count: Current retry attempt number

        Returns:
            JSON response as dictionary.

        Raises:
            RateLimitError: If rate limit is exceeded after all retries.
            O365ManagementAPIError: If API call fails.
        """
        token = await self._get_access_token()
        url = urljoin(f"{MANAGEMENT_API_BASE}/{self.tenant_id}/", endpoint)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method, url=url, headers=headers, params=params, timeout=60.0
                )

                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    if retry_count >= self.max_retries:
                        raise RateLimitError(
                            f"Rate limit exceeded after {self.max_retries} retries"
                        )

                    # Get retry-after header or use exponential backoff
                    retry_after = response.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after else self.base_delay * 2**retry_count

                    logger.warning(
                        f"Rate limited. Waiting {delay}s before retry {retry_count + 1}/{self.max_retries}"
                    )
                    await asyncio.sleep(delay)
                    return await self._make_request(method, endpoint, params, retry_count + 1)

                # Handle other errors
                if response.status_code == 401:
                    # Token might be expired, clear and retry once
                    if retry_count == 0:
                        self._access_token = None
                        return await self._make_request(method, endpoint, params, retry_count + 1)
                    raise O365ManagementAuthError(f"Authentication failed: {response.text}")

                if response.status_code == 403:
                    raise O365ManagementAuthError(
                        f"Access denied. Check permissions: {response.text}"
                    )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                raise O365ManagementAPIError(
                    f"HTTP error {e.response.status_code}: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                if retry_count < self.max_retries:
                    delay = self.base_delay * (2**retry_count)
                    logger.warning(f"Request error: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    return await self._make_request(method, endpoint, params, retry_count + 1)
                raise O365ManagementAPIError(
                    f"Request failed after {self.max_retries} retries: {e}"
                ) from e

    async def start_subscription(self, content_type: str) -> dict[str, Any]:
        """Start a subscription for a content type.

        Args:
            content_type: Office 365 content type (e.g., Audit.AzureActiveDirectory)

        Returns:
            Subscription response.
        """
        endpoint = "activity/feed/subscriptions/start"
        params = {"contentType": content_type}

        return await self._make_request("POST", endpoint, params)

    async def list_subscriptions(self) -> list[dict[str, Any]]:
        """List active subscriptions.

        Returns:
            List of subscription objects.
        """
        endpoint = "activity/feed/subscriptions/list"
        result = await self._make_request("GET", endpoint)
        return result if isinstance(result, list) else []

    async def stop_subscription(self, content_type: str) -> dict[str, Any]:
        """Stop a subscription for a content type.

        Args:
            content_type: Office 365 content type.

        Returns:
            Stop response.
        """
        endpoint = "activity/feed/subscriptions/stop"
        params = {"contentType": content_type}

        return await self._make_request("POST", endpoint, params)

    async def get_content_blobs(
        self,
        content_type: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        next_page_uri: str | None = None,
    ) -> dict[str, Any]:
        """Get content blob URLs for a content type.

        Args:
            content_type: Office 365 content type.
            start_time: Start time for content (defaults to 24 hours ago).
            end_time: End time for content (defaults to now).
            next_page_uri: URI for next page (pagination).

        Returns:
            Dictionary with content blobs and next page URI.
        """
        if next_page_uri:
            # Use the next page URI directly
            token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    next_page_uri, headers={"Authorization": f"Bearer {token}"}, timeout=60.0
                )
                response.raise_for_status()
                return response.json()

        # Build request with time range
        endpoint = "activity/feed/subscriptions/content"
        params: dict[str, str] = {"contentType": content_type}

        if start_time:
            params["startTime"] = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        if end_time:
            params["endTime"] = end_time.strftime("%Y-%m-%dT%H:%M:%S")

        return await self._make_request("GET", endpoint, params)

    async def download_content(self, content_uri: str) -> list[dict[str, Any]]:
        """Download content from a blob URL.

        Args:
            content_uri: URL to the content blob.

        Returns:
            List of audit log events.
        """
        # Content URIs are pre-authenticated, no need for bearer token
        async with httpx.AsyncClient() as client:
            response = await client.get(content_uri, timeout=60.0)
            response.raise_for_status()

            # Content is often newline-delimited JSON
            content = response.text.strip()
            if not content:
                return []

            events = []
            for line in content.split("\n"):
                line = line.strip()
                if line:
                    import json

                    events.append(json.loads(line))

            return events

    async def collect_logs(
        self,
        content_type: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Collect all logs for a content type with pagination.

        Args:
            content_type: Office 365 content type.
            start_time: Start time for collection.
            end_time: End time for collection.

        Yields:
            Batches of audit log events.
        """
        next_page_uri: str | None = None
        total_blobs = 0
        total_events = 0

        while True:
            try:
                # The content endpoint returns a LIST of content blob objects,
                # not a dict. Each item has a 'contentUri' field.
                if next_page_uri:
                    token = await self._get_access_token()
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            next_page_uri,
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=60.0,
                        )
                        response.raise_for_status()
                        result = response.json()
                        # Pagination via NextPageUri header
                        next_page_uri = response.headers.get("NextPageUri")
                else:
                    # First request
                    token = await self._get_access_token()
                    endpoint = "activity/feed/subscriptions/content"
                    params: dict[str, str] = {"contentType": content_type}
                    if start_time:
                        params["startTime"] = start_time.strftime("%Y-%m-%dT%H:%M:%S")
                    if end_time:
                        params["endTime"] = end_time.strftime("%Y-%m-%dT%H:%M:%S")

                    url = f"{MANAGEMENT_API_BASE}/{self.tenant_id}/{endpoint}"
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            url,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json",
                            },
                            params=params,
                            timeout=60.0,
                        )
                        response.raise_for_status()
                        result = response.json()
                        # Pagination via NextPageUri header
                        next_page_uri = response.headers.get("NextPageUri")

                # result is a list of content blob objects
                blob_items = result if isinstance(result, list) else []

                if not blob_items:
                    logger.info(f"No more content blobs for {content_type}")
                    break

                # Extract content URIs from blob objects
                blob_uris = []
                for item in blob_items:
                    if isinstance(item, dict) and "contentUri" in item:
                        blob_uris.append(item["contentUri"])

                total_blobs += len(blob_uris)
                logger.info(
                    f"Processing {len(blob_uris)} blobs for {content_type} (total: {total_blobs})"
                )

                # Download content from each blob
                for blob_url in blob_uris:
                    try:
                        events = await self.download_content(blob_url)
                        if events:
                            total_events += len(events)
                            yield events

                            # Small delay to be nice to the API
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Failed to download content from {blob_url}: {e}")
                        continue

                # If no next page, we're done
                if not next_page_uri:
                    logger.info(
                        f"Completed collection for {content_type}: "
                        f"{total_blobs} blobs, {total_events} events"
                    )
                    break

            except RateLimitError:
                logger.error(f"Rate limit exceeded for {content_type}")
                raise
            except Exception as e:
                logger.error(f"Error collecting logs for {content_type}: {e}")
                raise

    async def ensure_subscriptions(self) -> list[str]:
        """Ensure all required content type subscriptions are active.

        Returns:
            List of successfully subscribed content types.
        """
        subscribed = []

        for content_type in CONTENT_TYPES:
            try:
                result = await self.start_subscription(content_type)
                logger.info(f"Started/verified subscription for {content_type}: {result}")
                subscribed.append(content_type)
            except O365ManagementAPIError as e:
                if "already enabled" in str(e).lower():
                    logger.info(f"Subscription already active for {content_type}")
                    subscribed.append(content_type)
                else:
                    logger.error(f"Failed to subscribe to {content_type}: {e}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {content_type}: {e}")

        return subscribed


def map_content_type_to_log_type(content_type: str) -> str:
    """Map O365 content type to our log type enum value.

    Args:
        content_type: Office 365 content type.

    Returns:
        Our internal log type string.
    """
    mapping = {
        "Audit.AzureActiveDirectory": "signin",
        "Audit.Exchange": "audit_general",
        "Audit.SharePoint": "audit_general",
        "Audit.General": "audit_general",
        "DLP.All": "audit_general",
    }
    return mapping.get(content_type, "audit_general")
