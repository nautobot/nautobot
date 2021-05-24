###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

import os

from nautobot.core.settings import *  # noqa: F401,F403
from nautobot.core.settings_funcs import is_truthy


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
    "dummy_plugin",
]

SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# Redis variables
REDIS_HOST = os.getenv("NAUTOBOT_REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("NAUTOBOT_REDIS_PORT", 6379)
REDIS_PASSWORD = os.getenv("NAUTOBOT_REDIS_PASSWORD", "")

# Check for Redis SSL
REDIS_SCHEME = "redis"
REDIS_SSL = is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False))
if REDIS_SSL:
    REDIS_SCHEME = "rediss"

# The django-redis cache is used to establish concurrent locks using Redis. The
# django-rq settings will use the same instance/database by default.
#
# This "default" server is now used by RQ_QUEUES.
# >> See: nautobot.core.settings.RQ_QUEUES
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_SCHEME}://{REDIS_HOST}:{REDIS_PORT}/2",
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": REDIS_PASSWORD,
        },
    }
}

# RQ_QUEUES is not set here because it just uses the default that gets imported
# up top via `from nautobot.core.settings import *`.

# REDIS CACHEOPS
CACHEOPS_REDIS = f"{REDIS_SCHEME}://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/3"
