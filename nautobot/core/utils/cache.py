"""Utilities for conveniently working with the Django/Redis cache."""

from contextlib import contextmanager
import contextvars
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import models

logger = logging.getLogger(__name__)

# Holds a dict for the duration of a `request_cache()` context, or None outside of any such context.
_request_cache_var = contextvars.ContextVar("nautobot_request_cache", default=None)


@contextmanager
def request_cache():
    """
    Context manager providing a small in-process cache scoped to the enclosing block (typically a single request).

    Some model-metadata lookups (e.g. `CustomField.objects.get_for_model()`, `Relationship.objects.get_for_model()`)
    are normally cached in the shared Redis cache with an effectively infinite timeout, invalidated only when the
    underlying data actually changes. That's efficient across requests, but a *single* request that recursively
    serializes many related objects (e.g. the REST API's `depth` query parameter) can end up performing the exact
    same Redis lookup hundreds of times for the exact same cache key, since the data cannot possibly have changed
    partway through handling one request.

    Call sites that support it use `get_request_cache()` to transparently check/populate this local cache in
    addition to the shared Redis cache, eliminating those redundant round-trips. Because this cache is discarded
    the moment the `request_cache()` block exits, it can never serve data that is stale beyond the lifetime of a
    single request, so no additional invalidation logic is required.

    Nested calls reuse the outermost scope's cache rather than creating a new, empty one.
    """
    if _request_cache_var.get() is not None:
        # Already inside a request_cache() scope (e.g. this request is itself triggering a nested request/job) -
        # just reuse the existing cache rather than shadowing it with a new, empty one.
        yield
        return

    token = _request_cache_var.set({})
    try:
        yield
    finally:
        _request_cache_var.reset(token)


def get_request_cache():
    """Return the dict backing the current `request_cache()` scope, or `None` if not currently inside one."""
    return _request_cache_var.get()


def cache_get_or_set(cache_key, compute, *, timeout, cache_hit_callback=None):
    """
    Get `cache_key` from the current `request_cache()` scope if any, else from Redis, else compute and populate both.

    Optionally run a callback on whether the cache was hit or not.
    """
    request_local_cache = get_request_cache()
    if request_local_cache is not None and cache_key in request_local_cache:
        value, hit = request_local_cache[cache_key], True
    else:
        value = cache.get(cache_key)
        hit = value is not None
        if not hit:
            value = compute()
            cache.set(cache_key, value, timeout=timeout)
        if request_local_cache is not None:
            request_local_cache[cache_key] = value

    if cache_hit_callback is not None:
        cache_hit_callback(hit)
    return value, hit


def construct_cache_key(obj, *, method_name=None, branch_aware=True, **params):
    """
    Construct a consistently-structured Django/Redis cache key for the given obj and/or method name.

    Args:
        obj (Any): A model class, model instance, model manager, class, or function that will make use of the cache.
        method_name (str): Name of a specific method on `obj`. May be omitted only if `obj` is itself a function.
        branch_aware (bool): Whether this cache key needs to vary by branch when Version Control is enabled.
        **params (dict): Parameters that should further narrow the scope of the cache key.

    Examples:
        >>> construct_cache_key(Location.objects, method_name="max_depth")
        'nautobot.dcim.location.max_depth'
        >>> construct_cache_key(MinMaxValidationRule, method_name="get_for_model")
        'nautobot.data_validation.minmaxvalidationrule.get_for_model'
        >>> construct_cache_key(MinMaxValidationRule, method_name="get_for_model", content_type="dcim.location")
        'nautobot.data_validation.minmaxvalidationrule.get_for_model(content_type=dcim.location)'
        >>> construct_cache_key(CustomField.objects, method_name="get_for_model", model="dcim.location", exclude_filter_disabled=True, listing=True)
        'nautobot.extras.customfield.get_for_model(model=dcim.location,exclude_filter_disabled=True,listing=True)'
        >>> from nautobot.extras.utils import change_logged_models_queryset
        >>> construct_cache_key(change_logged_models_queryset)
        'nautobot.extras.utils.change_logged_models_queryset'
    """
    method_name_must_be_set = True
    if isinstance(obj, models.Model):
        tokens = ["nautobot", obj._meta.concrete_model._meta.label_lower, str(obj.pk), method_name]
    elif isinstance(obj, models.Manager):
        tokens = ["nautobot", obj.model._meta.concrete_model._meta.label_lower, method_name]
    elif isinstance(obj, type):
        # A class object
        if issubclass(obj, models.Model):
            tokens = ["nautobot", obj._meta.concrete_model._meta.label_lower, method_name]
        elif issubclass(obj, models.Manager):
            tokens = ["nautobot", obj.model._meta.concrete_model._meta.label_lower, method_name]
        else:
            tokens = [obj.__module__, obj.__name__, method_name]
    elif method_name is not None:
        # An instance of any class not specifically handled above
        tokens = [obj.__module__, obj.__class__.__name__, method_name]
    else:
        # A standalone function
        tokens = [obj.__module__, obj.__name__]
        method_name_must_be_set = False

    if method_name_must_be_set and method_name is None:
        raise ValueError("method_name must be specified for the given obj")

    if branch_aware and "nautobot_version_control" in settings.PLUGINS:
        from nautobot_version_control.utils import active_branch  # pylint: disable=import-error

        tokens += ["branch", active_branch()]

    cache_key = ".".join(tokens)

    params_tokens = [f"{key}={value}" for key, value in params.items()]
    if params_tokens:
        cache_key += f"({','.join(params_tokens)})"

    # Disabled as it's very noisy in some cases
    # logger.debug("Constructed cache key is %s", cache_key)
    return cache_key
