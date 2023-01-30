# Caching

A fundamental trade-off in dynamic websites like Nautobot is that, well, they’re dynamic. Each time a user requests a page, the Web server makes all sorts of calculations – from database queries to template rendering to business logic – to create the page that your site’s visitor sees. This is a lot more expensive, from a processing-overhead perspective, than your standard read-a-file-off-the-filesystem server arrangement.

That’s where caching comes in.

To cache something is to save the result of an expensive calculation so that you don’t have to perform the calculation next time.

Nautobot makes extensive use of caching; this is not a simple topic but it's a useful one for a Nautobot administrator to understand, so read on if you please.

## How it Works

Nautobot optionally supports database query caching using [`django-cacheops`](https://github.com/Suor/django-cacheops) and Redis. Caching can be enabled by toggling [`CACHEOPS_ENABLED`](../configuration/optional-settings.md#cacheops_enabled) to `True` (it is `False` by default). When caching is enabled, and a query is made, the results are cached in Redis for a short period of time, as defined by the [`CACHEOPS_DEFAULTS`](../configuration/optional-settings.md#cacheops_defaults) parameter (15 minutes by default). Within that time, all recurrences of that specific query will return the pre-fetched results from the cache.

!!! caution "Changed in version 1.5.0"
    Query caching is now disabled by default, and will be removed as a supported option in a future release.

If a change is made to any of the objects returned by the cached query within that time, or if the timeout expires, the cached results are automatically invalidated and the next request for those results will be sent to the database.

Caching is a complex topic and there are some important details to clarify with how caching is implemented and configured in Nautobot.

### Caching in Django

Django includes with its own [cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) that works for common cases, but does not work well for the wide array of use-cases within Nautobot. For that reason, **Django's built-in caching is not used for the caching of web UI views, API results, and underlying database queries.** Instead, we use [`django-cacheops`](https://github.com/Suor/django-cacheops). Please see below for more on this.

### `CACHES` and `django-redis`

The [`CACHES`](../configuration/required-settings.md#caches) setting is used to, among other things, configure Django's built-in caching. You'll observe that, even though we aren't using Django's built-in caching, *we still have this as a required setting*. Here's why:

Nautobot uses the [`django-redis`](https://github.com/jazzband/django-redis) Django plugin which allows it to use Redis as a backend for caching and session storage. This is used to provide a concurrent write lock for preventing race conditions when allocating IP address objects, and also to define centralized Redis connection settings that will be used by RQ.

`django-redis` *also* uses the [`CACHES`](../configuration/required-settings.md#caches) setting, in its case to simplify the configuration for establishing concurrent write locks, and also for referencing the correct Redis connection information when defining RQ task queues using the  [`RQ_QUEUES`](../configuration/required-settings.md#rq_queues) setting.

Again: **`CACHES` is not used for Django's built-in caching at this time, but it is still a required setting for `django-redis` to function properly.**

### Django Cacheops

Cacheops (aka [`django-cacheops`](https://github.com/Suor/django-cacheops)) is a Django plugin that does some very advanced caching, but *does not leverage the built-in cache framework*. Instead it uses a technique called ["monkey patching"](https://en.wikipedia.org/wiki/Monkey_patch). By monkey patching, a library can inject its own functionality into the core code behind the scenes.

This technique allows Cacheops to do more advanced caching operations that are not provided by the Django built-in cache framework without requiring Nautobot to also include some elaborate code of its own. This is accomplished by intercepting calls to the underlying queryset methods that get and set cached results in Redis.

For this purpose, Cacheops has its own `CACHEOPS_*` settings required to configure it that are not related to the `CACHES` setting.

For more information on the required settings needed to configure Cacheops, please see the [Caching section of the required settings documentation](../configuration/required-settings.md#caching).

The optional settings include:

* [`CACHEOPS_DEFAULTS`](../configuration/optional-settings.md#cacheops_defaults): To define the cache timeout value (Defaults to 15 minutes)
* [`CACHEOPS_ENABLED`](../configuration/optional-settings.md#cacheops_enabled) : To turn on/off caching (Defaults to `False`)

## Invalidating Cached Data

Although caching is performed automatically and rarely requires administrative intervention, Nautobot provides the `invalidate` management command to force invalidation of cached results. This command can reference a specific object my its type and UUID:

> Run these commands as the Nautobot user

```no-highlight
nautobot-server invalidate dcim.Device.84ae706d-c189-4d13-a898-9737648e34b3
```

Alternatively, it can also delete all cached results for an object type:

```no-highlight
nautobot-server invalidate dcim.Device
```

Finally, calling it with the `all` argument will force invalidation of the entire cache database:

```no-highlight
nautobot-server invalidate all
```

## High Availability Caching

[Redis](https://redis.io/) provides two different methods to achieve high availability: The first is [Redis Sentinel](https://redis.io/topics/sentinel) and the second is the newer [Redis Clustering](https://redis.io/topics/cluster-tutorial) feature. Unfortunately, due to an [known issue with django-cacheops](https://github.com/Suor/django-cacheops/issues/35) (last updated November 2021) Nautobot is unable to support Redis Clustering at this time. Therefore, Nautobot only supports Redis Sentinel for high availability.

### Using Redis Sentinel

The installation/configuration of the [Redis Sentinel](https://redis.io/topics/sentinel) cluster itself is outside the scope of this document, this section is intended to provide the steps necessary to configure Nautobot to connect to a Sentinel cluster.

We need to configure `django-redis`, `django-cacheops`, and `celery` to use Sentinel. Each library is configured differently, so please pay close attention to the details.

#### `django-redis` Sentinel Configuration

Notable settings:

* `SENTINELS`: List of tuples or tuple of tuples with each inner tuple containing the name or IP address
of the Redis server and port for each sentinel instance to connect to
* `LOCATION`: Similar to a redis URL, *however*, the hostname in the URL is the master/service name in redis sentinel
* `SENTINEL_KWARGS`: Options which will be passed directly to [Redis Sentinel](https://github.com/redis/redis-py#sentinel-support)
* `PASSWORD`: The redis password (if set), the `SENTINEL_KWARGS["password"]` setting is the password for Sentinel

Example:

```python
DJANGO_REDIS_CONNECTION_FACTORY = "django_redis.pool.SentinelConnectionFactory"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://nautobot/0",  # in this context 'nautobot' is the redis master/service name
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.SentinelClient",
            "CONNECTION_POOL_CLASS": "redis.sentinel.SentinelConnectionPool",
            "PASSWORD": "",
            "SENTINEL_KWARGS": {
                "password": "",  # likely the same password from above
            },
            "SENTINELS": [
                ("mysentinel.redis.example.com", 26379),
                ("othersentinel.redis.example.com", 26379),
                ("thirdsentinel.redis.example.com", 26379)
            ],
        },
    },
}
```

!!! note
    It is permissible to use Sentinel for only one database and not the other, see [`RQ_QUEUES`](../configuration/required-settings.md#rq_queues) for details.

For more details on configuring django-redis with Redis Sentinel, please see the documentation for [Django Redis](https://github.com/jazzband/django-redis#use-the-sentinel-connection-factory).

#### `django-cacheops` Sentinel Configuration

Notable settings:

* `locations`: List of tuples or tuple of tuples with each inner tuple containing the name or IP address
of the Redis server and port for each sentinel instance to connect to
* `service_name`: the master/service name in redis sentinel
* Additional parameters may be specified in the `CACHEOPS_SENTINEL` dictionary which are passed directly to Sentinel

!!! note
    `locations` for `django-cacheops` has a different meaning than the `LOCATION` value for `django-redis`

!!! warning
    [`CACHEOPS_REDIS`](../configuration/required-settings.md#cacheops_redis) and [`CACHEOPS_SENTINEL`](../configuration/required-settings.md#cacheops_sentinel) are mutually exclusive and will result in an error if both are set.

Example:

```python
CACHEOPS_REDIS = False
CACHEOPS_SENTINEL = {
    "db": 1,
    "locations": [
        ("mysentinel.redis.example.com", 26379),
        ("othersentinel.redis.example.com", 26379),
        ("thirdsentinel.redis.example.com", 26379)
    ],
    "service_name": "nautobot",
    "socket_timeout": 10,
    "sentinel_kwargs": {
        "password": ""
    },
    "password": "",
    # Everything else is passed to `Sentinel()`
}
```

For more details on how to configure Cacheops to use Redis Sentinel see the documentation for [Cacheops setup](https://github.com/Suor/django-cacheops#setup).

#### `celery` Sentinel Configuration

!!! note
    Celery is not directly related caching but it does utilize Redis, therefore in more advanced deployments if Redis Sentinel is required for caching, Celery must also be configured to use Redis Sentinel to high availability.

Celery Sentinel configuration is controlled by four settings within your `nautobot_config.py`:

* [`CELERY_BROKER_URL`](../configuration/optional-settings.md#celery_broker_url)
* [`CELERY_BROKER_TRANSPORT_OPTIONS`](../configuration/optional-settings.md#celery_broker_transport_options)
* [`CELERY_RESULT_BACKEND`](../configuration/optional-settings.md#celery_result_backend)
* [`CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS`](../configuration/optional-settings.md#celery_result_backend_transport_options)

By default Nautobot configures the celery broker and results backend with the same settings, so this pattern is mirrored here.

```python
redis_password = ""
sentinel_password = ""

CELERY_BROKER_URL = (
    f"sentinel://:{redis_password}@mysentinel.redis.example.com:26379;"
    f"sentinel://:{redis_password}@othersentinel.redis.example.com:26379;"
    # The final entry must not have the `;` delimiter
    f"sentinel://:{redis_password}@thirdsentinel.redis.example.com:26379"
)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "master_name": "nautobot",
    "sentinel_kwargs": {"password": sentinel_password},
}

CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = CELERY_BROKER_TRANSPORT_OPTIONS
```

Please see the official Celery documentation for more information on how to [configure Celery to use Redis Sentinel](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html?highlight=sentinel#configuration).

Please also see the [Nautobot documentation on required settings for Celery](../configuration/required-settings.md#task-queuing-with-celery) for additional information.
