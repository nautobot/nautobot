from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# This import is not used but removing it exposes a module loading order issue preventing nautobot from running
import nautobot.utilities.utils  # noqa F401

from nautobot.utilities.api import get_serializer_for_model
from nautobot.extras.models import Webhook, ObjectChange
from nautobot.extras.registry import registry
from nautobot.extras.tasks import process_webhook
from .choices import ObjectChangeActionChoices


def enqueue_webhooks(instance, user, request_id, action):
    """
    Find Webhook(s) assigned to this instance + action and enqueue them
    to be processed
    """
    # Determine whether this type of object supports webhooks
    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    if model_name not in registry["model_features"]["webhooks"].get(app_label, []):
        return

    # Retrieve any applicable Webhooks
    content_type = ContentType.objects.get_for_model(instance)
    action_flag = {
        ObjectChangeActionChoices.ACTION_CREATE: "type_create",
        ObjectChangeActionChoices.ACTION_UPDATE: "type_update",
        ObjectChangeActionChoices.ACTION_DELETE: "type_delete",
    }[action]
    webhooks = Webhook.objects.filter(content_types=content_type, enabled=True, **{action_flag: True})

    if webhooks.exists():
        # Get the Model's API serializer class and serialize the object
        serializer_class = get_serializer_for_model(instance.__class__)
        serializer_context = {
            "request": None,
        }
        serializer = serializer_class(instance, context=serializer_context)
        changed_object_type = ContentType.objects.get_for_model(instance)
        most_recent_change = ObjectChange.objects.filter(
            changed_object_type=changed_object_type,
            changed_object_id=instance.id,
        ).first()
        snapshots = most_recent_change.get_snapshots()

        # Enqueue the webhooks
        for webhook in webhooks:
            args = [
                webhook.pk,
                serializer.data,
                instance._meta.model_name,
                action,
                str(timezone.now()),
                user.username,
                request_id,
                snapshots,
            ]
            process_webhook.apply_async(args=args)
