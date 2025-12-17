"""EZUnsub API client."""

from __future__ import annotations

from typing import Any
import httpx

from .exceptions import (
    EZUnsubError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ForbiddenError,
)


class EZUnsubClient:
    """Client for interacting with the EZUnsub API.

    Example:
        ```python
        from ezunsub import EZUnsubClient

        client = EZUnsubClient(
            api_key="your-api-key",
            base_url="https://your-ezunsub-instance.com"
        )

        # List contacts
        contacts = client.contacts.list()

        # Check suppression
        is_suppressed = client.contacts.check("user@example.com")

        # Create webhook
        webhook = client.webhooks.create(
            name="My Webhook",
            url="https://my-app.com/webhooks/ezunsub",
            events=["contact.created", "contact.updated"]
        )
        ```
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.ezunsub.com",
        timeout: float = 30.0,
    ):
        """Initialize the EZUnsub client.

        Args:
            api_key: Your EZUnsub API key.
            base_url: Base URL for the EZUnsub API.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "ezunsub-python/0.1.0",
            },
            timeout=timeout,
        )

        # Resource endpoints
        self.contacts = ContactsResource(self)
        self.webhooks = WebhooksResource(self)
        self.links = LinksResource(self)
        self.offers = OffersResource(self)
        self.exports = ExportsResource(self)

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an API request."""
        response = self._client.request(
            method=method,
            url=path,
            json=json,
            params=params,
        )
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any] | list[Any]:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError()
        if response.status_code == 403:
            data = response.json() if response.content else {}
            raise ForbiddenError(data.get("error", "Access denied"))
        if response.status_code == 404:
            data = response.json() if response.content else {}
            raise NotFoundError(data.get("error", "Resource not found"))
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                retry_after=int(retry_after) if retry_after else None
            )
        if response.status_code == 400:
            data = response.json() if response.content else {}
            raise ValidationError(data.get("error", "Invalid request"))
        if response.status_code >= 400:
            data = response.json() if response.content else {}
            raise EZUnsubError(
                data.get("error", f"Request failed with status {response.status_code}"),
                status_code=response.status_code,
            )

        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> EZUnsubClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class ContactsResource:
    """Contacts API resource."""

    def __init__(self, client: EZUnsubClient):
        self._client = client

    def list(
        self,
        page: int = 1,
        limit: int = 50,
        link_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """List contacts.

        Args:
            page: Page number (default: 1).
            limit: Items per page (default: 50, max: 200).
            link_code: Filter by link code.

        Returns:
            List of contacts.
        """
        params: dict[str, Any] = {"page": page, "limit": limit}
        if link_code:
            params["linkCode"] = link_code
        return self._client._request("GET", "/api/contacts", params=params)

    def get(self, contact_id: str) -> dict[str, Any]:
        """Get a contact by ID.

        Args:
            contact_id: Contact ID.

        Returns:
            Contact details.
        """
        return self._client._request("GET", f"/api/contacts/{contact_id}")

    def delete(self, contact_id: str) -> dict[str, Any]:
        """Delete a contact (admin only).

        Args:
            contact_id: Contact ID.

        Returns:
            Success response.
        """
        return self._client._request("DELETE", f"/api/contacts/{contact_id}")

    def stats(self) -> dict[str, Any]:
        """Get contact statistics.

        Returns:
            Contact stats (total, emails, phones, global).
        """
        return self._client._request("GET", "/api/contacts/stats")


class WebhooksResource:
    """Webhooks API resource."""

    def __init__(self, client: EZUnsubClient):
        self._client = client

    def list(self, org_id: str | None = None) -> list[dict[str, Any]]:
        """List webhooks.

        Args:
            org_id: Filter by organization ID (admin only).

        Returns:
            List of webhooks.
        """
        params = {"orgId": org_id} if org_id else None
        return self._client._request("GET", "/api/webhooks", params=params)

    def get(self, webhook_id: str) -> dict[str, Any]:
        """Get a webhook by ID.

        Args:
            webhook_id: Webhook ID.

        Returns:
            Webhook details.
        """
        return self._client._request("GET", f"/api/webhooks/{webhook_id}")

    def create(
        self,
        name: str,
        url: str,
        events: list[str],
        pii_mode: str = "hashes",
        org_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a webhook.

        Args:
            name: Webhook name.
            url: Webhook URL (must be HTTPS).
            events: List of events to subscribe to.
            pii_mode: PII mode (full, hashes, none). Default: hashes.
            org_id: Organization ID (admin only).

        Returns:
            Created webhook with secret (only shown once).

        Events:
            - contact.created
            - contact.updated
            - complaint.created
            - complaint.updated
            - link.created
            - link.clicked
            - export.completed
        """
        data: dict[str, Any] = {
            "name": name,
            "url": url,
            "events": events,
            "piiMode": pii_mode,
        }
        if org_id:
            data["orgId"] = org_id
        return self._client._request("POST", "/api/webhooks", json=data)

    def update(
        self,
        webhook_id: str,
        name: str | None = None,
        url: str | None = None,
        events: list[str] | None = None,
        pii_mode: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Update a webhook.

        Args:
            webhook_id: Webhook ID.
            name: New webhook name.
            url: New webhook URL.
            events: New list of events.
            pii_mode: New PII mode.
            is_active: Enable/disable webhook.

        Returns:
            Updated webhook.
        """
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if url is not None:
            data["url"] = url
        if events is not None:
            data["events"] = events
        if pii_mode is not None:
            data["piiMode"] = pii_mode
        if is_active is not None:
            data["isActive"] = is_active
        return self._client._request("PATCH", f"/api/webhooks/{webhook_id}", json=data)

    def delete(self, webhook_id: str) -> dict[str, Any]:
        """Delete a webhook.

        Args:
            webhook_id: Webhook ID.

        Returns:
            Success response.
        """
        return self._client._request("DELETE", f"/api/webhooks/{webhook_id}")

    def rotate_secret(self, webhook_id: str) -> dict[str, Any]:
        """Rotate webhook secret.

        Args:
            webhook_id: Webhook ID.

        Returns:
            Webhook with new secret (only shown once).
        """
        return self._client._request("POST", f"/api/webhooks/{webhook_id}/rotate-secret")

    def test(self, webhook_id: str) -> dict[str, Any]:
        """Send a test webhook.

        Args:
            webhook_id: Webhook ID.

        Returns:
            Test result with success status and response.
        """
        return self._client._request("POST", f"/api/webhooks/{webhook_id}/test")

    def deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get webhook delivery history.

        Args:
            webhook_id: Webhook ID.
            limit: Max results (default: 50, max: 100).
            offset: Offset for pagination.

        Returns:
            Delivery history with pagination.
        """
        params = {"limit": limit, "offset": offset}
        return self._client._request(
            "GET", f"/api/webhooks/{webhook_id}/deliveries", params=params
        )

    def events(self) -> dict[str, Any]:
        """Get available webhook events.

        Returns:
            Dict with events and piiModes lists.
        """
        return self._client._request("GET", "/api/webhooks/events/list")


class LinksResource:
    """Links API resource."""

    def __init__(self, client: EZUnsubClient):
        self._client = client

    def list(
        self,
        page: int = 1,
        limit: int = 50,
        offer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List unsubscribe links.

        Args:
            page: Page number.
            limit: Items per page.
            offer_id: Filter by offer ID.

        Returns:
            List of links.
        """
        params: dict[str, Any] = {"page": page, "limit": limit}
        if offer_id:
            params["offerId"] = offer_id
        return self._client._request("GET", "/api/links", params=params)

    def get(self, code: str) -> dict[str, Any]:
        """Get a link by code.

        Args:
            code: Link code.

        Returns:
            Link details.
        """
        return self._client._request("GET", f"/api/links/{code}")

    def create(
        self,
        offer_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create an unsubscribe link.

        Args:
            offer_id: Offer ID.
            name: Optional link name.

        Returns:
            Created link.
        """
        data: dict[str, Any] = {"offerId": offer_id}
        if name:
            data["name"] = name
        return self._client._request("POST", "/api/links", json=data)


class OffersResource:
    """Offers API resource."""

    def __init__(self, client: EZUnsubClient):
        self._client = client

    def list(self, page: int = 1, limit: int = 50) -> list[dict[str, Any]]:
        """List offers.

        Args:
            page: Page number.
            limit: Items per page.

        Returns:
            List of offers.
        """
        params = {"page": page, "limit": limit}
        return self._client._request("GET", "/api/offers", params=params)

    def get(self, offer_id: str) -> dict[str, Any]:
        """Get an offer by ID.

        Args:
            offer_id: Offer ID.

        Returns:
            Offer details.
        """
        return self._client._request("GET", f"/api/offers/{offer_id}")


class ExportsResource:
    """Exports API resource."""

    def __init__(self, client: EZUnsubClient):
        self._client = client

    def list(self, page: int = 1, limit: int = 50) -> list[dict[str, Any]]:
        """List exports.

        Args:
            page: Page number.
            limit: Items per page.

        Returns:
            List of exports.
        """
        params = {"page": page, "limit": limit}
        return self._client._request("GET", "/api/exports", params=params)

    def get(self, export_id: str) -> dict[str, Any]:
        """Get an export by ID.

        Args:
            export_id: Export ID.

        Returns:
            Export details.
        """
        return self._client._request("GET", f"/api/exports/{export_id}")

    def create(
        self,
        name: str,
        filters: dict[str, Any] | None = None,
        format: str = "csv",
    ) -> dict[str, Any]:
        """Create an export job.

        Args:
            name: Export name.
            filters: Optional filters.
            format: Export format (csv).

        Returns:
            Created export job.
        """
        data: dict[str, Any] = {"name": name, "format": format}
        if filters:
            data["filters"] = filters
        return self._client._request("POST", "/api/exports", json=data)
