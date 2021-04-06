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
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "webhooks": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "PASSWORD": "",
        "SSL": False,
        "DEFAULT_TIMEOUT": 300,
    },
    "check_releases": {
        "HOST": os.getenv("NAUTOBOT_REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "custom_fields": {
        "HOST": os.getenv("REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("REDIS_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 900,
    },
}
