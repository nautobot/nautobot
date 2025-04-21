from logging import getLogger

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from jinja2.exceptions import TemplateError
import requests

from nautobot.core.celery import nautobot_task
from nautobot.core.models.query_functions import JSONRemove, JSONSet
from nautobot.extras.choices import CustomFieldTypeChoices, ObjectChangeActionChoices
from nautobot.extras.utils import generate_signature

logger = getLogger("nautobot.extras.tasks")


def _generate_bulk_object_changes(context, queryset, task_logger):
    # Circular import
    from nautobot.extras.context_managers import (
        change_logging,
        ChangeContext,
        deferred_change_logging_for_bulk_operation,
    )
    from nautobot.extras.signals import _handle_changed_object

    task_logger.info("Creating deferred ObjectChange records for bulk operation...")

    # Note: we use change_logging() here instead of web_request_context() because we don't want these change records to
    #       trigger jobhooks and webhooks.
    # TODO: this could be made much faster if we ensure the queryset has appropriate select_related/prefetch_related?
    change_context = ChangeContext(**context)
    i = 0
    with change_logging(change_context):
        with deferred_change_logging_for_bulk_operation():
            for i, instance in enumerate(queryset.iterator(), start=1):
                _handle_changed_object(queryset.model, instance, created=False)

    task_logger.info("Created %d ObjectChange records", i)


@nautobot_task(soft_time_limit=1800, time_limit=2000)
def update_custom_field_choice_data(field_id, old_value, new_value, change_context=None):
    """
    Update the values for a custom field choice used in objects' _custom_field_data for the given field.

    Args:
        field_id (uuid4): The PK of the custom field to which this choice value relates
        old_value (str): The existing value of the choice
        new_value (str): The value which will be used as replacement
        change_context (dict): Optional dict representation of change context for ObjectChange creation
    """
    # Circular Import
    from nautobot.extras.context_managers import web_request_context
    from nautobot.extras.models import CustomField

    task_logger = getLogger("celery.task.update_custom_field_choice_data")

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        task_logger.error("Custom field with ID %s not found, failing to act on choice data.", field_id)
        raise

    if field.type == CustomFieldTypeChoices.TYPE_SELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            queryset = model.objects.filter(**{f"_custom_field_data__{field.key}": old_value})
            if change_context is not None:
                pk_list = list(queryset.values_list("pk", flat=True))
            task_logger.info(
                "Updating selection for custom field `%s` from `%s` to `%s` on %s records...",
                field.key,
                old_value,
                new_value,
                ct.model,
                extra={"object": field},
            )
            count = queryset.update(_custom_field_data=JSONSet("_custom_field_data", field.key, new_value))
            task_logger.info("Updated %d records", count)
            if change_context is not None:
                # Since we used update() above, we bypassed ObjectChange automatic creation via signals. Create them now
                _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pk_list), task_logger)

    elif field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
        # Loop through all field content types and search for values to update
        # TODO: can we implement a bulk operator for this?
        for ct in field.content_types.all():
            model = ct.model_class()
            if change_context is not None:
                with web_request_context(**change_context):
                    for obj in model.objects.filter(**{f"_custom_field_data__{field.key}__contains": old_value}):
                        old_list = obj._custom_field_data[field.key]
                        new_list = [new_value if e == old_value else e for e in old_list]
                        obj._custom_field_data[field.key] = new_list
                        obj.save()
            else:
                for obj in model.objects.filter(**{f"_custom_field_data__{field.key}__contains": old_value}):
                    old_list = obj._custom_field_data[field.key]
                    new_list = [new_value if e == old_value else e for e in old_list]
                    obj._custom_field_data[field.key] = new_list
                    obj.save()

    else:
        task_logger.error(f"Unknown field type, failing to act on choice data for this field {field.key}.")
        raise ValueError

    return True


@nautobot_task(soft_time_limit=1800, time_limit=2000)
def delete_custom_field_data(field_key, content_type_pk_set, change_context=None):
    """
    Delete the values for a custom field

    Args:
        field_key (str): The key of the custom field which is being deleted
        content_type_pk_set (list): List of PKs for content types to act upon
        change_context (dict): Optional change context for ObjectChange creation
    """
    task_logger = getLogger("celery.task.delete_custom_field_data")
    for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
        model = ct.model_class()
        queryset = model.objects.filter(**{f"_custom_field_data__{field_key}__isnull": False})
        pk_list = []
        if change_context is not None:
            pk_list = list(queryset.values_list("pk", flat=True))
        task_logger.info("Deleting existing values for custom field `%s` from %s records...", field_key, ct.model)
        count = queryset.update(_custom_field_data=JSONRemove("_custom_field_data", field_key))
        task_logger.info("Updated %d records", count)
        if count and change_context is not None:
            # Since we used update() above, we bypassed ObjectChange automatic creation via signals. Create them now
            _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pk_list), task_logger)


@nautobot_task(soft_time_limit=1800, time_limit=2000)
def provision_field(field_id, content_type_pk_set, change_context=None):
    """
    Provision a new custom field on all relevant content type object instances.

    Args:
        field_id (uuid4): The PK of the custom field being provisioned
        content_type_pk_set (list): List of PKs for content types to act upon
        change_context (dict): Optional change context for ObjectChange creation.
    """
    # Circular Import
    from nautobot.extras.models import CustomField

    task_logger = getLogger("celery.task.provision_field")

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        task_logger.error(f"Custom field with ID {field_id} not found, failing to provision.")
        raise

    for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
        model = ct.model_class()
        queryset = model.objects.filter(**{f"_custom_field_data__{field.key}__isnull": True})
        pk_list = []
        if change_context is not None:
            pk_list = list(queryset.values_list("pk", flat=True))
        task_logger.info(
            "Adding data for custom field `%s` to %s records...",
            field.key,
            ct.model,
            extra={"object": field},
        )
        count = queryset.update(_custom_field_data=JSONSet("_custom_field_data", field.key, field.default))
        task_logger.info("Updated %d records.", count)
        if count and change_context is not None:
            # Since we used update() above, we bypassed ObjectChange automatic creation via signals. Create them now
            _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pk_list), task_logger)

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
