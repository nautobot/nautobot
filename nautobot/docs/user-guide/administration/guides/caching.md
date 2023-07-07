# Caching

A fundamental trade-off in dynamic websites like Nautobot is that, well, they’re dynamic. Each time a user requests a page, the Web server makes all sorts of calculations – from database queries to template rendering to business logic – to create the page that your site’s visitor sees. This is a lot more expensive, from a processing-overhead perspective, than your standard read-a-file-off-the-filesystem server arrangement.

That’s where caching comes in.

To cache something is to save the result of an expensive calculation so that you don’t have to perform the calculation next time.

Nautobot makes extensive use of caching; this is not a simple topic but it's a useful one for a Nautobot administrator to understand, so read on if you please.

## How it Works

--- 2.0.0
    `django-cacheops` has been removed as a Nautobot dependency and is no longer used.

Caching is a complex topic and there are some important details to clarify with how caching is implemented and configured in Nautobot.

### Caching in Django

Django includes its own [cache framework](https://docs.djangoproject.com/en/stable/topics/cache/). Nautobot uses this cache framework in a limited number of cases.

### `CACHES` and `django-redis`

The [`CACHES`](../configuration/required-settings.md#caches) setting is used to, among other things, configure Django's built-in caching. *This is a required setting*. Here's why:

Nautobot uses the [`django-redis`](https://github.com/jazzband/django-redis) Django plugin which allows it to use Redis as a backend for caching and session storage. This is used to provide a concurrent write lock for preventing race conditions when allocating IP address objects.

`django-redis` *also* uses the [`CACHES`](../configuration/required-settings.md#caches) setting, in its case to simplify the configuration for establishing concurrent write locks.

## High Availability Caching

[Redis](https://redis.io/) provides two different methods to achieve high availability: The first is [Redis Sentinel](https://redis.io/topics/sentinel) and the second is the newer [Redis Clustering](https://redis.io/topics/cluster-tutorial) feature. Currently, Nautobot only supports Redis Sentinel for high availability.

### Using Redis Sentinel

The installation/configuration of the [Redis Sentinel](https://redis.io/topics/sentinel) cluster itself is outside the scope of this document, this section is intended to provide the steps necessary to configure Nautobot to connect to a Sentinel cluster.

We need to configure `django-redis` and `celery` to use Sentinel. Each library is configured differently, so please pay close attention to the details.

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

For more details on configuring django-redis with Redis Sentinel, please see the documentation for [Django Redis](https://github.com/jazzband/django-redis#use-the-sentinel-connection-factory).

#### `celery` Sentinel Configuration

+/- 2.0.0
    Celery now stores results in the Nautobot database. The `CELERY_RESULT_BACKEND` and `CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS` should not be changed from their default values.

!!! note
    Celery is not directly related to caching but it does utilize Redis, therefore in more advanced deployments if Redis Sentinel is required for caching, Celery must also be configured to use Redis Sentinel to high availability.

Celery Sentinel configuration is controlled by two settings within your `nautobot_config.py`:

* [`CELERY_BROKER_URL`](../configuration/optional-settings.md#celery_broker_url)
* [`CELERY_BROKER_TRANSPORT_OPTIONS`](../configuration/optional-settings.md#celery_broker_transport_options)

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
```

Please see the official Celery documentation for more information on how to [configure Celery to use Redis Sentinel](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html?highlight=sentinel#configuration).

Please also see the [Nautobot documentation on required settings for Celery](../configuration/required-settings.md#task-queuing-with-celery) for additional information.
