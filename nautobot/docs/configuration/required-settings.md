# Required Configuration Settings

## ALLOWED_HOSTS

This is a list of valid fully-qualified domain names (FQDNs) and/or IP addresses that can be used to reach the Nautobot service. Usually this is the same as the hostname for the Nautobot server, but can also be different; for example, when using a reverse proxy serving the Nautobot website under a different FQDN than the hostname of the Nautobot server. To help guard against [HTTP Host header attackes](https://docs.djangoproject.com/en/3.0/topics/security/#host-headers-virtual-hosting), Nautobot will not permit access to the server via any other hostnames (or IPs).

!!! note
    This parameter must always be defined as a list or tuple, even if only a single value is provided.

The value of this option is also used to set `CSRF_TRUSTED_ORIGINS`, which restricts POST requests to the same set of hosts (more about this [here](https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-CSRF_TRUSTED_ORIGINS)). Keep in mind that Nautobot, by default, sets `USE_X_FORWARDED_HOST` to true, which means that if you're using a reverse proxy, it's the FQDN used to reach that reverse proxy which needs to be in this list (more about this [here](https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts)).

Example:

```
ALLOWED_HOSTS = ['nautobot.example.com', '192.0.2.123']
```

If you are not yet sure what the domain name and/or IP address of the Nautobot installation will be, and are comfortable accepting the risks in doing so, you can set this to a wildcard (asterisk) to allow all host values:

```
ALLOWED_HOSTS = ['*']
```

---

## DATABASES

Nautobot requires access to a PostgreSQL 9.6 or later database service to store data. This service can run locally on the Nautobot server or on a remote system. The following parameters must be defined within the `DATABASES` dictionary:

* `NAME` - Database name
* `USER` - PostgreSQL username
* `PASSWORD` - PostgreSQL password
* `HOST` - Name or IP address of the database server (use `localhost` if running locally)
* `PORT` - TCP port of the PostgreSQL service; leave blank for default port (TCP/5432)
* `CONN_MAX_AGE` - Lifetime of a [persistent database connection](https://docs.djangoproject.com/en/stable/ref/databases/#persistent-connections), in seconds (300 is the default)

!!! warning
    Nautobot only supports PostgreSQL as a database backend. Do not modify the `ENGINE` setting or you
    will be unable to connect to the database.

Example:

```python
DATABASES = {
    'default': {
        'NAME': 'nautobot',                         # Database name
        'USER': 'nautobot',                         # PostgreSQL username
        'PASSWORD': 'awesome_password',             # PostgreSQL password
        'HOST': 'localhost',                        # Database server
        'PORT': '',                                 # Database port (leave blank for default)
        'CONN_MAX_AGE': 300,                        # Max database connection age
        'ENGINE': 'django.db.backends.postgresql',  # Database driver (Do not change this!)
    }
}
```

!!! note
    Nautobot supports all PostgreSQL database options supported by the underlying Django framework. For a complete list of available parameters, please see [the Django documentation](https://docs.djangoproject.com/en/stable/ref/settings/#databases).

---

## Redis Settings

[Redis](https://redis.io/) is an in-memory data store similar to memcached. It is required to support Nautobot's
caching, task queueing, and webhook features. The connection settings are explained here, allowing Nautobot to connect
to different Redis instances/databases per feature.

!!! warning
    It is highly recommended to keep the Redis databases for caching and tasks separate. Using the same database number on the
    same Redis instance for both may result in queued background tasks being lost during cache flushing events.

    For this reason, the default settings utilize database `1` for caching and database `0` for tasks.

The default settings should be suitable for most deployments and should only require customization for more advanced
configurations.

### Caching

Nautobot supports database query caching using [`django-cacheops`](https://github.com/Suor/django-cacheops).

Caching is configured by defining the [`CACHEOPS_REDIS`](#cacheops_redis) setting which in its simplest form is just a URL. 

For more details Nautobot's caching see the guide on [Caching](../../additional-features/caching).

#### CACHEOPS_REDIS

Default: `"redis://localhost:6379/1"`

If you wish to use SSL, you may set the URL scheme to `rediss://`, for example:

```python
CACHEOPS_REDIS = "rediss://localhost:6379/1"
```

This setting may also be a dictionary style, but that is not covered here. Please see the official guide on [Cacheops setup](https://github.com/Suor/django-cacheops#setup).

#### CACHEOPS_SENTINEL

Default: `undefined`

If you are using [Redis Sentinel](https://redis.io/topics/sentinel) for high-availability purposes, you must replace the
[`CACHEOPS_REDIS`](#cacheops_redis) setting with [`CACHEOPS_SENTINEL`](#cacheops_sentinel).

!!! warning
    [`CACHEOPS_REDIS`](#cacheops_redis) and [`CACHEOPS_SENTINEL`](#cacheops_sentinel) are mutually exclusive and will
    result in an error if both are set.

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

Task queues are configured by defining the `RQ_QUEUES` setting. Tasks settings utilize the `default` settings, where
webhooks utilize the `check_releases` settings. By default, these are identical. It is up to you to modify them for your
environment.

#### RQ_QUEUES

Default: 

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
    "check_releases": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "PASSWORD": "",
        "SSL": False,
        "DEFAULT_TIMEOUT": 300
    }
}
```

- `HOST` - Name or IP address of the Redis server (use `localhost` if running locally)
- `PORT` - TCP port of the Redis service; leave blank for default port (6379)
- `PASSWORD` - Redis password (if set)
* `DB` - Numeric database ID
- `SSL` - Use SSL connection to Redis

#### Using Redis Sentinel

If you are using [Redis Sentinel](https://redis.io/topics/sentinel) for high-availability purposes, you must modify the
connection settings. It requires the removal of the `HOST`, `PORT`, and `DEFAULT_TIMEOUT` keys from above and the
addition of three new keys.

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

For more details on configuring RQ, please see the documentation for [Django RQ
installation](https://github.com/rq/django-rq#installation).

---

## SECRET_KEY

This is a secret, random string used to assist in the creation new cryptographic hashes for passwords and HTTP cookies. The key defined here should not be shared outside of the configuration file. `SECRET_KEY` can be changed at any time, however be aware that doing so will invalidate all existing sessions.

Please note that this key is **not** used directly for hashing user passwords or for the encrypted storage of secret data in Nautobot.

`SECRET_KEY` should be at least 50 characters in length and contain a random mix of letters, digits, and symbols. 

A unique `SECRET_KEY` is generated for you automatically when you use `nautobot init` to create a new configuration. You may run `nautobot-server generate_secret_key` to generate a new key at any time.

```no-highlight
$ nautobot-server generate_secret_key.py
+$_kw69oq&fbkfk6&q-+ksbgzw1&061ghw%420u3(wen54w(m
```

!!! warning
    In the case of a highly available installation with multiple web servers, `SECRET_KEY` must be identical among all servers in order to maintain a persistent user session state.

For more details see [Nautobot Configuration](..).
