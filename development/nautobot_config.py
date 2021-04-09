"""Nautobot configuration file."""
import os
import sys

from nautobot.core.settings import *
from nautobot.core.settings_funcs import is_truthy

ALLOWED_HOSTS = os.environ.get("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")

DATABASES = {
    "default": {
        "NAME": os.environ.get("NAUTOBOT_DB_NAME", "nautobot"),
        "USER": os.environ.get("NAUTOBOT_DB_USER", ""),
        "PASSWORD": os.environ.get("NAUTOBOT_DB_PASSWORD", ""),
        "HOST": os.environ.get("NAUTOBOT_DB_HOST", "localhost"),
        "PORT": os.environ.get("NAUTOBOT_DB_PORT", ""),
        "CONN_MAX_AGE": 300,
        "ENGINE": "django.db.backends.postgresql",
    }
}

DEBUG = True

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not TESTING:
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


RQ_QUEUES = {
    "default": {
        "HOST": os.environ["NAUTOBOT_REDIS_HOST"],
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 0,
        "PASSWORD": os.environ["NAUTOBOT_REDIS_PASSWORD"],
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    # "webhooks": {
    #     "HOST": os.environ["NAUTOBOT_REDIS_HOST"],
    #     "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
    #     "DB": 0,
    #     "PASSWORD": os.environ["NAUTOBOT_REDIS_PASSWORD"],
    #     "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
    #     "DEFAULT_TIMEOUT": 300,
    # },
    "check_releases": {
        "HOST": os.environ["NAUTOBOT_REDIS_HOST"],
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 0,
        "PASSWORD": os.environ["NAUTOBOT_REDIS_PASSWORD"],
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 300,
    },
    "custom_fields": {
        "HOST": os.environ["NAUTOBOT_REDIS_HOST"],
        "PORT": int(os.environ.get("NAUTOBOT_REDIS_PORT", 6379)),
        "DB": 0,
        "PASSWORD": os.environ["NAUTOBOT_REDIS_PASSWORD"],
        "SSL": is_truthy(os.environ.get("NAUTOBOT_REDIS_SSL", False)),
        "DEFAULT_TIMEOUT": 900,
    },
}

# Base URL path if accessing Nautobot within a directory. For example, if installed at https://example.com/nautobot/, set:
# BASE_PATH = 'nautobot/'
BASE_PATH = os.environ.get("BASE_PATH", "")

# REDIS CACHEOPS
CACHEOPS_REDIS = f"redis://:{os.getenv('NAUTOBOT_REDIS_PASSWORD')}@{os.getenv('NAUTOBOT_REDIS_HOST')}:{os.getenv('NAUTOBOT_REDIS_PORT')}/2"

HIDE_RESTRICTED_UI = os.environ.get("HIDE_RESTRICTED_UI", False)

SECRET_KEY = os.environ.get("NAUTOBOT_SECRET_KEY", "")

# Django Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG and not TESTING}

if "debug_toolbar" not in INSTALLED_APPS:
    INSTALLED_APPS.append("debug_toolbar")
if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
