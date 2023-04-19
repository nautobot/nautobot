"""Nautobot development configuration file."""
from nautobot.core.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "NAME": "nautobot",
        "USER": "nautobot",
        "PASSWORD": "changeme",
        "HOST": "localhost",
        "PORT": "5432",
        "ENGINE": "django.db.backends.postgresql",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    },
}
SECRET_KEY = "012345678901234567890123456789012345678901234567890123456789"
ALLOWED_HOSTS = ["*"]
