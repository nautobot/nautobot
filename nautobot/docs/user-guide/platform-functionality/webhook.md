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

[Jinja2 templating](https://jinja.palletsprojects.com/) allows you to customize headers and request bodies dynamically. This is useful for formatting webhook payloads to match external system expectations.

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
    "data": { "id": "5e4f9a91-372b-46df-a50a-c26357475bee", "name": "Campus A" },
    "snapshots": {
        "prechange": null,
        "postchange": { "id": "5e4f9a91-372b-46df-a50a-c26357475bee", "name": "Campus A" },
        "differences": { "added": { "id": "5e4f9a91-372b-46df-a50a-c26357475bee", "name": "Campus A" } }
    }
}
```

## Webhook Processing

When Nautobot detects a relevant change, it queues the webhook in Redis. This ensures that webhook processing does not delay the original request. A Celery worker then dequeues and sends the HTTP request to the specified receiver.

A webhook request is considered successful if the receiver responds with a `2XX` status code. Failed requests can be retried manually via the admin UI.

## Troubleshooting Webhooks

To inspect outgoing webhooks, you can use a local HTTP listener. Nautobot provides a built-in webhook receiver that logs incoming requests:

1. Set the webhook URL to `http://localhost:9000/`.
2. Start the webhook receiver:

    ```sh
    nautobot-server webhook_receiver
    ```

    Example output:

    ```sh
    Listening on port http://localhost:9000. Stop with CONTROL-C.
    ```

3. Send a test request:

    ```sh
    curl -X POST http://localhost:9000 --data '{"foo": "bar"}'
    ```

    The listener will output:

    ```sh
    [1] Tue, 07 Apr 2020 17:44:02 GMT 127.0.0.1 "POST / HTTP/1.1" 200 -
    Host: localhost:9000
    Content-Type: application/json
    Content-Length: 14

    {"foo": "bar"}
    ```

> **Alternative Testing Tools:**
> Instead of using the built-in webhook receiver, you can test webhooks with external services like [Beeceptor](https://beeceptor.com/) or [Pipedream RequestBin](https://pipedream.com/requestbin). These tools let you inspect webhook payloads and troubleshoot integration issues.

If a webhook does not trigger as expected, ensure that the **celery worker** process is running and check the Nautobot logs for errors.
