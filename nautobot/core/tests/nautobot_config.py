###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

from nautobot.core.settings import *  # noqa: F401,F403
from distutils.util import strtobool

import environ

import os

env = environ.Env(
    NAUTOBOT_DB_URL=(str, "postgres://:@localhost/nautobot"),
    NAUTOBOT_REDIS_HOST=(str, "localhost"),
    NAUTOBOT_REDIS_PASSWORD=(str, ""),
    NAUTOBOT_REDIS_PORT=(int, 6379),
    NAUTOBOT_REDIS_SSL=(bool, False),
    NAUTOBOT_REDIS_TIMEOUT=(int, 300),
    NAUTOBOT_REDIS_USER=(str, ""),
)
environ.Env.read_env()

ALLOWED_HOSTS = ["*"]

DATABASES = {"default": env.db("NAUTOBOT_DB_URL")}

PLUGINS = [
    "nautobot.extras.tests.dummy_plugin",
]

SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Here we are setting up a separate DB for the tests to use.
# This allows us to keep the rqworker running when working
# through the devcontainer or when using invoke.
RQ_QUEUES = {
    "default": {
        "HOST": env("NAUTOBOT_REDIS_HOST"),
        "PORT": env("NAUTOBOT_REDIS_PORT"),
        "DB": 2,
        "PASSWORD": env("NAUTOBOT_REDIS_PASSWORD"),
        "SSL": env("NAUTOBOT_REDIS_SSL"),
        "DEFAULT_TIMEOUT": env("NAUTOBOT_REDIS_TIMEOUT"),
    },
    "check_releases": {
        "HOST": env("NAUTOBOT_REDIS_HOST"),
        "PORT": env("NAUTOBOT_REDIS_PORT"),
        "DB": 2,
        "PASSWORD": env("NAUTOBOT_REDIS_PASSWORD"),
        "SSL": env("NAUTOBOT_REDIS_SSL"),
        "DEFAULT_TIMEOUT": env("NAUTOBOT_REDIS_TIMEOUT"),
    },
}
