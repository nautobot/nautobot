"""Customized Nautobot SSO items."""
from constance import config
from django.conf import settings
from django.shortcuts import resolve_url
from django.utils.encoding import force_str
from django.utils.functional import Promise
from social_core.pipeline import DEFAULT_AUTH_PIPELINE
from social_django.strategy import DjangoStrategy

from nautobot.users.models import SSOBackend


import logging

logger = logging.getLogger(__name__)


class NautobotStrategy(DjangoStrategy):
    """Subclassing to allow for constance config exposed via Nautobot."""

    def url_to_promie(self, variable_name, value):
        """Force text on URL named settings that are instance of Promise."""
        if variable_name.endswith("_URL"):
            if isinstance(value, Promise):
                value = force_str(value)
            value = resolve_url(value)
        return value

    def setting(self, name, default=None, backend=None):
        names = [setting_name(name), name]
        if backend:
            names.insert(0, setting_name(backend.name, name))
        for name in names:
            try:
                return self.get_setting(name, backend=backend)
            except (AttributeError, KeyError):
                pass
        return default

    def get_setting(self, variable_name, backend=None):
        """Try to find setting in django settings, fallback to namespaced constance config."""
        # First check if setting exists in settings
        if hasattr(settings, variable_name):
            return self.url_to_promie(variable_name, getattr(settings, variable_name))

        # Upstream strategy is expected an AttributeError or KeyError when setting is not found
        # Following block only works if a backend is supplied
        if not backend:
            raise AttributeError("Backend required if not ")

        try:
            backend_config = SSOBackend.objects.get(_backend_name=backend.name)
            if variable_name == backend_config.backend_var_namespace + "SECRET":
                if not backend_config.secret:
                    raise AttributeError("No Secret Configured")
                return backend_config.secret.get_value()
            if not variable_name in backend_config.configuration:
                raise AttributeError("Setting not configured")
            return self.url_to_promie(variable_name, backend_config.configuration[variable_name])
        except SSOBackend.ObjectDoesNotExist:
            raise AttributeError("Backend Not Configured")
        raise AttributeError(f"{variable_name} not found.")

    def get_backends(self):
        """Expose only database configured backend if SOCIAL_CORE_DATABASE_CONFIGURATION is True."""
        if get_settings_or_config("SOCIAL_CORE_DATABASE_CONFIGURATION"):
            return list(SSOBackend.objects.filter(enabled=True).values_list("backend", flat=True))
        return settings.AUTHENTICATION_BACKENDS

    def get_pipeline(self, backend=None):
        """Allows for DEFAULT, settings, or Constance Config."""
        try:
            return get_settings_or_config("SOCIAL_CORE_PIPELINE")
        except AttributeError:
            return DEFAULT_AUTH_PIPELINE
