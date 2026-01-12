"""
Plugin utilities.
"""

import importlib.util
import logging

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from nautobot.core.settings_funcs import ConstanceConfigItem

from .exceptions import PluginImproperlyConfigured, PluginNotFound

# Logging object
logger = logging.getLogger(__name__)


def load_plugins(settings):
    """Process plugins and log errors if they can't be loaded."""
    for plugin_name in settings.PLUGINS:
        # Attempt to load the plugin but let any errors bubble up.
        load_plugin(plugin_name, settings)


def load_plugin(plugin_name, settings):
    """Process a single plugin or raise errors that get bubbled up."""

    logger.debug(f"Loading {plugin_name}!")

    # Import plugin module
    try:
        plugin = importlib.import_module(plugin_name)
    except ModuleNotFoundError as err:
        if getattr(err, "name") == plugin_name:
            raise PluginNotFound(
                f"Unable to import plugin {plugin_name}: Module not found. Check that the plugin module has been "
                f"installed within the correct Python environment."
            ) from err
        raise err

    # Validate plugin config
    try:
        plugin_config = plugin.config
    except AttributeError as err:
        raise PluginImproperlyConfigured(
            f"Plugin {plugin_name} does not provide a 'config' variable. This should be defined in the plugin's "
            f"__init__.py file and point to the NautobotAppConfig subclass."
        ) from err

    # Validate user-provided configuration settings and assign defaults. Plugin
    # validation that fails will stop before modifying any settings.
    if plugin_name not in settings.PLUGINS_CONFIG:
        settings.PLUGINS_CONFIG[plugin_name] = {}
    plugin_config.validate(settings.PLUGINS_CONFIG[plugin_name], settings.VERSION)

    # Plugin config is valid, so now we can and add to INSTALLED_APPS.
    plugin_import_path = f"{plugin_config.__module__}.{plugin_config.__name__}"
    if plugin_import_path not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS.append(plugin_import_path)

    # Include any extra installed apps provided by the plugin
    # TODO(jathan): We won't be able to support advanced app-ordering concerns
    # and if the time comes that we do, this will have to be rethought.
    for plugin_installed_app in plugin_config.installed_apps:
        if plugin_installed_app not in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS.append(plugin_installed_app)

    # Include any extra middleware provided by the plugin
    for middleware in plugin_config.middleware:
        if middleware not in settings.MIDDLEWARE:
            settings.MIDDLEWARE.append(middleware)

    # Update Constance Config and Constance Fieldset
    if plugin_config.constance_config:
        app_config = {}
        for key, value in plugin_config.constance_config.items():
            config_item = value
            # Enforce ConstanceConfigItem namedtuple
            if not isinstance(value, ConstanceConfigItem):
                config_item = ConstanceConfigItem(*value)
                plugin_config.constance_config[key] = config_item

            app_config[f"{plugin_name}__{key}"] = config_item

        settings.CONSTANCE_CONFIG.update(app_config)
        settings.CONSTANCE_CONFIG_FIELDSETS.update({f"{plugin_config.verbose_name}": app_config.keys()})


def get_sso_backend_name(social_auth_module):
    """
    Return the name parameter of the social auth module defined in the module itself.

    :param social_auth_module: The social auth python module to read the name parameter from
    """
    try:
        backend_class = import_string(social_auth_module)
    except ImportError:
        raise ImproperlyConfigured(f"Unable to import Social Auth Module {social_auth_module}.")
    backend_name = backend_class.name
    return backend_name
