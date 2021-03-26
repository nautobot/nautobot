###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

from nautobot.core.settings import *  # noqa: F401,F403
from distutils.util import strtobool

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


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.
    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(str(arg)))


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
    "check_releases": {
        "HOST": os.getenv("NAUTOBOT_REDIS_HOST", "localhost"),
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 2,
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
}
