# Webhooks

A webhook is a mechanism for conveying to some external system a change that took place in Nautobot. For example, you may want to notify a monitoring system whenever the status of a device is updated in Nautobot. This can be done by creating a webhook for the device model in Nautobot and identifying the webhook receiver. When Nautobot detects a change to a device, an HTTP request containing the details of the change and who made it be sent to the specified receiver. Webhooks are configured in the web UI under Extensibility > Webhooks.

## Configuration

* **Name** - A unique name for the webhook. The name is not included with outbound messages.
* **Object type(s)** - The type or types of Nautobot object that will trigger the webhook.
* **Enabled** - If unchecked, the webhook will be inactive.
* **Events** - A webhook may trigger on any combination of create, update, and delete events. At least one event type must be selected.
* **HTTP method** - The type of HTTP request to send. Options include `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`.
* **URL** - The fuly-qualified URL of the request to be sent. This may specify a destination port number if needed.
* **HTTP content type** - The value of the request's `Content-Type` header. (Defaults to `application/json`)
* **Additional headers** - Any additional headers to include with the request (optional). Add one header per line in the format `Name: Value`. Jinja2 templating is supported for this field (see below).
* **Body template** - The content of the request being sent (optional). Jinja2 templating is supported for this field (see below). If blank, Nautobot will populate the request body with a raw dump of the webhook context. (If the HTTP content-type is set to `application/json`, this will be formatted as a JSON object.)
* **Secret** - A secret string used to prove authenticity of the request (optional). This will append a `X-Hook-Signature` header to the request, consisting of a HMAC (SHA-512) hex digest of the request body using the secret as the key.
* **SSL verification** - Uncheck this option to disable validation of the receiver's SSL certificate. (Disable with caution!)
* **CA file path** - The file path to a particular certificate authority (CA) file to use when validating the receiver's SSL certificate (optional).

## Jinja2 Template Support

[Jinja2 templating](https://jinja.palletsprojects.com/) is supported for the `additional_headers` and `body_template` fields. This enables the user to convey object data in the request headers as well as to craft a customized request body. Request content can be crafted to enable the direct interaction with external systems by ensuring the outgoing message is in a format the receiver expects and understands.

For example, you might create a Nautobot webhook to [trigger a Slack message](https://api.slack.com/messaging/webhooks) any time an IP address is created. You can accomplish this using the following configuration:

* Object type: IPAM > IP address
* HTTP method: `POST`
* URL: Slack incoming webhook URL
* HTTP content type: `application/json`
* Body template: `{"text": "IP address {{ data['address'] }} was created by {{ username }}!"}`

### Available Context

The following data is available as context for Jinja2 templates:

* `event` - The type of event which triggered the webhook: created, updated, or deleted.
* `model` - The Nautobot model which triggered the change.
* `timestamp` - The time at which the event occurred (in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format).
* `username` - The name of the user account associated with the change.
* `request_id` - The unique request ID. This may be used to correlate multiple changes associated with a single request.
* `data` - A serialized representation of the object _after_ the change was made. This is typically equivalent to the model's representation in Nautobot's REST API.

+++ 1.3.0
    * `snapshots` - snapshots of the serialized object state both before and after the change was made; provided as a dictionary with keys named `prechange`, `postchange` and `differences`.

### Default Request Body

If no body template is specified, the request body will be populated with a JSON object containing the context data. For example, a newly created Location might appear as follows:

```no-highlight
{
    "event": "created",
    "timestamp": "2023-02-14 12:34:56.000000+00:00",
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

When a change is detected, any resulting webhooks are placed into a Redis queue for processing. This allows the user's request to complete without needing to wait for the outgoing webhook(s) to be processed. The webhooks are then extracted from the queue by the `celery worker` process and HTTP requests are sent to their respective destinations.

A request is considered successful if the response has a 2XX status code; otherwise, the request is marked as having failed. Failed requests may be retried manually via the admin UI.

## Troubleshooting

To assist with verifying that the content of outgoing webhooks is rendered correctly, Nautobot provides a simple HTTP listener that can be run locally to receive and display webhook requests. First, modify the target URL of the desired webhook to `http://localhost:9000/`. This will instruct Nautobot to send the request to the local server on TCP port 9000. Then, start the webhook receiver service from the Nautobot root directory:

```no-highlight
nautobot-server webhook_receiver
```

Example output:

```no-highlight
Listening on port http://localhost:9000. Stop with CONTROL-C.
```

You can test the receiver itself by sending any HTTP request to it. For example:

```no-highlight
curl -X POST http://localhost:9000 --data '{"foo": "bar"}'
```

The server will print output similar to the following:

```no-highlight
[1] Tue, 07 Apr 2020 17:44:02 GMT 127.0.0.1 "POST / HTTP/1.1" 200 -
Host: localhost:9000
User-Agent: curl/7.58.0
Accept: */*
Content-Length: 14
Content-Type: application/x-www-form-urlencoded

{"foo": "bar"}
------------
```

Note that `webhook_receiver` does not actually _do_ anything with the information received: It merely prints the request headers and body for inspection.

Now, when the Nautobot webhook is triggered and processed, you should see its headers and content appear in the terminal where the webhook receiver is listening. If you don't, check that the `celery worker` process is running.
