"""NetBox configuration file."""
import os

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
