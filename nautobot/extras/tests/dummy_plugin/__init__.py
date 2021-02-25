from nautobot.extras.plugins import PluginConfig


class DummyPluginConfig(PluginConfig):
    name = "nautobot.extras.tests.dummy_plugin"
    verbose_name = "Dummy plugin"
    version = "0.0"
    description = "For testing purposes only"
    base_url = "dummy-plugin"
    min_version = "0.9"
    max_version = "9.0"
    middleware = ["nautobot.extras.tests.dummy_plugin.middleware.DummyMiddleware"]
    installed_apps = ["nautobot.extras.tests.dummy_plugin_dependency"]
    default_settings = {
        "dummy_default_key": "dummy_default_value",
    }


config = DummyPluginConfig
