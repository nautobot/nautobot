from importlib import metadata
import os

import django

# Primary package version
__version__ = metadata.version(__name__)


def setup(config_path=None):
    """Similar to `django.setup()`, this configures Django with the appropriate Nautobot settings data."""
    from nautobot.core.cli import get_config_path, load_settings

    if config_path is None:
        config_path = get_config_path()

    # Point Django to our 'nautobot_config' pseudo-module that we'll load from the provided config path
    os.environ["DJANGO_SETTINGS_MODULE"] = "nautobot_config"

    load_settings(config_path)
    django.setup()
