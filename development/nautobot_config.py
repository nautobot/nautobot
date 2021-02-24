"""Nautobot configuration file."""
from distutils.util import strtobool
import os
import sys

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(" ")

DATABASES = {
    "default": {
        "NAME": os.environ.get("DB_NAME", "nautobot"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", ""),
        "CONN_MAX_AGE": 300,
        "ENGINE": "django.db.backends.postgresql",
    }
}

DEBUG = True

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s :\n  %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "verbose": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() :\n  %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "normal_console": {
            "level": "INFO",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "normal",
        },
        "verbose_console": {
            "level": "DEBUG",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["normal_console"], "level": "INFO"},
        "nautobot": {
            "handlers": ["verbose_console" if DEBUG else "normal_console"],
            "level": LOG_LEVEL,
        },
        "rq.worker": {
            "handlers": ["verbose_console" if DEBUG else "normal_console"],
            "level": LOG_LEVEL,
        },
    },
}


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


RQ_QUEUES = {
    "default": {
        "HOST": os.environ["REDIS_HOST"],
        "PORT": int(os.environ.get("REDIS_PORT", 6379)),
        "DB": 0,
        "PASSWORD": os.environ["REDIS_PASSWORD"],
        "SSL": is_truthy(os.environ.get("REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "check_releases": {
        "HOST": os.environ["REDIS_HOST"],
        "PORT": int(os.environ.get("REDIS_PORT", 6379)),
        "DB": 0,
        "PASSWORD": os.environ["REDIS_PASSWORD"],
        "SSL": is_truthy(os.environ.get("REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
}

# REDIS CACHEOPS
CACHEOPS_REDIS = f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/2"


SECRET_KEY = os.environ.get("SECRET_KEY", "")

# Django Debug Toolbar
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG and not TESTING}
HIDE_RESTRICTED_UI = os.environ.get("HIDE_RESTRICTED_UI", False)
