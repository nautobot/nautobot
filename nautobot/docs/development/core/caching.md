# Use of Caches and Caching in Nautobot Development

> There are two hard things in computer science: cache invalidation, naming things, and off-by-one errors. -- Jeff Atwood

## Cache APIs

Nautobot uses [Django's cache framework](https://docs.djangoproject.com/en/stable/topics/cache/), specifically the [`django-redis` backend](https://github.com/jazzband/django-redis?tab=readme-ov-file#configure-as-cache-backend), for the majority of its caching use cases. The primary exception is (or should be) the use of the `@cached_property` decorator for information that is specific to an ephemeral object instance and does not need to be cached in any more persistent fashion. Otherwise, use of Django's caching API should be preferred over other libraries and APIs such as `@functools.lru_cache`.

!!! warning
    While the Nautobot development server (`nautobot-server runserver`) generally doesn't persist in-memory data between requests, a production deployment (i.e., uWSGI) has long-running processes which _do_ have persistent memory. We've had bugs sneak in because of this where in-memory caches (`@cached_property`, `@lru_cache`) have a much longer (and incorrect) lifespan in production than they did during development and testing.

## Things to Consider when Adding a Cache

Always consider and account for ways that cached data may become invalid. In many cases, the primary cause of cache invalidation is database changes, so you may need to add appropriate signal handlers to clear caches when such updates occur. This is another reason to prefer Django's shared cache over local in-memory caching, as signals only apply to the process that triggered the signal, and in-memory caches in other processes wouldn't be appropriately cleared by the signal.

When adding a signal that interacts with the cache, you may want to wrap the cache interaction in `with contextlib.suppress(redis.exceptions.ConnectionError)`, as signals may be triggered during database data migrations, during which time it's possible that the Redis server might not be up and operational yet.

## Cache keys

* For database models with caches, cache keys should generally take the form `"nautobot.{model._meta.label_lower}.[{uuid}.]..."`. For example:
    * `Location.objects.max_depth()` --> `nautobot.dcim.location.max_depth`
    * `Location.display` (instance attribute) --> `nautobot.dcim.location.00000000-0000-0000-0000-000000000000.display`
    * `ComputedField.objects.get_for_model(Location)` --> `nautobot.extras.computedfield.get_for_model.dcim.location`
    * `CustomField.objects.get_for_model(Location, False)` --> `nautobot.extras.customfield.get_for_model.dcim.location.False`
* For functions and methods that don't belong to a database model, cache keys should generally take the form `"{dotted.module.path.function}..."`. For example:
    * `nautobot.core.releases.get_latest_release()` --> `nautobot.core.releases.get_latest_release`
    * `nautobot.extras.utils.changed_logged_models_queryset()` --> `nautobot.extras.utils.change_logged_models_queryset`
