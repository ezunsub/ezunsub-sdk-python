"""Tests for webhook verification."""

import json
import time
import hmac
import hashlib

import pytest

from ezunsub import WebhookVerifier, WebhookPayload


def create_signature(secret: str, timestamp: int, body: str) -> str:
    """Create a valid webhook signature."""
    message = f"{timestamp}.{body}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


class TestWebhookVerifier:
    def test_verify_valid_signature(self):
        secret = "test-secret-123"
        timestamp = int(time.time())
        body = '{"event":"contact.created","timestamp":"2024-01-15T10:00:00Z","data":{}}'

        verifier = WebhookVerifier(secret=secret)
        signature = create_signature(secret, timestamp, body)

        assert verifier.verify_signature(f"sha256={signature}", timestamp, body) is True

    def test_verify_invalid_signature(self):
        secret = "test-secret-123"
        timestamp = int(time.time())
        body = '{"event":"contact.created","timestamp":"2024-01-15T10:00:00Z","data":{}}'

        verifier = WebhookVerifier(secret=secret)

        assert verifier.verify_signature("sha256=invalid", timestamp, body) is False

    def test_verify_expired_timestamp(self):
        secret = "test-secret-123"
        timestamp = int(time.time()) - 600  # 10 minutes ago
        body = '{"event":"contact.created","timestamp":"2024-01-15T10:00:00Z","data":{}}'

        verifier = WebhookVerifier(secret=secret, max_age_seconds=300)
        signature = create_signature(secret, timestamp, body)

        assert verifier.verify_signature(f"sha256={signature}", timestamp, body) is False

    def test_verify_and_parse_valid(self):
        secret = "test-secret-123"
        timestamp = int(time.time())
        payload = {
            "event": "contact.created",
            "timestamp": "2024-01-15T10:00:00Z",
            "data": {
                "contactId": "abc123",
                "emailHash": "sha1hash",
            },
        }
        body = json.dumps(payload)
        signature = create_signature(secret, timestamp, body)

        verifier = WebhookVerifier(secret=secret)
        result = verifier.verify_and_parse(
            signature=f"sha256={signature}",
            timestamp=str(timestamp),
            body=body,
            delivery_id="delivery-123",
        )

        assert isinstance(result, WebhookPayload)
        assert result.event == "contact.created"
        assert result.contact_id == "abc123"
        assert result.email_hash == "sha1hash"
        assert result.delivery_id == "delivery-123"

    def test_verify_and_parse_invalid_signature(self):
        secret = "test-secret-123"
        timestamp = int(time.time())
        body = '{"event":"contact.created","timestamp":"2024-01-15T10:00:00Z","data":{}}'

        verifier = WebhookVerifier(secret=secret)

        with pytest.raises(ValueError, match="Invalid webhook signature"):
            verifier.verify_and_parse(
                signature="sha256=invalid",
                timestamp=str(timestamp),
                body=body,
            )

    def test_verify_and_parse_invalid_json(self):
        secret = "test-secret-123"
        timestamp = int(time.time())
        body = "not valid json"
        signature = create_signature(secret, timestamp, body)

        verifier = WebhookVerifier(secret=secret)

        with pytest.raises(ValueError, match="Invalid JSON"):
            verifier.verify_and_parse(
                signature=f"sha256={signature}",
                timestamp=str(timestamp),
                body=body,
            )

    def test_extract_headers(self):
        headers = {
            "X-Webhook-Signature": "sha256=abc123",
            "X-Webhook-Timestamp": "1705312800",
            "X-Webhook-Event": "contact.created",
            "X-Webhook-Delivery-Id": "delivery-123",
        }

        sig, ts, event, delivery_id = WebhookVerifier.extract_headers(headers)

        assert sig == "sha256=abc123"
        assert ts == "1705312800"
        assert event == "contact.created"
        assert delivery_id == "delivery-123"

    def test_extract_headers_missing_signature(self):
        headers = {
            "X-Webhook-Timestamp": "1705312800",
        }

        with pytest.raises(ValueError, match="Missing X-Webhook-Signature"):
            WebhookVerifier.extract_headers(headers)
