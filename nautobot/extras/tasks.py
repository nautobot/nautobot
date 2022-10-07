from logging import getLogger

import requests
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from jinja2.exceptions import TemplateError

from nautobot.core.celery import nautobot_task
from nautobot.extras.choices import CustomFieldTypeChoices, ObjectChangeActionChoices
from nautobot.extras.utils import generate_signature


logger = getLogger("nautobot.extras.tasks")


@nautobot_task
def update_custom_field_choice_data(field_id, old_value, new_value):
    """
    Update the values for a custom field choice used in objects' _custom_field_data for the given field.

    Args:
        field_id (uuid4): The PK of the custom field to which this choice value relates
        old_value (str): The existing value of the choice
        new_value (str): The value which will be used as replacement
    """
    from nautobot.extras.models import CustomField

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        logger.error(f"Custom field with ID {field_id} not found, failing to act on choice data.")
        return False

    if field.type == CustomFieldTypeChoices.TYPE_SELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            # 2.0 TODO: #824 field.slug rather than field.name
            for obj in model.objects.filter(**{f"_custom_field_data__{field.name}": old_value}):
                obj._custom_field_data[field.name] = new_value
                obj.save()

    elif field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            # 2.0 TODO: #824 field.slug rather than field.name
            for obj in model.objects.filter(**{f"_custom_field_data__{field.name}__contains": old_value}):
                old_list = obj._custom_field_data[field.name]
                new_list = [new_value if e == old_value else e for e in old_list]
                obj._custom_field_data[field.name] = new_list
                obj.save()

    else:
        logger.error(f"Unknown field type, failing to act on choice data for this field {field.name}.")
        return False

    return True


# 2.0 TODO: #824 rename field_name to field_slug
@nautobot_task
def delete_custom_field_data(field_name, content_type_pk_set):
    """
    Delete the values for a custom field

    Args:
        field_name (str): The name of the custom field which is being deleted
        content_type_pk_set (list): List of PKs for content types to act upon
    """
    with transaction.atomic():
        for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
            model = ct.model_class()
            for obj in model.objects.filter(**{f"_custom_field_data__{field_name}__isnull": False}):
                del obj._custom_field_data[field_name]
                obj.save()


@nautobot_task
def provision_field(field_id, content_type_pk_set):
    """
    Provision a new custom field on all relevant content type object instances.

    Args:
        field_id (uuid4): The PK of the custom field being provisioned
        content_type_pk_set (list): List of PKs for content types to act upon
    """
    from nautobot.extras.models import CustomField

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        logger.error(f"Custom field with ID {field_id} not found, failing to provision.")
        return False

    with transaction.atomic():
        for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
            model = ct.model_class()
            for obj in model.objects.all():
                # 2.0 TODO: #824 field.slug rather than field.name
                obj._custom_field_data.setdefault(field.name, field.default)
                obj.save()

    return True


@nautobot_task
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
