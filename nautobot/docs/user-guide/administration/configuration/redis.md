# Redis for Caching and Celery

[Redis](https://redis.io/) is an in-memory data store similar to memcached. It is required to support Nautobot's
caching, task queueing, and webhook features. The connection settings are explained here, allowing Nautobot to connect
to different Redis instances/databases per feature.

!!! warning
    It is highly recommended to keep the Redis databases for caching and tasks separate. Using the same database number on the same Redis instance for both may result in queued background tasks being lost during cache flushing events. For this reason, the default settings utilize database `1` for caching and database `0` for tasks.

!!! tip
    The default Redis settings in your `nautobot_config.py` should be suitable for most deployments and should only require customization for more advanced configurations. See below for examples.

## Caching

Out of the box you do not need to make any changes to utilize caching with Redis. The default settings are sufficient for most installations.

Django includes its own [cache framework](https://docs.djangoproject.com/en/stable/topics/cache/). Nautobot uses this cache framework, and specifically the extension [`django-redis`](https://github.com/jazzband/django-redis), which allows it to use Redis as a backend for caching and session storage. This extension is also used to provide a concurrent write lock for preventing race conditions when allocating IP address objects.

The [`CACHES`](../configuration/settings.md#caches) setting is used to, among other things, configure Django's built-in caching and the `django-redis` extension to appropriately use Redis.

In the event you need to use a customized `django-redis` client, the following settings (under `CACHES["default"]["OPTIONS"]`) can be changed:

* [`CLIENT_CLASS`](https://github.com/jazzband/django-redis?tab=readme-ov-file#pluggable-clients)
* [`CUSTOM_HEALTH_CHECK_CLASS`](../guides/health-checks.md#redis)

### Redis User Permissions

+++ 3.0.10

[`nautobot-server post_upgrade`](../tools/nautobot-server.md#post_upgrade) clears the cache, which `django-redis` does by running the Redis [`FLUSHDB`](https://redis.io/docs/latest/commands/flushdb/) command against the caching database. This deletes every key in that database, which is another reason to keep the caching and task databases separate as described above.

If you restrict the Redis user that Nautobot connects as with an [ACL](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/), make sure that it is allowed to run `FLUSHDB`. `FLUSHDB` is in the `@dangerous` command category, so an ACL that includes `-@dangerous` needs to add `+flushdb` back, for example:

```no-highlight
user nautobot on >password ~* &* +@all -@dangerous +flushdb
```

Otherwise `post_upgrade` fails with `redis.exceptions.NoPermissionError: this user has no permissions to run the 'flushdb' command or its subcommand`.

Alternatively, you can skip clearing the cache with `nautobot-server post_upgrade --no-clear-cache`, but data cached by the previous version of Nautobot may then cause errors after the upgrade.

## Task Queuing with Celery

Out of the box you do not need to make any changes to utilize task queueing with Celery and Redis. The default settings are sufficient for most installations.

In the event you do need to make customizations to how Celery interacts with the message broker such as for more advanced clustered deployments, the following settings may be changed:

* [`CELERY_BROKER_URL`](../configuration/settings.md#celery_broker_url)
    * Rather than directly configuring this setting, you may prefer to control it and the `CACHES["default"]["LOCATION"]` setting through the various `NAUTOBOT_REDIS_*` environment variables in order to reduce duplication of information.
* [`CELERY_BROKER_USE_SSL`](../configuration/settings.md#celery_broker_use_ssl)
* [`CELERY_REDIS_BACKEND_USE_SSL`](../configuration/settings.md#celery_redis_backend_use_ssl)

## High Availability Using Redis Sentinel

Redis provides two different methods to achieve high availability: The first is [Redis Sentinel](https://redis.io/topics/sentinel) and the second is the newer [Redis Clustering](https://redis.io/topics/cluster-tutorial) feature. Currently, Nautobot only supports Redis Sentinel for high availability.

The installation/configuration of the [Redis Sentinel](https://redis.io/topics/sentinel) cluster itself is outside the scope of this document, this section is intended to provide the steps necessary to configure Nautobot to connect to a Sentinel cluster.

We need to configure `django-redis` and `celery` to use Sentinel. Each library is configured differently, so please pay close attention to the details.

### `django-redis` Sentinel Configuration

Notable settings:

* `SENTINELS`: List of tuples or tuple of tuples with each inner tuple containing the name or IP address
of the Redis server and port for each sentinel instance to connect to
* `LOCATION`: Similar to a redis URL, _however_, the hostname in the URL is the master/service name in redis sentinel
* `SENTINEL_KWARGS`: Options which will be passed directly to [Redis Sentinel](https://github.com/redis/redis-py#sentinel-support)
* `PASSWORD`: The redis password (if set), the `SENTINEL_KWARGS["password"]` setting is the password for Sentinel
* `TIMEOUT`: (Optional) Cache timeout in seconds. Defaults to 300 seconds if not specified.

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
                ("thirdsentinel.redis.example.com", 26379),
            ],
        },
    },
}
```

For more details on configuring `django-redis` with Redis Sentinel, please see the documentation for [Django Redis](https://github.com/jazzband/django-redis#use-the-sentinel-connection-factory).

### `celery` Sentinel Configuration

+/- 2.0.0 "Do not change `CELERY_RESULT_BACKEND` or `CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS`"
    Celery now stores results in the Nautobot database. The `CELERY_RESULT_BACKEND` and `CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS` should not be changed from their default values.

Celery Sentinel configuration is controlled by two settings within your `nautobot_config.py`:

* [`CELERY_BROKER_URL`](../configuration/settings.md#celery_broker_url)
* [`CELERY_BROKER_TRANSPORT_OPTIONS`](../configuration/settings.md#celery_broker_transport_options)

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
