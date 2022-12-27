"""
Plugin utilities.
"""

import importlib.util
import json
import logging
import os
import pathlib
import sys

import simplejson
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

    # Load plugin UI
    load_plugin_ui(plugin, settings)

    # Update caching configg
    settings.CACHEOPS.update({f"{plugin_name}.{key}": value for key, value in plugin_config.caching_config.items()})


def get_start_and_end_indexes(data, filter_by):
    start = None
    end = None

    for idx, line in enumerate(data):
        if filter_by in line and not start:
            start = idx
        elif filter_by in line and start and not end:
            end = idx
        if start and end:
            break
    return start, end


def load_plugin_ui(plugin, settings):
    """Modify jsconfig and routers inorder to make nautobot react aware of a plugin UI"""
    plugin_path = os.path.dirname(plugin.__file__)
    plugin_ui_name = getattr(plugin.config, "nautobot_ui", None)
    if not plugin_ui_name:
        return

    plugin_ui_path = os.path.join(plugin_path, plugin_ui_name)
    if not os.path.exists(plugin_ui_path):
        return
        # raise PluginImproperlyConfigured(f"Plugin {plugin.config.name} UI directory does not exists")
    # TODO(timizuo): It would be nice to check if _app.js and package.json are available in plugin_ui since they are important to nautobot

    nautobot_path = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
    nautobot_ui_path = os.path.join(nautobot_path, "nautobot_ui")
    jsconfig_file_path = os.path.join(nautobot_ui_path, "jsconfig.json")

    ##########################################
    # Add plugin to nautobot_ui/jsconfig file
    ##########################################
    with open(jsconfig_file_path, "r", encoding="utf-8") as file:
        jsconfig = json.load(file)

    jsconfig_paths = jsconfig["compilerOptions"]["paths"]
    plugin_name_without_ui_suffix = plugin_ui_name.replace("_ui", "")
    plugin_ui_alias = f"@{plugin_name_without_ui_suffix}"
    plugin_ui_jsconfig_path_dir = f"{plugin_ui_path}/*"

    # check if plugin_ui name is available and path is correct
    if jsconfig_paths.get(plugin_ui_alias + "/*") != [plugin_ui_jsconfig_path_dir]:
        jsconfig["compilerOptions"]["paths"][plugin_ui_alias + "/*"] = [plugin_ui_jsconfig_path_dir]

        with open(jsconfig_file_path, "w", encoding="utf-8") as file:
            simplejson.dump(jsconfig, file, indent=4)

    ##########################################
    # Add plugin to nautobot_ui/src/router.js file
    ##########################################
    navigation_file_path = os.path.join(nautobot_ui_path, "src/config/nav-items.js")

    with open(navigation_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
        import_lines_index = get_start_and_end_indexes(lines, "__inject_import__")
        import_lines = lines[import_lines_index[0]: import_lines_index[1] + 1]

    # Check if plugin module has been imported
    plugin_import_name = plugin_name_without_ui_suffix.replace("_", " ").title().replace(" ", "")
    import_statement = f'import {{ navigation as {plugin_name_without_ui_suffix}_nav }} from "{plugin_ui_alias}/navigation";\n'
    if list(filter(lambda line: import_statement in line, import_lines)):
        # Skip because plugin route exists
        return

    # insert import statement
    lines.insert(import_lines_index[1], import_statement)

    navigation_lines_index = get_start_and_end_indexes(lines, "__inject_installed_plugins__")
    plugin_route_path = getattr(plugin.config, "base_url", plugin_name_without_ui_suffix.replace("_", "-"))
    route_statement = [
        "    {\n",
        f'        path: "{plugin_route_path}",\n',
        f"        navigation: {plugin_name_without_ui_suffix}_nav\n",
        "    },\n",
    ]
    lines[navigation_lines_index[1]: navigation_lines_index[1]] = route_statement

    with open(navigation_file_path, "w", encoding="utf-8") as file:
        file.writelines(lines)


# TODO(timizuo): Remember to remove plugin obsolete packages from nautobot_ui jsconfig and router
def remove_stale_nautobot_ui():
    """Remove from jsconfig and routers plugins that are not installed in nautobot"""


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
