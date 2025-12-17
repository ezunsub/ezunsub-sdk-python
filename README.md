# EZUnsub Python SDK

Official Python SDK for [EZUnsub](https://ezunsub.com) - Contact suppression and unsubscribe management for affiliate marketing compliance.

## Installation

```bash
pip install ezunsub
```

## Quick Start

```python
from ezunsub import EZUnsubClient

# Initialize client
client = EZUnsubClient(
    api_key="your-api-key",
    base_url="https://your-ezunsub-instance.com"
)

# List contacts
contacts = client.contacts.list(page=1, limit=50)

# Get contact statistics
stats = client.contacts.stats()
print(f"Total contacts: {stats['total']}")

# Create a webhook
webhook = client.webhooks.create(
    name="My Webhook",
    url="https://my-app.com/webhooks/ezunsub",
    events=["contact.created", "contact.updated"]
)
print(f"Webhook secret (save this!): {webhook['secret']}")
```

## Webhook Verification

Verify incoming webhooks from EZUnsub:

```python
from ezunsub import WebhookVerifier

verifier = WebhookVerifier(secret="your-webhook-secret")

# In your webhook handler (Flask example)
@app.post("/webhooks/ezunsub")
def handle_webhook():
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

### FastAPI Example

```python
from fastapi import FastAPI, Request, HTTPException
from ezunsub import WebhookVerifier

app = FastAPI()
verifier = WebhookVerifier(secret="your-webhook-secret")

@app.post("/webhooks/ezunsub")
async def handle_webhook(request: Request):
    body = await request.body()

    try:
        payload = verifier.verify_and_parse(
            signature=request.headers.get("X-Webhook-Signature", ""),
            timestamp=request.headers.get("X-Webhook-Timestamp", ""),
            body=body.decode(),
            delivery_id=request.headers.get("X-Webhook-Delivery-Id", ""),
        )

        # Handle the event
        match payload.event:
            case "contact.created":
                await handle_new_contact(payload)
            case "contact.updated":
                await handle_contact_update(payload)
            case "export.completed":
                await handle_export_complete(payload)

        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## API Reference

### Client

```python
from ezunsub import EZUnsubClient

client = EZUnsubClient(
    api_key="your-api-key",
    base_url="https://your-ezunsub-instance.com",
    timeout=30.0  # optional, default 30s
)
```

### Contacts

```python
# List contacts
contacts = client.contacts.list(page=1, limit=50, link_code="abc123")

# Get single contact (admin only)
contact = client.contacts.get("contact-id")

# Delete contact (admin only)
client.contacts.delete("contact-id")

# Get statistics
stats = client.contacts.stats()
```

### Webhooks

```python
# List webhooks
webhooks = client.webhooks.list()

# Create webhook
webhook = client.webhooks.create(
    name="My Webhook",
    url="https://example.com/webhook",
    events=["contact.created", "contact.updated"],
    pii_mode="hashes"  # full, hashes, or none
)

# Update webhook
client.webhooks.update(
    webhook_id="webhook-id",
    is_active=False
)

# Delete webhook
client.webhooks.delete("webhook-id")

# Rotate secret
new_webhook = client.webhooks.rotate_secret("webhook-id")

# Send test
result = client.webhooks.test("webhook-id")

# Get delivery history
deliveries = client.webhooks.deliveries("webhook-id", limit=50)

# Get available events
events = client.webhooks.events()
```

### Links

```python
# List links
links = client.links.list(offer_id="offer-id")

# Get link
link = client.links.get("link-code")

# Create link
link = client.links.create(offer_id="offer-id", name="My Link")
```

### Offers

```python
# List offers
offers = client.offers.list()

# Get offer
offer = client.offers.get("offer-id")
```

### Exports

```python
# List exports
exports = client.exports.list()

# Get export
export = client.exports.get("export-id")

# Create export
export = client.exports.create(
    name="My Export",
    filters={"status": "suppressed"}
)
```

## Webhook Events

| Event | Description |
|-------|-------------|
| `contact.created` | New contact added to suppression list |
| `contact.updated` | Contact record updated |
| `complaint.created` | New complaint filed |
| `complaint.updated` | Complaint status changed |
| `link.created` | New unsubscribe link created |
| `link.clicked` | Unsubscribe link was clicked |
| `export.completed` | Export job finished |

## Webhook Payload

All webhooks include these headers:

| Header | Description |
|--------|-------------|
| `X-Webhook-Signature` | HMAC-SHA256 signature (`sha256=...`) |
| `X-Webhook-Timestamp` | Unix timestamp |
| `X-Webhook-Event` | Event type |
| `X-Webhook-Delivery-Id` | Unique delivery ID |

Payload structure:

```json
{
  "event": "contact.created",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "data": {
    "contactId": "abc123",
    "linkCode": "xyz789",
    "emailHash": "sha1-hash",
    "phoneHash": "sha1-hash",
    "status": "suppressed"
  }
}
```

## Error Handling

```python
from ezunsub import (
    EZUnsubClient,
    EZUnsubError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

client = EZUnsubClient(api_key="your-api-key")

try:
    contact = client.contacts.get("invalid-id")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Contact not found")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except EZUnsubError as e:
    print(f"API error: {e.message} (status: {e.status_code})")
```

## License

MIT
