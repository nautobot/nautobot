from importlib import metadata
import logging
import os

import django

# Primary package version
__version__ = metadata.version(__name__)

# Sentinel to make sure we only initialize once.
__initialized = False

logger = logging.getLogger(__name__)


def setup(config_path=None):
    """Similar to `django.setup()`, this configures Django with the appropriate Nautobot settings data."""
    from nautobot.core.cli import get_config_path, load_settings

    global __initialized

    if __initialized:
        return

    if config_path is None:
        config_path = get_config_path()

    # Point Django to our 'nautobot_config' pseudo-module that we'll load from the provided config path
    os.environ["DJANGO_SETTINGS_MODULE"] = "nautobot_config"

    load_settings(config_path)
    django.setup()

    logger.info("Nautobot initialized!")
    __initialized = True
