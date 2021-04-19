# Caching

Nautobot supports database query caching using [`django-cacheops`](https://github.com/Suor/django-cacheops) and Redis. When a query is made, the results are cached in Redis for a short period of time, as defined by the [`CACHEOPS_DEFAULTS`](../../configuration/optional-settings/#cacheops_defaults) parameter (15 minutes by default). Within that time, all recurrences of that specific query will return the pre-fetched results from the cache. Caching can be completely disabled by toggling [`CACHEOPS_ENABLED`](../../configuration/optional-settings/#cacheops_enabled) to `False` (it is `True` by default).

If a change is made to any of the objects returned by the cached query within that time, or if the timeout expires, the cached results are automatically invalidated and the next request for those results will be sent to the database.

!!! important
    Cacheops does not utilize the built-in [Django cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) to perform caching. Therefore it does not rely upon the [`CACHES`](../../configuration/required-settings/#caches) setting. Instead it monkey patches the underlying queryset methods to intercept calls to get and set cached items in Redis.

## How it Works

Caching is a complex topic and there are some important details to clarify with how caching is implemented and configureed in Nautobot.

### Caching in Django

Django comes included with its own [cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) that works for common cases, but it does not work well for the wide array of use-cases within Nautobot. For that reason, for the caching of web UI views, API results, and underlying database queries **Django's built-in cache framework caching is not used.**

Django's built-in caching is configured using the [`CACHES`](../../configuration/required-settings/#caches) setting. You'll observe that we have this as a required setting. Here's why:

Nautobot uses the [`django-redis`](https://github.com/jazzband/django-redis) Django plugin is used to provide the backend for Redis as a concurrent write lock for preventing race conditions when allocating IP address objects and to define centralized Redis connection settings that will be used by RQ. Previously, Nautobot was using PostgreSQL "advisory" locks, but because we are adding support for MySQL and other database backends in the future, we replaced the database-specific locking with a distributed Redis lock.

For this purpose, the [`CACHES`](../../configuration/required-settings/#caches) setting is required to to simplify the configuration for establishing concurrent write locks and for referencing the correct Redis connection information when defining RQ task queues using the  [`RQ_QUEUES`](../../configuration/required-settings/#rq_queues) setting.

Again: **`CACHES` is not used for caching at this time.**

!!! important
    Nautobot does not utilize the built-in [Django cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) to perform caching because Cacheops is being used instead as detailed just above. *Yes, we know this is confusing, which is why this is being called out explicitly!*

### Django Cacheops

Cacheops (aka [`django-cacheops`](https://github.com/Suor/django-cacheops)) is a Django plugin that does some very advanced caching, but *does not leverage the built-in cache framework*. Instead it uses a technique called ["monkey patching"](https://en.wikipedia.org/wiki/Monkey_patch). By monkey patching, a library can inject its own functionality into the core code behind the scenes.

This technique allows Cacheops to do more advanced caching operations that are not provided by the Django built-in cache framework without requiring Nautobot to also include some elaborate code of its own. This is accomplished by intercepting calls to the underlying queryset methods that get and set cached results in Redis.

For this purpose, Cacheops has its own `CACHEOPS_*` settings required to configure it that are not related to the `CACHES` setting.

For more information on the required settings needed to configure Cacheops, please see the [Caching section of the required settings documentation](../../configuration/required-settings/#caching).

The optional settings include:

- [`CACHEOPS_DEFAULTS`](../../configuration/optional-settings/#cacheops_defaults): To define the cache timeout value (Defaults to 15 minutes)
- [`CACHEOPS_ENABLED`](../../configuration/optional-settings/#cacheops_enabled) : To turn on/off caching (Defaults to `True`)

## Invalidating Cached Data

Although caching is performed automatically and rarely requires administrative intervention, Nautobot provides the `invalidate` management command to force invalidation of cached results. This command can reference a specific object my its type and UUID:

```no-highlight
$ nautobot-server invalidate dcim.Device.84ae706d-c189-4d13-a898-9737648e34b3
```

Alternatively, it can also delete all cached results for an object type:

```no-highlight
$ nautobot-server invalidate dcim.Device
```

Finally, calling it with the `all` argument will force invalidation of the entire cache database:

```no-highlight
$ nautobot-server invalidate all
```
