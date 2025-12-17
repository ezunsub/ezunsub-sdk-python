"""Webhook verification and parsing utilities."""

from __future__ import annotations

import hmac
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Literal


WebhookEvent = Literal[
    "contact.created",
    "contact.updated",
    "complaint.created",
    "complaint.updated",
    "link.created",
    "link.clicked",
    "export.completed",
    "test",
]


@dataclass
class WebhookPayload:
    """Parsed webhook payload."""

    event: WebhookEvent
    timestamp: str
    data: dict[str, Any]
    delivery_id: str

    @property
    def contact_id(self) -> str | None:
        """Get contact ID from data (for contact events)."""
        return self.data.get("contactId")

    @property
    def link_code(self) -> str | None:
        """Get link code from data."""
        return self.data.get("linkCode")

    @property
    def email(self) -> str | None:
        """Get email from data (if PII mode allows)."""
        return self.data.get("email")

    @property
    def email_hash(self) -> str | None:
        """Get email hash from data."""
        return self.data.get("emailHash")

    @property
    def phone(self) -> str | None:
        """Get phone from data (if PII mode allows)."""
        return self.data.get("phone")

    @property
    def phone_hash(self) -> str | None:
        """Get phone hash from data."""
        return self.data.get("phoneHash")


class WebhookVerifier:
    """Verify and parse EZUnsub webhook payloads.

    Example:
        ```python
        from ezunsub import WebhookVerifier

        verifier = WebhookVerifier(secret="your-webhook-secret")

        # In your webhook handler (e.g., Flask/FastAPI)
        @app.post("/webhooks/ezunsub")
        def handle_webhook(request):
            signature = request.headers.get("X-Webhook-Signature")
            timestamp = request.headers.get("X-Webhook-Timestamp")
            delivery_id = request.headers.get("X-Webhook-Delivery-Id")
            body = request.get_data(as_text=True)

            try:
                payload = verifier.verify_and_parse(
                    signature=signature,
                    timestamp=timestamp,
                    body=body,
                    delivery_id=delivery_id,
                )

                if payload.event == "contact.created":
                    print(f"New contact: {payload.email_hash}")
                elif payload.event == "contact.updated":
                    print(f"Contact updated: {payload.contact_id}")

                return {"status": "ok"}
            except ValueError as e:
                return {"error": str(e)}, 400
        ```
    """

    def __init__(self, secret: str, max_age_seconds: int = 300):
        """Initialize webhook verifier.

        Args:
            secret: Webhook secret from EZUnsub.
            max_age_seconds: Maximum age for webhook timestamps (default: 300s / 5min).
        """
        self.secret = secret
        self.max_age_seconds = max_age_seconds

    def verify_signature(self, signature: str, timestamp: int, body: str) -> bool:
        """Verify webhook signature.

        Args:
            signature: Signature from X-Webhook-Signature header.
            timestamp: Timestamp from X-Webhook-Timestamp header.
            body: Raw request body.

        Returns:
            True if signature is valid, False otherwise.
        """
        # Check timestamp is within acceptable range
        now = int(time.time())
        if abs(now - timestamp) > self.max_age_seconds:
            return False

        # Calculate expected signature
        message = f"{timestamp}.{body}"
        expected = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Extract signature value (remove "sha256=" prefix if present)
        sig_value = signature
        if signature.startswith("sha256="):
            sig_value = signature[7:]

        return hmac.compare_digest(expected, sig_value)

    def verify_and_parse(
        self,
        signature: str,
        timestamp: str | int,
        body: str,
        delivery_id: str = "",
    ) -> WebhookPayload:
        """Verify signature and parse webhook payload.

        Args:
            signature: Signature from X-Webhook-Signature header.
            timestamp: Timestamp from X-Webhook-Timestamp header.
            body: Raw request body (JSON string).
            delivery_id: Delivery ID from X-Webhook-Delivery-Id header.

        Returns:
            Parsed webhook payload.

        Raises:
            ValueError: If signature is invalid or payload is malformed.
        """
        import json

        # Convert timestamp to int
        ts = int(timestamp) if isinstance(timestamp, str) else timestamp

        # Verify signature
        if not self.verify_signature(signature, ts, body):
            raise ValueError("Invalid webhook signature")

        # Parse body
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}")

        # Validate required fields
        if "event" not in data:
            raise ValueError("Missing 'event' field in payload")
        if "timestamp" not in data:
            raise ValueError("Missing 'timestamp' field in payload")
        if "data" not in data:
            raise ValueError("Missing 'data' field in payload")

        return WebhookPayload(
            event=data["event"],
            timestamp=data["timestamp"],
            data=data["data"],
            delivery_id=delivery_id,
        )

    @staticmethod
    def extract_headers(headers: dict[str, str]) -> tuple[str, str, str, str]:
        """Extract webhook headers from a request.

        Args:
            headers: Request headers dict.

        Returns:
            Tuple of (signature, timestamp, event, delivery_id).

        Raises:
            ValueError: If required headers are missing.
        """
        # Handle case-insensitive headers
        normalized = {k.lower(): v for k, v in headers.items()}

        signature = normalized.get("x-webhook-signature")
        timestamp = normalized.get("x-webhook-timestamp")
        event = normalized.get("x-webhook-event")
        delivery_id = normalized.get("x-webhook-delivery-id", "")

        if not signature:
            raise ValueError("Missing X-Webhook-Signature header")
        if not timestamp:
            raise ValueError("Missing X-Webhook-Timestamp header")

        return signature, timestamp, event or "", delivery_id
