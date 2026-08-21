# Webhooks

A webhook is a mechanism for notifying an external system when a change occurs in Nautobot. For example, you might want to alert a monitoring tool whenever a device's status is updated. This can be achieved by creating a webhook for the device model and specifying a receiver URL. When Nautobot detects a change, it sends an HTTP request with details about the event and the user who triggered it.

Webhooks are managed via the web UI under **Extensibility > Webhooks**.

## Configuring a Webhook

When setting up a webhook, you need to define the following parameters:

| Parameter | Description |
|-----------|-------------|
| **Name** | A unique name for the webhook (not included in outgoing messages). |
| **Object type(s)** | The type(s) of Nautobot objects that trigger the webhook. |
| **Enabled** | Indicates whether the webhook is active. |
| **Events** | Select one or more events: `create`, `update`, or `delete`. |
| **HTTP method** | The type of HTTP request (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`). |
| **URL** | The fully qualified URL of the receiver. You can specify a port if needed. |
| **HTTP content type** | Sets the `Content-Type` header (default: `application/json`). |
| **Additional headers** | Custom headers, one per line (`Name: Value`). Supports Jinja2 templating. |
| **Body template** | Custom request body. Supports Jinja2 templating. If empty, Nautobot sends the default payload. |
| **Secret** | A secret string used for HMAC (SHA-512) authentication. The webhook request includes an `X-Hook-Signature` header. |
| **SSL verification** | If unchecked, Nautobot skips SSL certificate validation (use with caution). |
| **CA file path** | Specifies a custom CA file for SSL validation. |

## Jinja2 Template Support

[Jinja2 templating](https://jinja.palletsprojects.com/) is supported for the `additional_headers` and `body_template` fields. It allows you to customize headers and request bodies dynamically. This is useful for formatting webhook payloads to match external system expectations.

Example: Trigger a Slack message when a new IP address is created.

**Webhook Configuration:**

- **Object type**: IPAM > IP address
- **HTTP method**: `POST`
- **URL**: Slack incoming webhook URL
- **HTTP content type**: `application/json`
- **Body template**:
  
  ```json
  {"text": "IP address {{ data['address'] }} was created by {{ username }}!"}
  ```

### Available Context Variables

| Variable | Description |
|----------|-------------|
| `event` | The event type (`created`, `updated`, `deleted`). |
| `model` | The Nautobot model triggering the event. |
| `timestamp` | The event timestamp in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format. |
| `username` | The user who triggered the event. |
| `request_id` | A unique request ID for correlation of multiple changes associated with a single request. |
| `data` | A serialized representation of the object *after* the change. |
| `snapshots` | Contains `prechange`, `postchange`, and `differences` snapshots. |

## Default Request Body

If no body template is provided, Nautobot sends a default JSON payload:

```json
{
    "event": "created",
    "timestamp": "2023-02-14T12:34:56.000000+00:00",
    "model": "location",
    "username": "admin",
    "request_id": "fab0a4fb-52ba-4cb4-9756-4e6a3ac05332",
    "data": {
        "id": "5e4f9a91-372b-46df-a50a-c26357475bee",
        "display": "Campus A",
        "url": "/api/dcim/locations/5e4f9a91-372b-46df-a50a-c26357475bee/",
        "name": "Campus A",
        "status": {
            "display": "Active",
            "id": "363a431c-c784-40b5-8513-758cafd174ad",
            "url": "/api/extras/statuses/363a431c-c784-40b5-8513-758cafd174ad/",
            "name": "Active",
            "created": "2023-02-14T00:00:00Z",
            "last_updated": "2023-02-14T19:40:13.216150Z"
        },
        ...
    },
    "snapshots": {
        "prechange": null,
        "postchange": {
            "id": "5e4f9a91-372b-46df-a50a-c26357475bee",
            "asn": null,
            "url": "/api/dcim/locations/5e4f9a91-372b-46df-a50a-c26357475bee/",
            "name": "Campus A",
            ...
        },
        "differences": {
            "removed": null,
            "added": {
                "id": "5e4f9a91-372b-46df-a50a-c26357475bee",
                "asn": null,
                "url": "/api/dcim/locations/5e4f9a91-372b-46df-a50a-c26357475bee/",
                "name": "Campus A",
                ...
            }
        }
    }
}
```

## Webhook Processing

When Nautobot detects a relevant change, it queues the webhook in Redis. This ensures that webhook processing does not delay the original request. A Celery worker then dequeues and sends the HTTP request to the specified receiver.

A webhook request is considered successful if the receiver responds with a `2XX` status code. Failed requests can be retried manually via the admin UI.

## Troubleshooting Webhooks

You can test webhooks with external services like [Beeceptor](https://beeceptor.com/) or [Pipedream RequestBin](https://pipedream.com/requestbin). These tools let you inspect webhook payloads and troubleshoot integration issues.

If a webhook does not trigger as expected, ensure that the **Celery worker** process is running and check the Nautobot logs for errors.

## Webhook Administration and Security

Because configured webhooks are sent automatically to another system, and because the data sent by a webhook contains information about the data stored in Nautobot, it's often necessary to restrict what users may configure webhooks, and what systems the webhooks may be sent to. The former is achieved by only granting webhook `add` and `change` [permissions](users/objectpermission.md) to the users that have a legitimate need to manage webhooks, while the later is a bit more involved.

To provide a baseline of security, Nautobot automatically disallows the configuration of webhooks that point to certain classes of IP addresses (link-local, loopback, multicast, and reserved addresses), and at webhook transmission time, webhooks configured to send to a hostname that resolves to such an IP is also automatically blocked. This restriction is built-in to Nautobot and cannot be disabled.

An administrator can further restrict the range of IPs and hosts that webhooks can be sent to by configuring [`WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS`](../administration/configuration/settings.md#webhook_additional_blocked_networks) and/or [`WEBHOOK_ALLOWED_HOSTS`](../administration/configuration/settings.md#webhook_allowed_hosts) in `nautobot_config.py`. The former defines additional IP networks that should be blocked, and the latter defines an allow-list of hosts or domains that are explicitly permitted **despite falling within the `ADDITIONAL_BLOCKED_NETWORKS` networks**. For example, to disallow webhooks to **all** hosts except for those within `example.com`, you could configure:

```python
WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS = ["0.0.0.0/0", "::/0"]
WEBHOOK_ALLOWED_HOSTS = [".example.com"]
```

A third administratively-definable setting is [`WEBHOOK_ALLOWED_SCHEMES`](../administration/configuration/settings.md#webhook_allowed_schemes). This defaults to `["http", "https"]` but can be configured if desired, for example to disallow HTTP-only webhooks or to allow specific additional protocols.
