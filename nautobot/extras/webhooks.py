from django.utils import timezone

from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import Webhook
from nautobot.extras.registry import registry
from nautobot.extras.tasks import process_webhook


def enqueue_webhooks(object_change):
    """
    Find Webhook(s) assigned to this instance + action and enqueue them
    to be processed
    """
    # Determine whether this type of object supports webhooks
    app_label = object_change.changed_object_type.app_label
    model_name = object_change.changed_object_type.model
    if model_name not in registry["model_features"]["webhooks"].get(app_label, []):
        return

    # Retrieve any applicable Webhooks
    content_type = object_change.changed_object_type
    action_flag = {
        ObjectChangeActionChoices.ACTION_CREATE: "type_create",
        ObjectChangeActionChoices.ACTION_UPDATE: "type_update",
        ObjectChangeActionChoices.ACTION_DELETE: "type_delete",
    }[object_change.action]
    webhooks = Webhook.objects.filter(content_types=content_type, enabled=True, **{action_flag: True})

    if webhooks.exists():
        # fall back to object_data if object_data_v2 is not available
        serialized_data = object_change.object_data_v2
        if serialized_data is None:
            serialized_data = object_change.object_data

        # Enqueue the webhooks
        for webhook in webhooks:
            args = [
                webhook.pk,
                serialized_data,
                model_name,
                object_change.action,
                str(timezone.now()),
                object_change.user_name,
                object_change.request_id,
                object_change.get_snapshots(),
            ]
            process_webhook.apply_async(args=args)
