# Caching

A fundamental trade-off in dynamic websites like Nautobot is that, well, they’re dynamic. Each time a user requests a page, the Web server makes all sorts of calculations – from database queries to template rendering to business logic – to create the page that your site’s visitor sees. This is a lot more expensive, from a processing-overhead perspective, than your standard read-a-file-off-the-filesystem server arrangement.

That’s where caching comes in.

To cache something is to save the result of an expensive calculation so that you don’t have to perform the calculation next time.

Nautobot makes extensive use of caching; this is not a simple topic but it's a useful one for a Nautobot administrator to understand, so read on if you please.

## How it Works

Nautobot supports database query caching using [`django-cacheops`](https://github.com/Suor/django-cacheops) and Redis. When a query is made, the results are cached in Redis for a short period of time, as defined by the [`CACHEOPS_DEFAULTS`](../../configuration/optional-settings/#cacheops_defaults) parameter (15 minutes by default). Within that time, all recurrences of that specific query will return the pre-fetched results from the cache. Caching can be completely disabled by toggling [`CACHEOPS_ENABLED`](../../configuration/optional-settings/#cacheops_enabled) to `False` (it is `True` by default).

If a change is made to any of the objects returned by the cached query within that time, or if the timeout expires, the cached results are automatically invalidated and the next request for those results will be sent to the database.

Caching is a complex topic and there are some important details to clarify with how caching is implemented and configureed in Nautobot.

### Caching in Django

Django includes with its own [cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) that works for common cases, but does not work well for the wide array of use-cases within Nautobot. For that reason, **Django's built-in caching is not used for the caching of web UI views, API results, and underlying database queries.** Instead, we use [`django-cacheops`](https://github.com/Suor/django-cacheops). Please see below for more on this.

### `CACHES` and `django-redis`

The [`CACHES`](../../configuration/required-settings/#caches) setting is used to, among other things, configure Django's built-in caching. You'll observe that, even though we aren't using Django's built-in caching, *we still have this as a required setting*. Here's why:

Nautobot uses the [`django-redis`](https://github.com/jazzband/django-redis) Django plugin which allows it to use Redis as a backend for caching and session storage. This is used to provide a concurrent write lock for preventing race conditions when allocating IP address objects, and also to define centralized Redis connection settings that will be used by RQ. 

`django-redis` *also* uses the [`CACHES`](../../configuration/required-settings/#caches) setting, in its case to simplify the configuration for establishing concurrent write locks, and also for referencing the correct Redis connection information when defining RQ task queues using the  [`RQ_QUEUES`](../../configuration/required-settings/#rq_queues) setting.

Again: **`CACHES` is not used for Django's built-in caching at this time, but it is still a required setting for `django-redis` to function properly.**

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
