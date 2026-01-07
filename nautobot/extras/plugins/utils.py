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


def load_plugins(settings_module):
    """Process plugins and log errors if they can't be loaded."""
    for plugin_name in settings_module.PLUGINS:
        # Attempt to load the plugin but let any errors bubble up.
        load_plugin(plugin_name, settings_module)


def load_plugin(plugin_name, settings_module):
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
    if plugin_name not in settings_module.PLUGINS_CONFIG:
        settings_module.PLUGINS_CONFIG[plugin_name] = {}
    plugin_config.validate(settings_module.PLUGINS_CONFIG[plugin_name], settings_module.VERSION)

    # Plugin config is valid, so now we can and add to INSTALLED_APPS.
    plugin_import_path = f"{plugin_config.__module__}.{plugin_config.__name__}"
    if plugin_import_path not in settings_module.INSTALLED_APPS:
        settings_module.INSTALLED_APPS.append(plugin_import_path)

    # Include any extra installed apps provided by the plugin
    # TODO(jathan): We won't be able to support advanced app-ordering concerns
    # and if the time comes that we do, this will have to be rethought.
    for plugin_installed_app in plugin_config.installed_apps:
        if plugin_installed_app not in settings_module.INSTALLED_APPS:
            settings_module.INSTALLED_APPS.append(plugin_installed_app)

    # Include any extra middleware provided by the plugin
    for middleware in plugin_config.middleware:
        if middleware not in settings_module.MIDDLEWARE:
            settings_module.MIDDLEWARE.append(middleware)

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

        settings_module.CONSTANCE_CONFIG.update(app_config)
        settings_module.CONSTANCE_CONFIG_FIELDSETS.update({f"{plugin_config.verbose_name}": app_config.keys()})


def load_function_from_app_if_present(dotted_path, default_return=None):
    """
    If a given App is in `settings.PLUGINS`, load the given function from that App, else return a usable stub instead.

    NOTE: since this relies on inspecting `settings.PLUGINS`, it's generally *NOT* safe to call at module import time.
    Call it inline as needed instead.

    Args:
        dotted_path (str): Path to a function to import, such as "nautobot_version_control.utils.active_branch"
        default_return (Any): Value to return from the stub function if the App isn't installed/enabled.

    Returns:
        func (Callable): either the requested function, or a lambda function that just returns `default_return`.
    """
    from django.conf import settings

    app_name, _ = dotted_path.split(".", 1)
    if app_name in settings.PLUGINS:
        return import_string(dotted_path)

    return lambda *args, **kwargs: default_return


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
