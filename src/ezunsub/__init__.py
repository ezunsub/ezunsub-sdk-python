"""EZUnsub Python SDK - Contact suppression and unsubscribe management."""

from .client import EZUnsubClient
from .webhook import WebhookVerifier, WebhookEvent, WebhookPayload
from .exceptions import (
    EZUnsubError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

__version__ = "0.1.0"
__all__ = [
    "EZUnsubClient",
    "WebhookVerifier",
    "WebhookEvent",
    "WebhookPayload",
    "EZUnsubError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
]
