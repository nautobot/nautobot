# Required Configuration Settings

## ALLOWED_HOSTS

Environment Variable: `NAUTOBOT_ALLOWED_HOSTS` specified as a space-separated quoted string (e.g. `NAUTOBOT_ALLOWED_HOSTS="localhost 127.0.0.1 example.com"`).

This is a list of valid fully-qualified domain names (FQDNs) and/or IP addresses that can be used to reach the Nautobot service. Usually this is the same as the hostname for the Nautobot server, but can also be different; for example, when using a reverse proxy serving the Nautobot website under a different FQDN than the hostname of the Nautobot server. To help guard against [HTTP Host header attacks](https://docs.djangoproject.com/en/stable/topics/security/#host-headers-virtual-hosting), Nautobot will not permit access to the server via any other hostnames (or IPs).

Keep in mind that by default Nautobot sets [`USE_X_FORWARDED_HOST`](https://docs.djangoproject.com/en/stable/ref/settings/#use-x-forwarded-host) to `True`, which means that if you're using a reverse proxy, the FQDN used to reach that reverse proxy needs to be in this list.

!!! note
    This parameter must always be defined as a list or tuple, even if only a single value is provided.

Example:

```
ALLOWED_HOSTS = ['nautobot.example.com', '192.0.2.123']
```

!!! tip
    If there is more than one hostname in this list, you *may* also need to set [`CSRF_TRUSTED_ORIGINS`](optional-settings.md#csrf_trusted_origins) as well.

If you are not yet sure what the domain name and/or IP address of the Nautobot installation will be, and are comfortable accepting the risks in doing so, you can set this to a wildcard (asterisk) to allow all host values:

```
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
* `ENGINE` - The database backend to use. This can be either `django.db.backends.postgresql` or `django.db.backends.mysql`.

The following environment variables may also be set for each of the above values:

* `NAUTOBOT_DB_NAME`
* `NAUTOBOT_DB_USER`
* `NAUTOBOT_DB_PASSWORD`
* `NAUTOBOT_DB_HOST`
* `NAUTOBOT_DB_PORT`
* `NAUTOBOT_DB_TIMEOUT`
* `NAUTOBOT_DB_ENGINE`

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

!!! tip
    By default, MySQL is case-insensitive in its handling of text strings. This is different from PostgreSQL which is case-sensitive by default. We strongly recommend that you configure MySQL to be case-sensitive for use with Nautobot, either when you enable the MySQL server, or when you create the Nautobot database in MySQL. If you follow the provided installation instructions for CentOS or Ubuntu, the recommended steps there will include the appropriate database configuration.

When using MySQL as a database backend, and you want to enable support for Unicode characters like the beloved poop emoji, you'll need to update your settings.

If you try to use emojis without this setting, you will encounter a server error along the lines of `Incorrect string value`, because you are running afoul of the legacy implementation of Unicode (aka `utf8`) encoding in MySQL. The `utf8` encoding in MySQL is limited to 3-bytes per character. Newer Unicode emoji require 4-bytes. 

To properly support using such characters, you will need to create an entry in `DATABASES` -> `default` -> `OPTIONS` with the value `{"charset": "utf8mb4"}` in your `nautobot_config.py` and restart all Nautobot services. This will tell MySQL to always use `utf8mb4` character set for database client connections.

For example:

```python
DATABASES = {
    "default": {
        # Other setttings...
        "OPTIONS": {"charset": "utf8mb4"},  # Add this line
    }
}
```

!!! tip
    Starting in v1.1.0, if you have generated a new `nautobot_config.py` using `nautobot-server init`, this line is already there for you in your config. You'll just need to uncomment it! 

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

Nautobot supports database query caching using [`django-cacheops`](https://github.com/Suor/django-cacheops).

Caching is configured by defining the [`CACHEOPS_REDIS`](#cacheops_redis) setting which in its simplest form is just a URL.

For more details Nautobot's caching see the guide on [Caching](../../additional-features/caching).

!!! important
    Nautobot does not utilize the built-in [Django cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) to perform caching, as `django-cacheops` takes its place.

#### CACHEOPS_REDIS

Default: `"redis://localhost:6379/1"`

Environment Variable: `NAUTOBOT_CACHEOPS_REDIS`

If you wish to use SSL, you may set the URL scheme to `rediss://`, for example:

```python
CACHEOPS_REDIS = "rediss://localhost:6379/1"
```

This setting may also be a dictionary style, but that is not covered here. Please see the official guide on [Cacheops setup](https://github.com/Suor/django-cacheops#setup).

#### CACHEOPS_SENTINEL

Default: `undefined`

If you are using [Redis Sentinel](https://redis.io/topics/sentinel) for high-availability purposes, you must replace the [`CACHEOPS_REDIS`](#cacheops_redis) setting with [`CACHEOPS_SENTINEL`](#cacheops_sentinel).

!!! warning
    [`CACHEOPS_REDIS`](#cacheops_redis) and [`CACHEOPS_SENTINEL`](#cacheops_sentinel) are mutually exclusive and will result in an error if both are set.

Example:

```python
# Set CACHEOPS_REDIS to an empty value
CACHEOPS_REDIS = False

# If you want to use Sentinel, specify this variable
CACHEOPS_SENTINEL = {
    "locations": [("localhost", 26379)], # Sentinel locations, required
    "service_name": "nautobot",          # Sentinel service name, required
    "socket_timeout": 10,                # Connection timeout in seconds, optional
    "db": 0                              # Redis database, default: 0
    # ...                                # Everything else is passed to `Sentinel()`
}
```

For more details on how to configure Cacheops to use Redis Sentinel see the official guide on [Cacheops
setup](https://github.com/Suor/django-cacheops#setup).

---

### Task Queuing

Task queues are configured by defining them within the [`RQ_QUEUES`](#rq_queues) setting. 

Nautobot's core functionality relies on several distinct queues and these represent the minimum required set of queues that must be defined. By default, these use identical connection settings as defined in [`CACHES`](#caches) (yes, that's confusing and we'll explain below).

In most cases the default settings will be suitable for production use, but it is up to you to modify the task queues for your environment and know that other use cases such as utilizing specific plugins may require additional queues to be defined. 

#### CACHES

The [`django-redis`](https://github.com/jazzband/django-redis) Django plugin is used to enable Redis as a concurrent write lock for preventing race conditions when allocating IP address objects, and also to define centralized Redis connection settings that will be used by RQ. The `CACHES` setting is required to to simplify the configuration for defining queues. *It is not used for caching at this time.*

!!! important
    Nautobot does not utilize the built-in [Django cache framework](https://docs.djangoproject.com/en/stable/topics/cache/) (which also relies on the `CACHES` setting) to perform caching because Cacheops is being used instead as detailed just above. *Yes, we know this is confusing, which is why this is being called out explicitly!*

Default:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/0",
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
```

#### RQ_QUEUES

The default value for this setting defines the queues and instructs RQ to use the `default` Redis connection defined in [`CACHES`](#caches). This is intended to simplify default configuration for the common case.

Please see the [official `django-rq` documentation on support for django-redis connection settings](https://github.com/rq/django-rq#support-for-django-redis-and-django-redis-cache) for more information.

Default:

```python
RQ_QUEUES = {
    "default": {
        "USE_REDIS_CACHE": "default",
    },
    "check_releases": {
        "USE_REDIS_CACHE": "default",
    },
    "custom_fields": {
        "USE_REDIS_CACHE": "default",
    },
    "webhooks": {
        "USE_REDIS_CACHE": "default",
    },
}
```

More verbose dictionary-style configuration is still supported, but is not required unless you absolutely need more advanced task queuing configuration. An example configuration follows:

```python
RQ_QUEUES = {
    "default": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "PASSWORD": "",
        "SSL": False,
        "DEFAULT_TIMEOUT": 300
    },
    "webhooks": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "PASSWORD": "",
        "SSL": False,
        "DEFAULT_TIMEOUT": 300
    },
    "check_releases": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "PASSWORD": "",
        "SSL": False,
        "DEFAULT_TIMEOUT": 300
    },
    "custom_fields": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "PASSWORD": "",
        "SSL": False,
        "DEFAULT_TIMEOUT": 300
    }
}
```

* `HOST` - Name or IP address of the Redis server (use `localhost` if running locally)
* `PORT` - TCP port of the Redis service; leave blank for default port (6379)
* `PASSWORD` - Redis password (if set)
* `DB` - Numeric database ID
* `SSL` - Use SSL connection to Redis
* `DEFAULT_TIMEOUT` - The maximum execution time of a background task (such as running a [Job](../additional-features/jobs.md)), in seconds.

The following environment variables may also be set for some of the above values:

* `NAUTOBOT_REDIS_HOST`
* `NAUTOBOT_REDIS_PORT`
* `NAUTOBOT_REDIS_PASSWORD`
* `NAUTOBOT_REDIS_USERNAME`
* `NAUTOBOT_REDIS_SSL`
* `NAUTOBOT_REDIS_TIMEOUT`

!!! note
    If you overload any of the default values in [`CACHES`](#caches) or [`RQ_QUEUES`](#rq_queues) you may be unable to utilize the environment variables, depending on what you change.

For more details on configuring RQ, please see the documentation for [Django RQ installation](https://github.com/rq/django-rq#installation).

#### Using Redis Sentinel

If you are using [Redis Sentinel](https://redis.io/topics/sentinel) for high-availability purposes, you must be using dictionary-style settings, and modify the connection settings. This requires the removal of the `HOST`, `PORT`, and `DEFAULT_TIMEOUT` keys from the example above and the addition of three new keys.

* `SENTINELS`: List of tuples or tuple of tuples with each inner tuple containing the name or IP address
of the Redis server and port for each sentinel instance to connect to
* `MASTER_NAME`: Name of the master / service to connect to
* `SOCKET_TIMEOUT`: Timeout in seconds for a connection to timeout
* `CONNECTION_KWARGS`: Connection timeout, in seconds

Example:

```python
RQ_QUEUES = {
    "default": {
        "SENTINELS": [
            ("mysentinel.redis.example.com", 6379)
            ("othersentinel.redis.example.com", 6379)
        ],
        "MASTER_NAME": "nautobot",
        "DB": 0,
        "PASSWORD": "",
        "SOCKET_TIMEOUT": None,
        "CONNECTION_KWARGS": {
            "socket_connect_timeout": 10,
        },
        "SSL": False,
    },
    "check_releases": {
        "SENTINELS": [
            ("mysentinel.redis.example.com", 6379)
            ("othersentinel.redis.example.com", 6379)
        ],
        "MASTER_NAME": "nautobot",
        "DB": 0,
        "PASSWORD": "",
        "SOCKET_TIMEOUT": None,
        "CONNECTION_KWARGS": {
            "socket_connect_timeout": 10,
        },
        "SSL": False,
    }
}
```

!!! note
    It is permissible to use Sentinel for only one database and not the other.

For more details on configuring RQ with Redis Sentinel, please see the documentation for [Django RQ installation](https://github.com/rq/django-rq#installation).

---

## SECRET_KEY

Environment Variable: `NAUTOBOT_SECRET_KEY`

This is a secret, random string used to assist in the creation new cryptographic hashes for passwords and HTTP cookies. The key defined here should not be shared outside of the configuration file. `SECRET_KEY` can be changed at any time, however be aware that doing so will invalidate all existing sessions.

Please note that this key is **not** used directly for hashing user passwords or for the encrypted storage of secret data in Nautobot.

`SECRET_KEY` should be at least 50 characters in length and contain a random mix of letters, digits, and symbols.

!!! note
    A unique `SECRET_KEY` is generated for you automatically when you use `nautobot-server init` to create a new `nautobot_config.py`.

You may run `nautobot-server generate_secret_key` to generate a new key at any time.

```no-highlight
$ nautobot-server generate_secret_key
+$_kw69oq&fbkfk6&q-+ksbgzw1&061ghw%420u3(wen54w(m
```

!!! warning
    In the case of a highly available installation with multiple web servers, `SECRET_KEY` must be identical among all servers in order to maintain a persistent user session state.

For more details see [Nautobot Configuration](index.md).
