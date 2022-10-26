"""Helper functions to detect settings after app initialization (AKA 'dynamic settings')."""

from django.conf import settings
from distutils.util import strtobool
from functools import lru_cache
import os


#
# X_auth_enabled checks to see if a backend has been specified, thus assuming it is enabled.
# Leverages `lru_cache` since these are called per user session.  The wrappers are a
# workaround to pass `lru_cache` a hashable data structure.
#


def remote_auth_enabled(auth_backends):
    return _remote_auth_enabled(tuple(auth_backends))


@lru_cache(maxsize=5)
def _remote_auth_enabled(auth_backends):
    return "nautobot.core.authentication.RemoteUserBackend" in auth_backends


def sso_auth_enabled(auth_backends):
    return _sso_auth_enabled(tuple(auth_backends))


@lru_cache(maxsize=5)
def _sso_auth_enabled(auth_backends):
    for backend in auth_backends:
        if backend.startswith(settings.SOCIAL_AUTH_BACKEND_PREFIX):
            return True
    return False


def ldap_auth_enabled(auth_backends):
    return _ldap_auth_enabled(tuple(auth_backends))


@lru_cache(maxsize=5)
def _ldap_auth_enabled(auth_backends):
    return "django_auth_ldap.backend.LDAPBackend" in auth_backends


def is_truthy(arg):
    """
    Convert "truthy" strings into Booleans.

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


def parse_redis_connection(redis_database):
    """
    Parse environment variables to emit a Redis connection URL.

    Args:
        redis_database (int): Redis database number to use for the connection

    Returns:
        Redis connection URL (str)
    """
    # The following `_redis_*` variables are used to generate settings based on
    # environment variables.
    redis_scheme = os.getenv("NAUTOBOT_REDIS_SCHEME")
    if redis_scheme is None:
        redis_scheme = "rediss" if is_truthy(os.getenv("NAUTOBOT_REDIS_SSL", "false")) else "redis"
    redis_host = os.getenv("NAUTOBOT_REDIS_HOST", "localhost")
    redis_port = int(os.getenv("NAUTOBOT_REDIS_PORT", "6379"))
    redis_username = os.getenv("NAUTOBOT_REDIS_USERNAME", "")
    redis_password = os.getenv("NAUTOBOT_REDIS_PASSWORD", "")

    # Default Redis credentials to being empty unless a username or password is
    # provided. Then map it to "username:password@". We're not URL-encoding the
    # password because the Redis Python client already does this.
    redis_creds = ""
    if redis_username or redis_password:
        redis_creds = f"{redis_username}:{redis_password}@"

    if redis_scheme == "unix":
        return f"{redis_scheme}://{redis_creds}{redis_host}?db={redis_database}"
    else:
        return f"{redis_scheme}://{redis_creds}{redis_host}:{redis_port}/{redis_database}"
