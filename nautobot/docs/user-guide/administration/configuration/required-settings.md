# Required Configuration Settings

[[% for property, attrs in settings_data.properties.items() if attrs.is_required_setting|default(false) %]]

---

## `[[ property ]]`

[[% if attrs.version_added|default(None) %]]
+++ [[ attrs.version_added ]]
[[% endif %]]
[[% with default = attrs.default|default(None) %]]
[[% if default is string %]]Default: `"[[ default ]]"`
[[% elif default is boolean %]]Default: `[[ default|title ]]`
[[% elif default is mapping and default != {} %]]Default:

```json
[[ default|tojson(4) ]]
```

[[% else %]]Default: `[[ default ]]`
[[% endif %]]
[[% endwith %]]

[[% if attrs.environment_variable|default(None) %]]
Environment variable: `[[ attrs.environment_variable ]]`
[[% elif attrs.type == "object" %]]
[[% for property_attrs in attrs.properties.values() if property_attrs.environment_variable|default(None) %]]
[[% if loop.first %]]Environment variables:[[% endif %]]
* `[[ property_attrs.environment_variable ]]`
[[% endfor %]]
[[% endif %]]

[[ attrs.description|default("") ]]

[[ attrs.details|default("") ]]

[[% endfor %]]

---

## DATABASES

Nautobot requires access to a supported database service to store data. This service can run locally on the Nautobot server or on a remote system. The following parameters must be defined within the `DATABASES` dictionary:

* `NAME` - Database name
* `USER` - Database username
* `PASSWORD` - Database password
* `HOST` - Name or IP address of the database server (use `localhost` if running locally)
* `PORT` - The port to use when connecting to the database. An empty string means the default port for your selected backend. (PostgreSQL: `5432`, MySQL: `3306`)
* `CONN_MAX_AGE` - Lifetime of a [persistent database connection](https://docs.djangoproject.com/en/stable/ref/databases/#persistent-connections), in seconds (300 is the default)
* `ENGINE` - The database backend to use. This can be either `django.db.backends.postgresql` or `django.db.backends.mysql`.  If `METRICS_ENABLED` is `True` this can also be either `django_prometheus.db.backends.postgresql` or `django_prometheus.db.backends.mysql`

The following environment variables may also be set for each of the above values:

* `NAUTOBOT_DB_NAME`
* `NAUTOBOT_DB_USER`
* `NAUTOBOT_DB_PASSWORD`
* `NAUTOBOT_DB_HOST`
* `NAUTOBOT_DB_PORT`
* `NAUTOBOT_DB_TIMEOUT`
* `NAUTOBOT_DB_ENGINE`

+++ 1.1.0
    The `NAUTOBOT_DB_ENGINE` setting was added along with support for MySQL.

---

## Redis Settings

[Redis](https://redis.io/) is an in-memory data store similar to memcached. It is required to support Nautobot's
caching, task queueing, and webhook features. The connection settings are explained here, allowing Nautobot to connect
to different Redis instances/databases per feature.

!!! warning
    It is highly recommended to keep the Redis databases for caching and tasks separate. Using the same database number on the same Redis instance for both may result in queued background tasks being lost during cache flushing events. For this reason, the default settings utilize database `1` for caching and database `0` for tasks.

!!! tip
    The default Redis settings in your `nautobot_config.py` should be suitable for most deployments and should only require customization for more advanced configurations.

### Caching

For more details on Nautobot's caching, including TLS and HA configuration, see the guide on [Caching](../../administration/guides/caching.md).

### Task Queuing

#### CACHES

Default:

```python
# Uncomment the following line to configure TLS/SSL
# import ssl

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Uncomment the following lines to configure TLS/SSL
            # "CONNECTION_POOL_KWARGS": {
            #     "ssl_cert_reqs": ssl.CERT_REQUIRED,
            #     "ssl_ca_certs": "/opt/nautobot/redis/ca.crt",
            #     "ssl_certfile": "/opt/nautobot/redis/tls.crt",
            #     "ssl_keyfile": "/opt/nautobot/redis/tls.key",
            # },
        },
    }
}
```

The following environment variables may also be set for some of the above values:

* `NAUTOBOT_CACHES_BACKEND`

+/- 2.0.0
    The default value of `CACHES["default"]["LOCATION"]` has changed from `redis://localhost:6379/0` to `redis://localhost:6379/1`, as Django's native caching is now taking the role previously occupied by `django-cacheops`.

### Task Queuing with Celery

+++ 1.1.0

Out of the box you do not need to make any changes to utilize task queueing with Celery. All of the default settings are sufficient for most installations.

In the event you do need to make customizations to how Celery interacts with the message broker such as for more advanced clustered deployments, the following setting may be changed.

#### Configuring Celery for High Availability

High availability clustering of Redis for use with Celery can be performed using Redis Sentinel. Please see documentation section on configuring [Celery for Redis Sentinel](../../administration/guides/caching.md#celery-sentinel-configuration) for more information.
