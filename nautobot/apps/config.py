"""Helper code for loading values that may be defined in settings.py/nautobot_config.py *or* in django-constance."""

from constance import config
from django import template
from django.conf import settings
from django_jinja import library

register = template.Library()


def get_app_settings_or_config(app_name, variable_name):
    """Get a value from Django settings (if specified there) or Constance configuration (otherwise)."""
    # Explicitly set in settings.py or nautobot_config.py takes precedence, for now
    if variable_name in settings.PLUGINS_CONFIG[app_name]:
        return settings.PLUGINS_CONFIG[app_name][variable_name]
    return getattr(config, f"{app_name}:{variable_name}")

#
# Filters
#

@library.filter()
@register.filter()
def app_settings_or_config(key, app_name):
    """Get a value from Django settings (if specified there) or Constance configuration (otherwise)."""
    return get_app_settings_or_config(app_name, key)
