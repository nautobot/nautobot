import re

from django.conf import settings
from django.core.checks import Error, register, Tags, Warning  # pylint: disable=redefined-builtin
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import connections

E002 = Error(
    "'nautobot.core.authentication.ObjectPermissionBackend' must be included in AUTHENTICATION_BACKENDS",
    id="nautobot.core.E002",
    obj=settings,
)

E003 = Error(
    "RELEASE_CHECK_TIMEOUT must be at least 3600 seconds (1 hour)",
    id="nautobot.core.E003",
    obj=settings,
)

E004 = Error(
    "RELEASE_CHECK_URL must be a valid API URL. Example: https://api.github.com/repos/nautobot/nautobot",
    id="nautobot.core.E004",
    obj=settings,
)

E005 = Error(
    "MAINTENANCE_MODE has been set but SESSION_ENGINE is still using the database.  Nautobot can not enter Maintenance mode.",
    id="nautobot.core.E005",
    obj=settings,
)

W005 = Warning(
    "STORAGE_CONFIG has been set but STORAGE_BACKEND is not defined. STORAGE_CONFIG will be ignored.",
    id="nautobot.core.W005",
    obj=settings,
)

MIN_POSTGRESQL_MAJOR_VERSION = 12
MIN_POSTGRESQL_MINOR_VERSION = 0

MIN_POSTGRESQL_VERSION = MIN_POSTGRESQL_MAJOR_VERSION * 10000 + MIN_POSTGRESQL_MINOR_VERSION


@register(Tags.security)
def check_object_permissions_backend(app_configs, **kwargs):
    if "nautobot.core.authentication.ObjectPermissionBackend" not in settings.AUTHENTICATION_BACKENDS:
        return [E002]
    return []


@register(Tags.compatibility)
def check_release_check_timeout(app_configs, **kwargs):
    if hasattr(settings, "RELEASE_CHECK_TIMEOUT") and settings.RELEASE_CHECK_TIMEOUT < 3600:
        return [E003]
    return []


@register(Tags.compatibility)
def check_release_check_url(app_configs, **kwargs):
    validator = URLValidator()
    if hasattr(settings, "RELEASE_CHECK_URL") and settings.RELEASE_CHECK_URL:
        try:
            validator(settings.RELEASE_CHECK_URL)
        except ValidationError:
            return [E004]
    return []


@register(Tags.compatibility)
def check_storage_config_and_backend(app_configs, **kwargs):
    if settings.STORAGE_CONFIG and (settings.STORAGE_BACKEND is None):
        return [W005]
    return []


@register(Tags.compatibility)
def check_maintenance_mode(app_configs, **kwargs):
    if settings.MAINTENANCE_MODE and settings.SESSION_ENGINE == "django.contrib.sessions.backends.db":
        return [E005]
    return []


@register(Tags.database)
def check_postgresql_version(app_configs, databases=None, **kwargs):
    if databases is None:
        return []
    errors = []
    for alias in databases:
        conn = connections[alias]
        if conn.vendor == "postgresql":
            server_version = conn.cursor().connection.info.server_version
            if server_version < MIN_POSTGRESQL_VERSION:
                errors.append(
                    Error(
                        f"PostgreSQL version less than {MIN_POSTGRESQL_VERSION} "
                        f"(i.e. {MIN_POSTGRESQL_MAJOR_VERSION}.{MIN_POSTGRESQL_MINOR_VERSION}) "
                        "is not supported by this version of Nautobot",
                        id="nautobot.core.E006",
                        obj=f"connections[{alias}]",
                        hint=f"Detected version is {server_version} (major version {server_version // 10000})",
                    )
                )

    return errors


@register(Tags.security)
def check_sanitizer_patterns(app_configs, **kwargs):
    errors = []
    for entry in settings.SANITIZER_PATTERNS:
        if (
            not isinstance(entry, (tuple, list))
            or len(entry) != 2
            or not isinstance(entry[0], re.Pattern)
            or not isinstance(entry[1], str)
        ):
            errors.append(
                Error(
                    "Invalid entry in settings.SANITIZER_PATTERNS",
                    hint="Each entry must be a list or tuple of (compiled regexp, replacement string)",
                    obj=entry,
                    id="nautobot.core.E007",
                )
            )
            continue

        sanitizer, repl = entry
        try:
            sanitizer.sub(repl.format(replacement="(REDACTED)"), "Hello world!")
        except re.error as exc:
            errors.append(
                Error(
                    "Entry in settings.SANITIZER_PATTERNS not usable for sanitization",
                    hint=str(exc),
                    obj=entry,
                    id="nautobot.core.E008",
                )
            )

    return errors
