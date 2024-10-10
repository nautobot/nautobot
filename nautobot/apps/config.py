"""Helper code for loading values that may be defined in settings.py/nautobot_config.py *or* in django-constance."""

import contextlib
import logging

from constance import config
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


def get_app_settings_or_config(app_name, variable_name, fallback=None):
    """
    Get a value from Django settings.PLUGINS_CONFIG (if specified there) or Constance configuration (otherwise).

    The fallback value is returned *only* if the requested variable cannot be found at all - this is an error case,
    and will generate warning logs.
    """
    # Explicitly set in settings.py or nautobot_config.py takes precedence, for now
    if variable_name in settings.PLUGINS_CONFIG[app_name]:
        return settings.PLUGINS_CONFIG[app_name][variable_name]
    # django-constance 4.x removed some built-in error handling here, so we have to do it ourselves now
    constance_key = f"{app_name}__{variable_name}"
    with contextlib.suppress(ObjectDoesNotExist, OperationalError, ProgrammingError):
        return getattr(config, constance_key)
    logger.warning(
        '"PLUGINS_CONFIG[%r][%r]" is not in settings, and could not read from the Constance database table '
        "(perhaps not initialized yet?)",
        app_name,
        variable_name,
    )
    if constance_key in settings.CONSTANCE_CONFIG:
        default = settings.CONSTANCE_CONFIG[constance_key][0]
        logger.warning('Using default value of "%s" from Constance configuration for "%s"', default, constance_key)
        return default
    logger.warning(
        'Constance configuration does not include an entry for "%s" - must return %s', constance_key, fallback
    )
    return fallback
