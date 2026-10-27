# Use of Caches and Caching in Nautobot Development

> There are two hard things in computer science: cache invalidation, naming things, and off-by-one errors. -- Jeff Atwood

## Cache APIs

Nautobot uses [Django's cache framework](https://docs.djangoproject.com/en/stable/topics/cache/), specifically the [`django-redis` backend](https://github.com/jazzband/django-redis?tab=readme-ov-file#configure-as-cache-backend), for the majority of its caching use cases. The primary exception is (or should be) the use of the `@cached_property` decorator for information that is specific to an ephemeral object instance and does not need to be cached in any more persistent fashion. Otherwise, use of Django's caching API should be preferred over other libraries and APIs such as `@functools.lru_cache`.

!!! warning
    While the Nautobot development server (`nautobot-server runserver`) generally doesn't persist in-memory data between requests, a production deployment (i.e., uWSGI) has long-running processes which _do_ have persistent memory. We've had bugs sneak in because of this where in-memory caches (`@cached_property`, `@lru_cache`) have a much longer (and incorrect) lifespan in production than they did during development and testing.

## Things to Consider when Adding a Cache

Always consider and account for ways that cached data may become invalid. In many cases, the primary cause of cache invalidation is database changes, so you may need to add appropriate signal handlers to clear caches when such updates occur. This is another reason to prefer Django's shared cache over local in-memory caching, as signals only apply to the process that triggered the signal, and in-memory caches in other processes wouldn't be appropriately cleared by the signal.

When such a signal handler (or a model's `save()` or `delete()` method) clears cached data, it should do so with `invalidate_cache()`, as described in [Invalidating Cached Data](#invalidating-cached-data) below.

## Cache keys

In general, cache keys used by Nautobot should be constructed via the `construct_cache_key()` method from `nautobot.core.utils.cache` (or `nautobot.apps.utils`, for App developers). This ensures a consistent structure for cache keys and helps to avoid unintended collisions. Refer to the [function documentation](../../code-reference/nautobot/apps/utils.md#nautobot.apps.utils.construct_cache_key) for examples.

## Invalidating Cached Data

+++ 3.2.9

Clear cached data with `invalidate_cache()` from `nautobot.core.utils.cache`, never by calling `cache.delete()` or `cache.delete_pattern()` directly.

Signal handlers and `save()`/`delete()` methods usually run inside the database transaction that is making the change. If that code deletes a cache entry directly, any other request that misses the cache before the transaction commits still reads the _old_ data from the database and re-caches it. Nothing clears that stale entry until the next invalidation, which for a cache with no timeout may be days or weeks later. For example, a stale list of custom fields causes the REST API to omit a new custom field from its responses and silently discard any values submitted for it.

`invalidate_cache()` deletes the given keys and patterns immediately, so that the rest of the current transaction sees its own changes, and again once the transaction commits (via `transaction.on_commit()`), discarding anything that a concurrent request re-cached in the meantime. Outside of a transaction, the second deletion is a harmless no-op. It also suppresses `redis.exceptions.ConnectionError`, as signals may be triggered during database data migrations, when the Redis server might not be up and operational yet.

```python
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nautobot.core.utils.cache import construct_cache_key, invalidate_cache


@receiver(post_save, sender=MyModel)
@receiver(post_delete, sender=MyModel)
def invalidate_my_model_cache(sender, **kwargs):
    cache_key = construct_cache_key(MyModel.objects, method_name="get_for_model", branch_aware=True)
    invalidate_cache(patterns=[f"{cache_key}(*)"])
```

Pass fully constructed keys and patterns to `invalidate_cache()`, as above. Branch-aware cache keys depend on the branch that is active when the change is made, which may no longer be the active branch by the time the transaction commits.

### Persistent Caches

A cache that is refreshed only by explicit invalidation (a "persistent cache") should be stored with `timeout=settings.PERSISTENT_CACHE_TIMEOUT` rather than `timeout=None`. The [`PERSISTENT_CACHE_TIMEOUT`](../../user-guide/administration/configuration/settings.md#persistent_cache_timeout) setting defaults to `None` (no expiry), but administrators can set it to a number of seconds to bound how long a stale entry can survive.

Even with `invalidate_cache()`, a narrow window remains: a request that read the database just before the commit can write to the cache just after the commit-time invalidation. The timeout is the safety net for that case.

When adding a persistent cache, also add it to the table of cases in `nautobot/core/tests/test_persistent_caches.py`, which verifies that each persistent cache is invalidated on commit and honors `PERSISTENT_CACHE_TIMEOUT`.
