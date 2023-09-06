"""Helper code for loading values that may be defined in settings.py/nautobot_config.py *or* in django-constance."""

from constance import config
from django.conf import settings


def get_settings_or_config(variable_name):
    """Get a value from Django settings (if specified there) or Constance configuration (otherwise)."""
    # Explicitly set in settings.py or nautobot_config.py takes precedence, for now
    if hasattr(settings, variable_name):
        return getattr(settings, variable_name)
    return getattr(config, variable_name)
