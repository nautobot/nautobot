try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)


from nautobot.core.signals import nautobot_database_ready
from nautobot.extras.plugins import PluginConfig

from dummy_plugin.signals import nautobot_database_ready_callback


class DummyPluginConfig(PluginConfig):
    name = "dummy_plugin"
    verbose_name = "Dummy plugin"
    author = "Nautobot development team"
    author_email = "nautobot@example.com"
    version = __version__
    description = "For testing purposes only"
    base_url = "dummy-plugin"
    min_version = "0.9"
    max_version = "9.0"
    middleware = ["dummy_plugin.middleware.DummyMiddleware"]
    installed_apps = ["nautobot.extras.tests.dummy_plugin_dependency"]
    default_settings = {
        "dummy_default_key": "dummy_default_value",
    }

    # URL reverse lookup names
    home_view_name = "plugins:dummy_plugin:home"
    config_view_name = "plugins:dummy_plugin:config"

    def ready(self):
        """Callback when this plugin is loaded."""
        super().ready()
        # Connect the nautobot_database_ready_callback() function to the nautobot_database_ready signal.
        # This is by no means a requirement for all plugins, but is a useful way for a plugin to perform
        # database operations such as defining CustomFields, Relationships, etc. at the appropriate time.
        nautobot_database_ready.connect(nautobot_database_ready_callback, sender=self)


config = DummyPluginConfig
