"""Helper code for loading values that may be defined in settings.py/nautobot_config.py *or* in django-constance."""

import contextlib

from constance import config
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError, ProgrammingError


def get_app_settings_or_config(app_name, variable_name):
    """Get a value from Django settings (if specified there) or Constance configuration (otherwise)."""
    # Explicitly set in settings.py or nautobot_config.py takes precedence, for now
    if variable_name in settings.PLUGINS_CONFIG[app_name]:
        return settings.PLUGINS_CONFIG[app_name][variable_name]
    # django-constance 4.x removed some built-in error handling here, so we have to do it ourselves now
    with contextlib.suppress(ObjectDoesNotExist, OperationalError, ProgrammingError):
        return getattr(config, f"{app_name}__{variable_name}")
    return None
