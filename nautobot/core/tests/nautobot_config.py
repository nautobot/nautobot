###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

from nautobot.core.settings import *  # noqa: F401,F403
from nautobot.core.settings_funcs import is_truthy

import os

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),
        "PORT": "",
        "CONN_MAX_AGE": 300,
        "ENGINE": "django.db.backends.postgresql",
    }
}

PLUGINS = [
    "nautobot.extras.tests.dummy_plugin",
]

SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# Here we are setting up a separate DB for the tests to use.
# This allows us to keep the rqworker running when working
# through the devcontainer or when using invoke.
RQ_QUEUES = {
    "default": {
        "HOST": os.getenv("NAUTOBOT_REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("NAUTOBOT_REDIS_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "webhooks": {
        "HOST": os.getenv("NAUTOBOT_REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("NAUTOBOT_REDIS_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "check_releases": {
        "HOST": os.getenv("NAUTOBOT_REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("NAUTOBOT_REDIS_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "custom_fields": {
        "HOST": os.getenv("NAUTOBOT_REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("NAUTOBOT_REDIS_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 900,
    },
}

redis_protocol = "rediss" if is_truthy(os.getenv("NAUTOBOT_REDIS_SSL", False)) else "redis"
cache_ops_pwd = os.getenv("NAUTOBOT_REDIS_PASSWORD")
cache_ops_host = os.getenv("NAUTOBOT_REDIS_HOST", "localhost")
cache_ops_user = os.getenv("NAUTOBOT_REDIS_USER")
cache_ops_port = int(os.getenv("NAUTOBOT_REDIS_PORT", 6379))

CACHEOPS_REDIS = os.getenv(
    "NAUTOBOT_CACHEOPS_REDIS", f"{redis_protocol}://:{cache_ops_pwd}@{cache_ops_host}:{cache_ops_port}/2"
)

# This is used for configuring Redis locks via django caching backend.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHEOPS_REDIS,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
