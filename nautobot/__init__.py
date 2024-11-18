from importlib import metadata
import logging
import os
import sys

import django

# Primary package version
__version__ = metadata.version(__name__)

# Sentinel to make sure we only initialize once.
__initialized = False


def add_success_logger():
    """Add a custom log level for success messages."""
    SUCCESS = 25
    logging.addLevelName(SUCCESS, "SUCCESS")

    def success(self, message, *args, **kws):
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, message, args, **kws)

    logging.Logger.success = success
    return success


add_success_logger()
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

    if "nautobot_config" not in sys.modules:
        load_settings(config_path)
    django.setup()

    logger.info("Nautobot %s initialized!", __version__)
    __initialized = True
