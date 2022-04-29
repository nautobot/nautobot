try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)


from nautobot.core.signals import nautobot_database_ready
from nautobot.extras.plugins import PluginConfig

from example_plugin.signals import nautobot_database_ready_callback


class ExamplePluginConfig(PluginConfig):
    name = "example_plugin"
    verbose_name = "Example plugin"
    author = "Nautobot development team"
    author_email = "nautobot@example.com"
    version = __version__
    description = "For testing purposes only"
    base_url = "example-plugin"
    min_version = "0.9"
    max_version = "9.0"
    middleware = ["example_plugin.middleware.ExampleMiddleware"]
    installed_apps = ["nautobot.extras.tests.example_plugin_dependency"]
    default_settings = {
        "example_default_key": "example_default_value",
    }

    # URL reverse lookup names
    home_view_name = "plugins:example_plugin:home"
    config_view_name = "plugins:example_plugin:config"
    docs_view_name = "plugins:example_plugin:docs"

    def ready(self):
        """Callback when this plugin is loaded."""
        super().ready()
        # Connect the nautobot_database_ready_callback() function to the nautobot_database_ready signal.
        # This is by no means a requirement for all plugins, but is a useful way for a plugin to perform
        # database operations such as defining CustomFields, Relationships, etc. at the appropriate time.
        nautobot_database_ready.connect(nautobot_database_ready_callback, sender=self)


config = ExamplePluginConfig
