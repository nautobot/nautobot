try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)


from nautobot.extras.plugins import PluginConfig


class DummyPluginConfig(PluginConfig):
    name = "dummy_plugin"
    verbose_name = "Dummy plugin"
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


config = DummyPluginConfig
