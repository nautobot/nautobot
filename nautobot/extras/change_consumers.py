"""Determining whether anything actually consumes a given object change.

The consumers of an `ObjectChange` are Webhooks, JobHooks, and event brokers. `change_has_consumers()`
reports whether any of them is configured for a given content type and action, so that callers can skip
work done solely to feed them.
"""

import contextlib
import logging

from django.conf import settings
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

    The Webhook/JobHook half of the answer is cached for `CACHES["default"]["TIMEOUT"]`; `nautobot.extras.signals`
    invalidates it when a Webhook or JobHook changes. Event brokers are checked on every call rather than cached,
    because they live in process memory while the cache outlives the process that populated it.

    Args:
        content_type (ContentType): Content type of the changed object.
        action (str): One of the `ObjectChangeActionChoices` values.

    Returns:
        (bool): True if at least one consumer would be triggered, or if that could not be determined.
    """
    if action not in ObjectChangeActionChoices.HOOK_FLAGS:
        logger.warning("Unrecognized change action %r; assuming a consumer exists", action)
        return True

    # Intentionally before checking the cache: a `False` value stored in the cache will outlive the process that
    # calculated it, so caching this value would hide a broker added later to EVENT_BROKERS (or registered by the
    # application), and there would be nothing to invalidate this value. This is a memory scan without queries, so
    # caching this value offers no benefits.
    if event_topic_has_subscriber(get_change_event_topic(content_type, action)):
        return True

    # Not branch-aware: Webhook and JobHook aren't version-controlled, so the answer can't vary by branch.
    cache_key = construct_cache_key(
        change_has_consumers, branch_aware=False, content_type=content_type.pk, action=action
    )
    try:
        value, _ = cache_get_or_set(
            cache_key,
            lambda: _compute_change_has_consumers(content_type, action),
            # Bounded, not indefinite: an invalidation can be lost to a race or a rolled-back transaction,
            # and a permanent stale `False` would silence a live webhook.
            timeout=settings.CACHES["default"]["TIMEOUT"],
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
    """Uncached Webhook/JobHook half of `change_has_consumers()`."""
    hook_filter = {"content_types": content_type, "enabled": True, ObjectChangeActionChoices.HOOK_FLAGS[action]: True}

    # Determine whether this type of object supports webhooks
    supports_webhooks = content_type.model in registry["model_features"]["webhooks"].get(content_type.app_label, [])
    if supports_webhooks and Webhook.objects.filter(**hook_filter).exists():
        return True

    # Determine whether this type of object supports job hooks
    supports_job_hooks = content_type in change_logged_models_queryset()
    return supports_job_hooks and JobHook.objects.filter(**hook_filter).exists()
