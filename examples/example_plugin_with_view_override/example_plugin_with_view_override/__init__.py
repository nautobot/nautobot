try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)

from nautobot.apps import NautobotAppConfig


class ExamplePluginWithOverrideConfig(NautobotAppConfig):
    name = "example_plugin_with_view_override"
    verbose_name = "Example App With View Override"
    author = "Nautobot development team"
    author_email = "nautobot@example.com"
    version = __version__
    description = "For testing purposes only"
    base_url = "example-plugin-with-view-override"


config = ExamplePluginWithOverrideConfig

default_app_config = "nautobot.core.apps.CoreConfig"
