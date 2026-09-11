"""Determining whether anything actually consumes a given object change.

The consumers of an `ObjectChange` are Webhooks, JobHooks, and event brokers. `change_has_consumers()`
reports whether any of them is configured for a given content type and action, so that callers can skip
work done solely to feed them.
"""

import contextlib
import logging

from django.core.cache import cache
import redis.exceptions

from nautobot.core.events import event_topic_has_subscriber
from nautobot.core.utils.cache import cache_get_or_set, construct_cache_key, get_request_cache
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import JobHook, Webhook
from nautobot.extras.registry import registry
from nautobot.extras.utils import change_logged_models_queryset

logger = logging.getLogger(__name__)


def get_change_event_topic(content_type, action):
    """Event topic that a change of `action` to an object of `content_type` is published to.

    Examples: `nautobot.create.dcim.device`, `nautobot.update.ipam.ipaddress`.
    """
    return f"nautobot.{action}.{content_type.app_label}.{content_type.model}"


def change_has_consumers(content_type, action):
    """Whether any Webhook, JobHook, or event broker would act on a change with this content type and action.

    Only enabled `Webhook` and `JobHook` records count; an event broker counts when its topic filters
    accept `get_change_event_topic(content_type, action)`.

    The answer is cached indefinitely; `nautobot.extras.signals` invalidates it when a Webhook or JobHook
    changes. Event brokers are registered once at startup, so they need no invalidation.

    Args:
        content_type (ContentType): Content type of the changed object.
        action (str): One of the `ObjectChangeActionChoices` values.

    Returns:
        (bool): True if at least one consumer would be triggered, or if that could not be determined.
    """
    if action not in ObjectChangeActionChoices.HOOK_FLAGS:
        logger.warning("Unrecognized change action %r; assuming a consumer exists", action)
        return True

    # Not branch-aware: Webhook and JobHook aren't version-controlled, so the answer can't vary by branch.
    cache_key = construct_cache_key(
        change_has_consumers, branch_aware=False, content_type=content_type.pk, action=action
    )
    try:
        value, _ = cache_get_or_set(
            cache_key, lambda: _compute_change_has_consumers(content_type, action), timeout=None
        )
    except redis.exceptions.ConnectionError:
        # The cache is an optimization, not a source of truth, so don't fail the save that triggered this.
        value = _compute_change_has_consumers(content_type, action)
    return value


def invalidate_change_consumers_cache():
    """Drop every cached `change_has_consumers()` answer.

    Called from `nautobot.extras.signals` when Webhook or JobHook data changes.
    """
    prefix = construct_cache_key(change_has_consumers, branch_aware=False)

    request_local_cache = get_request_cache()
    if request_local_cache is not None:
        for key in [key for key in request_local_cache if key.startswith(prefix)]:
            del request_local_cache[key]

    with contextlib.suppress(redis.exceptions.ConnectionError):
        cache.delete_pattern(f"{prefix}(*)")


def _compute_change_has_consumers(content_type, action):
    """Uncached form of `change_has_consumers()`."""
    if event_topic_has_subscriber(get_change_event_topic(content_type, action)):
        return True

    hook_filter = {"content_types": content_type, "enabled": True, ObjectChangeActionChoices.HOOK_FLAGS[action]: True}

    # Determine whether this type of object supports webhooks
    supports_webhooks = content_type.model in registry["model_features"]["webhooks"].get(content_type.app_label, [])
    if supports_webhooks and Webhook.objects.filter(**hook_filter).exists():
        return True

    # Determine whether this type of object supports job hooks
    supports_job_hooks = content_type in change_logged_models_queryset()
    return supports_job_hooks and JobHook.objects.filter(**hook_filter).exists()
