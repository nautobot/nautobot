"""Helper code for loading values that may be defined in settings.py/nautobot_config.py *or* in django-constance."""

import contextlib
import logging

from constance import config
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


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
