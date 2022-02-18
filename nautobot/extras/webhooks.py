from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from nautobot.utilities.api import get_serializer_for_model
from nautobot.extras.models import Webhook
from nautobot.extras.registry import registry
from nautobot.extras.tasks import process_webhook
from .choices import ObjectChangeActionChoices
from ..utilities.utils import shallow_compare_dict


def get_snapshots(instance, action):
    serializer_class = get_serializer_for_model(instance.__class__)

    prechange = (
        getattr(instance, "_prechange_snapshot", None)
        if action != ObjectChangeActionChoices.ACTION_CREATE
        else None
    )

    postchange = (
        serializer_class(instance, context={"request": None}).data
        if action != ObjectChangeActionChoices.ACTION_DELETE
        else None
    )
    if prechange and postchange:
        diff_added = shallow_compare_dict(prechange, postchange, exclude=["last_updated"])
        diff_removed = {x: prechange.get(x) for x in diff_added}
    elif prechange and not postchange:
        diff_added, diff_removed = None, prechange
    else:
        diff_added, diff_removed = postchange, None

    return {
        "prechange": prechange,
        "postchange": postchange,
        "differences": {"removed": diff_removed, "added": diff_added},
    }


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
        snapshot = get_snapshots(instance, action)

        # Enqueue the webhooks
        for webhook in webhooks:
            args = [
                webhook.pk,
                serializer.data,
                snapshot,
                instance._meta.model_name,
                action,
                str(timezone.now()),
                user.username,
                request_id,
            ]
            process_webhook.apply_async(args=args)
