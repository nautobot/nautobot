"""Helper code for loading values that may be defined in settings.py/nautobot_config.py *or* in django-constance."""

import contextlib
from functools import lru_cache
import logging

from constance import config
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError, ProgrammingError

from nautobot.core.choices import NautobotEditionChoices
from nautobot.core.constants import TEMPLATE_EXPOSED_SETTINGS
from nautobot.core.utils.otel import traced_span

logger = logging.getLogger(__name__)


def is_template_exposable_setting(variable_name):
    """Return whether `variable_name` is safe to read from a rendered template.

    Only settings and Constance keys named in the `TEMPLATE_EXPOSED_SETTINGS` allowlist may be exposed.
    """
    return variable_name in TEMPLATE_EXPOSED_SETTINGS


class ExposedSettings:
    """Read-only proxy over Django settings that only permits access to template-exposable settings.

    Templates read non-sensitive values through this proxy (e.g. `{{ settings.VERSION }}`); any other
    attribute access raises `AttributeError`.
    """

    def __getattr__(self, name):
        if is_template_exposable_setting(name):
            return getattr(settings, name)
        raise AttributeError(name)


def get_settings_or_config(variable_name, fallback=None):
    """
    Get a value from Django settings (if specified there) or Constance configuration (otherwise).

    The fallback value is returned *only* if the requested variable cannot be found at all - this is an error case,
    and will generate warning logs.
    """
    # Explicitly set in settings.py or nautobot_config.py takes precedence, for now
    if hasattr(settings, variable_name):
        return getattr(settings, variable_name)
    # django-constance 4.x removed some built-in error handling here, so we have to do it ourselves now
    with traced_span(
        "nautobot.core.config",
        "constance_config.get",
        **{"constance_config.key": variable_name},
    ):
        with contextlib.suppress(ObjectDoesNotExist, OperationalError, ProgrammingError):
            return getattr(config, variable_name)
    logger.warning(
        'Configuration "%s" is not in settings, and could not read from the Constance database table '
        "(perhaps not initialized yet?)",
        variable_name,
    )
    if variable_name in settings.CONSTANCE_CONFIG:
        default = settings.CONSTANCE_CONFIG[variable_name][0]
        logger.warning('Using default value of "%s" from Constance configuration for "%s"', default, variable_name)
        return default
    logger.warning(
        'Constance configuration does not include an entry for "%s" - must return %s', variable_name, fallback
    )
    return fallback


@lru_cache(maxsize=None)
def get_nautobot_edition():
    """Return the active Nautobot edition: the highest-weighted `nautobot_edition` declared by any installed app."""
    current_edition = NautobotEditionChoices.COMMUNITY
    editions_by_weight = NautobotEditionChoices.WEIGHTS
    for app_config in apps.get_app_configs():
        app_edition = getattr(app_config, "nautobot_edition", None)
        if app_edition in editions_by_weight and editions_by_weight[app_edition] > editions_by_weight[current_edition]:
            current_edition = app_edition
    return current_edition
