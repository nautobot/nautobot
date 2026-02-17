from logging import getLogger

from django.conf import settings
from jinja2.exceptions import TemplateError
import requests

from nautobot.core import celery
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.utils import generate_signature

# Get an instance of a logger

logger = getLogger("nautobot.extras.tasks")


@celery.nautobot_task
def process_webhook(webhook_pk, data, model_name, event, timestamp, username, request_id, snapshots):
    """
    Make a POST request to the defined Webhook
    """
    from nautobot.extras.models import Webhook  # avoiding circular import

    webhook = Webhook.objects.get(pk=webhook_pk)

    context = {
        "event": dict(ObjectChangeActionChoices)[event].lower(),
        "timestamp": timestamp,
        "model": model_name,
        "username": username,
        "request_id": request_id,
        "data": data,
        "snapshots": snapshots,
    }

    # Build the headers for the HTTP request
    headers = {
        "Content-Type": webhook.http_content_type,
    }
    try:
        headers.update(webhook.render_headers(context))
    except (TemplateError, ValueError) as e:
        logger.error("Error parsing HTTP headers for webhook %s: %s", webhook, e)
        raise

    # Render the request body
    try:
        body = webhook.render_body(context)
    except TemplateError as e:
        logger.error("Error rendering request body for webhook %s: %s", webhook, e)
        raise

    # Prepare the HTTP request
    params = {
        "method": webhook.http_method,
        "url": webhook.payload_url,
        "headers": headers,
        "data": body.encode("utf8"),
    }
    logger.info("Sending %s request to %s (%s %s)", params["method"], params["url"], context["model"], context["event"])
    logger.debug("%s", params)
    try:
        prepared_request = requests.Request(**params).prepare()
    except requests.exceptions.RequestException as e:
        logger.error("Error forming HTTP request: %s", e)
        raise

    # If a secret key is defined, sign the request with a hash of the key and its content
    if webhook.secret != "":
        prepared_request.headers["X-Hook-Signature"] = generate_signature(prepared_request.body, webhook.secret)

    # Send the request
    with requests.Session() as session:
        session.verify = webhook.ssl_verification
        if webhook.ca_file_path:
            session.verify = webhook.ca_file_path
        response = session.send(prepared_request, proxies=settings.HTTP_PROXIES)

    if response.ok:
        logger.info("Request succeeded; response status %s", response.status_code)
        return f"Status {response.status_code} returned, webhook successfully processed."
    else:
        logger.warning("Request failed; response status %s: %s", response.status_code, response.content)
        raise requests.exceptions.RequestException(
            f"Status {response.status_code} returned with content '{response.content}', webhook FAILED to process."
        )
