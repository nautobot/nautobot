# Required Configuration Settings

## ALLOWED_HOSTS

Environment Variable: `NAUTOBOT_ALLOWED_HOSTS` specified as a space-separated quoted string (e.g. `NAUTOBOT_ALLOWED_HOSTS="localhost 127.0.0.1 example.com"`).

This is a list of valid fully-qualified domain names (FQDNs) and/or IP addresses that can be used to reach the Nautobot service. Usually this is the same as the hostname for the Nautobot server, but can also be different; for example, when using a reverse proxy serving the Nautobot website under a different FQDN than the hostname of the Nautobot server. To help guard against [HTTP Host header attacks](https://docs.djangoproject.com/en/stable/topics/security/#host-headers-virtual-hosting), Nautobot will not permit access to the server via any other hostnames (or IPs).

Keep in mind that by default Nautobot sets [`USE_X_FORWARDED_HOST`](https://docs.djangoproject.com/en/stable/ref/settings/#use-x-forwarded-host) to `True`, which means that if you're using a reverse proxy, the FQDN used to reach that reverse proxy needs to be in this list.

!!! note
    This parameter must always be defined as a list or tuple, even if only a single value is provided.

Example:

```python
ALLOWED_HOSTS = ['nautobot.example.com', '192.0.2.123']
```

!!! tip
    If there is more than one hostname in this list, you *may* also need to set [`CSRF_TRUSTED_ORIGINS`](optional-settings.md#csrf_trusted_origins) as well.

If you are not yet sure what the domain name and/or IP address of the Nautobot installation will be, and are comfortable accepting the risks in doing so, you can set this to a wildcard (asterisk) to allow all host values:

```python
ALLOWED_HOSTS = ['*']
```

!!! warning
    It is not recommended to leave this value as `['*']` for production deployments. Please see the [official Django documentation on `ALLOWED_HOSTS`](https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts) for help.

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

!!! warning
    Nautobot supports either MySQL or PostgreSQL as a database backend. You must make sure that the `ENGINE` setting matches your selected database backend or **you will be unable to connect to the database**.

Example:

```python
DATABASES = {
    'default': {
        'NAME': 'nautobot',                         # Database name
        'USER': 'nautobot',                         # Database username
        'PASSWORD': 'awesome_password',             # Database password
        'HOST': 'localhost',                        # Database server
        'PORT': '',                                 # Database port (leave blank for default)
        'CONN_MAX_AGE': 300,                        # Max database connection age
        'ENGINE': 'django.db.backends.postgresql',  # Database driver ("mysql" or "postgresql")
    }
}
```

!!! note
    Nautobot supports all database options supported by the underlying Django framework. For a complete list of available parameters, please see [the official Django documentation on `DATABASES`](https://docs.djangoproject.com/en/stable/ref/settings/#databases).

### MySQL Unicode Settings

+++ 1.1.0

!!! tip
    By default, MySQL is case-insensitive in its handling of text strings. This is different from PostgreSQL which is case-sensitive by default. We strongly recommend that you configure MySQL to be case-sensitive for use with Nautobot, either when you enable the MySQL server, or when you create the Nautobot database in MySQL. If you follow the provided installation instructions for CentOS or Ubuntu, the recommended steps there will include the appropriate database configuration.

When using MySQL as a database backend, and you want to enable support for Unicode characters like the beloved poop emoji, you'll need to update your settings.

If you try to use emojis without this setting, you will encounter a server error along the lines of `Incorrect string value`, because you are running afoul of the legacy implementation of Unicode (aka `utf8`) encoding in MySQL. The `utf8` encoding in MySQL is limited to 3-bytes per character. Newer Unicode emoji require 4-bytes.

To properly support using such characters, you will need to create an entry in `DATABASES` -> `default` -> `OPTIONS` with the value `{"charset": "utf8mb4"}` in your `nautobot_config.py` and restart all Nautobot services. This will tell MySQL to always use `utf8mb4` character set for database client connections.

For example:

```python
DATABASES = {
    "default": {
        # Other settings...
        "OPTIONS": {"charset": "utf8mb4"},  # Add this line
    }
}
```

+++ 1.1.0
    If you have generated a new `nautobot_config.py` using `nautobot-server init`, this line is already there for you in your config. You'll just need to uncomment it!

+/- 1.1.5
    If you have generated a new `nautobot_config.py` using `nautobot-server init`, this line is already present in your config and no action is required.

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

The [`django-redis`](https://github.com/jazzband/django-redis) Django plugin is used to enable Redis as a concurrent write lock for preventing race conditions when allocating IP address objects. The `CACHES` setting is required to simplify the configuration for `django-redis`.

!!! important
    Nautobot also utilizes the built-in [Django cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) (which also relies on the `CACHES` setting) to perform caching.

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

#### CELERY_BROKER_URL

This setting tells Celery and its workers how and where to communicate with the message broker. The default value for this points to `redis://localhost:6379/0`. Please see the [optional settings documentation for `CELERY_BROKER_URL`](optional-settings.md#celery_broker_url) for more information on customizing this setting.

#### Configuring Celery with TLS

Optionally, you can configure Celery to use custom SSL certificates to connect to redis by setting the following variables:

```python
import ssl

CELERY_REDIS_BACKEND_USE_SSL = {
    "ssl_cert_reqs": ssl.CERT_REQUIRED,
    "ssl_ca_certs": "/opt/nautobot/redis/ca.crt",
    "ssl_certfile": "/opt/nautobot/redis/tls.crt",
    "ssl_keyfile": "/opt/nautobot/redis/tls.key",
}
CELERY_BROKER_USE_SSL = CELERY_REDIS_BACKEND_USE_SSL
```

Please see the celery [documentation](https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-broker_use_ssl) for additional details.

#### Configuring Celery for High Availability

High availability clustering of Redis for use with Celery can be performed using Redis Sentinel. Please see documentation section on configuring [Celery for Redis Sentinel](../../administration/guides/caching.md#celery-sentinel-configuration) for more information.

---

## SECRET_KEY

Environment Variable: `NAUTOBOT_SECRET_KEY`

This is a secret, random string used to assist in the creation new cryptographic hashes for passwords and HTTP cookies. The key defined here should not be shared outside of the configuration file. `SECRET_KEY` can be changed at any time, however be aware that doing so will invalidate all existing sessions.

`SECRET_KEY` should be at least 50 characters in length and contain a random mix of letters, digits, and symbols.

!!! note
    A unique `SECRET_KEY` is generated for you automatically when you use `nautobot-server init` to create a new `nautobot_config.py`.

You may run `nautobot-server generate_secret_key` to generate a new key at any time.

```no-highlight
nautobot-server generate_secret_key
```

Sample output:

```no-highlight
+$_kw69oq&fbkfk6&q-+ksbgzw1&061ghw%420u3(wen54w(m
```

Alternatively use the following command to generate a secret even before `nautobot-server` is runnable:

```no-highlight
LC_ALL=C tr -cd '[:lower:][:digit:]!@#$%^&*(\-_=+)' < /dev/urandom | fold -w50 | head -n1
```

Example output:

```no-highlight
9.V$@Kxkc@@Kd@z<a/=.J-Y;rYc79<y@](9o9(L(*sS)Q+ud5P
```

!!! warning
    In the case of a highly available installation with multiple web servers, `SECRET_KEY` must be identical among all servers in order to maintain a persistent user session state.

For more details see [Nautobot Configuration](index.md).
