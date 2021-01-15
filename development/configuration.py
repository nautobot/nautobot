"""NetBox configuration file."""
import os
import sys

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(" ")

DATABASE = {
    "NAME": os.environ.get("DB_NAME", "netbox"),
    "USER": os.environ.get("DB_USER", ""),
    "PASSWORD": os.environ.get("DB_PASSWORD", ""),
    "HOST": os.environ.get("DB_HOST", "localhost"),
    "PORT": os.environ.get("DB_PORT", ""),
    "CONN_MAX_AGE": 300,
}

DEBUG = True
DEVELOPER = True

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
