"""Nautobot configuration file."""
import os
import sys

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(" ")

DATABASES = {
    'default': {
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
        "normal_console": {"level": "INFO", "class": "rq.utils.ColorizingStreamHandler", "formatter": "normal"},
        "verbose_console": {"level": "DEBUG", "class": "rq.utils.ColorizingStreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {"handlers": ["normal_console"], "level": "INFO"},
        "nautobot": {"handlers": ["verbose_console" if DEBUG else "normal_console"], "level": LOG_LEVEL},
        "rq.worker": {"handlers": ["verbose_console" if DEBUG else "normal_console"], "level": LOG_LEVEL},
    },
}

REDIS = {
    "caching": {
        "HOST": os.environ.get("REDIS_HOST", "redis"),
        "PORT": int(os.environ.get("REDIS_PORT", 6379)),
        "PASSWORD": os.environ.get("REDIS_PASSWORD", ""),
        "DATABASE": 1,
        "SSL": bool(os.environ.get("REDIS_SSL", False)),
    },
    "tasks": {
        "HOST": os.environ.get("REDIS_HOST", "redis"),
        "PORT": int(os.environ.get("REDIS_PORT", 6379)),
        "PASSWORD": os.environ.get("REDIS_PASSWORD", ""),
        "DATABASE": 0,
        "SSL": bool(os.environ.get("REDIS_SSL", False)),
    },
}

SECRET_KEY = os.environ.get("SECRET_KEY", "")

# Django Debug Toolbar
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG and not TESTING}
HIDE_RESTRICTED_UI = os.environ.get("HIDE_RESTRICTED_UI", False)
