###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

from nautobot.core.settings import *  # noqa: F401,F403

import os

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DATABASE", "nautobot"),
        "USER": os.getenv("NAUTOBOT_USER", ""),
        "PASSWORD": os.getenv("NAUTOBOT_PASSWORD", ""),
        "HOST": "localhost",
        "PORT": "",
        "CONN_MAX_AGE": 300,
        "ENGINE": "django.db.backends.postgresql",
    }
}

PLUGINS = [
    "nautobot.extras.tests.dummy_plugin",
]

REDIS = {
    "tasks": {
        "HOST": "localhost",
        "PORT": 6379,
        "PASSWORD": "",
        "DATABASE": 0,
        "SSL": False,
    },
    "caching": {
        "HOST": "localhost",
        "PORT": 6379,
        "PASSWORD": "",
        "DATABASE": 1,
        "SSL": False,
    },
}

SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
