"""Customized Nautobot SSO items."""
from constance import config
from django.conf import settings
from django.shortcuts import resolve_url
from django.utils.encoding import force_str
from django.utils.functional import Promise
from social_django.strategy import DjangoStrategy


import logging

logger = logging.getLogger(__name__)


class NautobotStrategy(DjangoStrategy):
    """Subclassing to allow for constance config exposed via Nautobot."""

    def get_setting(self, variable_name):
        """Try to find setting in django settings, fallback to namespaced constance config."""
        value = None
        if hasattr(settings, variable_name):
            value = getattr(settings, variable_name)
        social_config = getattr(config, "SOCIAL_CORE_CONFIG")
        if variable_name in social_config:
            value = social_config[variable_name]
        if not value:
            raise AttributeError(f"{variable_name} not found.")
        # Force text on URL named settings that are instance of Promise
        if variable_name.endswith("_URL"):
            if isinstance(value, Promise):
                value = force_str(value)
            value = resolve_url(value)
        return value

    def get_backends(self):
        """Only expose configured backends via constance config."""
        return getattr(config, "ALLOWED_SOCIAL_BACKENDS")
