"""Helper functions to detect settings after app initialization (AKA 'dynamic settings')."""

from collections import namedtuple
import os
import sys

from django.conf import settings
import structlog

ConstanceConfigItem = namedtuple("ConstanceConfigItem", ["default", "help_text", "field_type"], defaults=[str])

#
# X_auth_enabled checks to see if a backend has been specified, thus assuming it is enabled.
#


def remote_auth_enabled(auth_backends):
    return "nautobot.core.authentication.RemoteUserBackend" in auth_backends


def sso_auth_enabled(auth_backends):
    for backend in auth_backends:
        if backend.startswith(settings.SOCIAL_AUTH_BACKEND_PREFIX):
            return True
    return False


def ldap_auth_enabled(auth_backends):
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

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truthy value: `{arg}`")


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


def setup_structlog_logging(
    django_logging: dict,
    django_apps: list,
    django_middleware: list,
    log_level="INFO",
    root_level="INFO",
    debug=False,
    debug_db=False,
    plain_format=False,
) -> None:
    """Set up structlog logging for Django."""
    django_logging["version"] = 1
    django_logging["disable_existing_loggers"] = True
    if "test" in sys.argv:
        django_logging["handlers"] = {
            "null_handler": {
                "level": "INFO",
                "class": "logging.NullHandler",
            },
        }
        for logger in django_logging["loggers"].values():
            logger["handlers"] = ["null_handler"]
            logger["level"] = "INFO"

        return

    django_apps.append("django_structlog")
    django_middleware.append("django_structlog.middlewares.RequestMiddleware")

    processors = (
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        *([] if debug else [structlog.processors.format_exc_info]),
    )

    django_logging["formatters"] = {
        "default_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": processors,
            "processor": structlog.dev.ConsoleRenderer() if plain_format else structlog.processors.JSONRenderer(),
        },
    }

    django_logging["handlers"] = {
        "default_handler": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default_formatter",
        },
    }

    django_logging["root"] = {
        "handlers": ["default_handler"],
        "level": root_level,
    }

    if debug_db:
        django_logging["loggers"]["django.db.backends"] = {"level": "DEBUG"}

    for logger in django_logging["loggers"].values():
        if "level" not in logger:
            logger["level"] = log_level
        logger["propagate"] = False
        logger["handlers"] = ["default_handler"]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
