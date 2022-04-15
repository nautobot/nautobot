"""
Plugin utilities.
"""

import importlib.util
import logging
import sys

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .exceptions import PluginNotFound, PluginImproperlyConfigured


# Logging object
logger = logging.getLogger("nautobot.plugins")


def import_object(module_and_object):
    """
    Import a specific object from a specific module by name, such as "nautobot.extras.plugins.utils.import_object".

    Returns the imported object, or None if it doesn't exist.
    """
    target_module_name, object_name = module_and_object.rsplit(".", 1)
    module_hierarchy = target_module_name.split(".")

    # Iterate through the module hierarchy, checking for the existence of each successive submodule.
    # We have to do this rather than jumping directly to calling find_spec(target_module_name)
    # because find_spec will raise a ModuleNotFoundError if any parent module of target_module_name does not exist.
    module_name = ""
    for module_component in module_hierarchy:
        module_name = f"{module_name}.{module_component}" if module_name else module_component
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            # No such module
            return None

    # Okay, target_module_name exists. Load it if not already loaded
    if target_module_name in sys.modules:
        module = sys.modules[target_module_name]
    else:
        module = importlib.util.module_from_spec(spec)
        sys.modules[target_module_name] = module
        spec.loader.exec_module(module)

    return getattr(module, object_name, None)


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
            f"__init__.py file and point to the PluginConfig subclass."
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

    # Update caching configg
    settings.CACHEOPS.update({f"{plugin_name}.{key}": value for key, value in plugin_config.caching_config.items()})


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
