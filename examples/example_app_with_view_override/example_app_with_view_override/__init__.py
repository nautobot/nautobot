from importlib import metadata

__version__ = metadata.version(__name__)

from nautobot.apps import NautobotAppConfig


class ExampleAppWithOverrideConfig(NautobotAppConfig):
    name = "example_app_with_view_override"
    verbose_name = "Example App With View Override"
    author = "Nautobot development team"
    author_email = "nautobot@example.com"
    version = __version__
    description = "For testing purposes only"
    base_url = "example-app-with-view-override"


config = ExampleAppWithOverrideConfig

default_app_config = "nautobot.core.apps.CoreConfig"
