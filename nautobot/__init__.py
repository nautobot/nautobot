import logging

try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata


# Primary package version
__version__ = metadata.version(__name__)

# Sentinel to make sure we only initialize once.
__initialized = False

logger = logging.getLogger(__name__)


def setup():
    """
    Used to configure the settings for Nautobot so the app may run.

    This should be called before any settings are loaded as it handles all of
    the file loading, conditional settings, and settings overlays required to
    load Nautobot settings from anywhere using environment or config path.

    This pattern is inspired by `django.setup()`.
    """
    global __initialized

    if __initialized:
        logger.info("Nautobot NOT initialized (because it already was)!")
        return

    from nautobot.core import cli
    from nautobot.core.runner import configure_app

    configure_app(
        project="nautobot",
        default_config_path=cli.DEFAULT_CONFIG_PATH,
        default_settings=cli.DEFAULT_SETTINGS,
        settings_initializer=cli.generate_settings,
        settings_envvar=cli.SETTINGS_ENVVAR,
        initializer=cli._configure_settings,
    )
    logger.info("Nautobot initialized!")

    __initialized = True
