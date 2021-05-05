"""Helper functions to detect settings after app initialization.  AKA 'dynamic settings'"""
from distutils.util import strtobool
from functools import lru_cache


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
        if backend.startswith("social_core.backends"):
            return True
    return False


def ldap_auth_enabled(auth_backends):
    return _ldap_auth_enabled(tuple(auth_backends))


@lru_cache(maxsize=5)
def _ldap_auth_enabled(auth_backends):
    return "django_auth_ldap.backend.LDAPBackend" in auth_backends


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
