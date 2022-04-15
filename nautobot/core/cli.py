"""
Utilities and primitives for the `nautobot-server` CLI command.
"""

from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from jinja2 import BaseLoader, Environment

from nautobot.core.runner import run_app
from nautobot.extras.plugins.utils import load_plugins


# Default file location for the generated config emitted by `init`
NAUTOBOT_ROOT = os.getenv("NAUTOBOT_ROOT", os.path.expanduser("~/.nautobot"))
DEFAULT_CONFIG_PATH = os.path.join(NAUTOBOT_ROOT, "nautobot_config.py")

# Default settings to use when building the config
DEFAULT_SETTINGS = "nautobot.core.settings"

# Name of the environment variable used to specify path of config
SETTINGS_ENVVAR = "NAUTOBOT_CONFIG"

# Base directory for this module
BASE_DIR = os.path.dirname(__file__)

# File path of template used to generate config emitted by `init`
CONFIG_TEMPLATE = os.path.join(BASE_DIR, "templates/nautobot_config.py.j2")

DESCRIPTION = """
Nautobot server management utility.

Type '%(prog)s help' to display a list of included sub-commands.

Type '%(prog)s init' to generate a new configuration.
"""


def main():
    """
    The main server CLI command that replaces `manage.py` and allows a
    configuration file to be passed in.

    How this works:

    - Process CLI args
    - Load default settings
    - Read config file from path
    - Overlay config settings on top of default settings
    - Overlay special/conditional settings (see `_configure_settings`)
    """
    run_app(
        project="nautobot",
        description=DESCRIPTION,
        default_config_path=DEFAULT_CONFIG_PATH,
        default_settings=DEFAULT_SETTINGS,
        settings_initializer=generate_settings,
        settings_envvar=SETTINGS_ENVVAR,
        initializer=_configure_settings,  # Called after defaults
    )


def generate_settings(config_template=CONFIG_TEMPLATE, **kwargs):
    """
    This command is ran when `default_config_path` doesn't exist, or `init` is
    ran and returns a string representing the default data to put into the
    settings file.
    """
    secret_key = get_random_secret_key()

    with open(config_template) as fh:
        environment = Environment(loader=BaseLoader, keep_trailing_newline=True)
        config = environment.from_string(fh.read())

    return config.render(secret_key=secret_key)


def _configure_settings(config):
    """
    Callback for processing conditional or special purpose settings.

    Any specially prepared settings will be handled here, such as loading
    plugins, enabling social auth, etc.

    This is intended to be called by `run_app` and should not be invoked
    directly.

    :param config:
        A dictionary of `config_path`, `project`, `settings`

    Example::

        {
            'project': 'nautobot',
            'config_path': '/path/to/nautobot_config.py',
            'settings': <LazySettings "nautobot_config">
        }
    """

    settings = config["settings"]

    # Include the config path to the settings to align with builtin
    # `settings.SETTINGS_MODULE`. Useful for debugging correct config path.
    settings.SETTINGS_PATH = config["config_path"]

    #
    # Storage directories
    #
    if not os.path.exists(settings.GIT_ROOT):
        os.makedirs(settings.GIT_ROOT)
    if not os.path.exists(settings.JOBS_ROOT):
        os.makedirs(settings.JOBS_ROOT)
    if not os.path.exists(os.path.join(settings.JOBS_ROOT, "__init__.py")):
        Path(os.path.join(settings.JOBS_ROOT, "__init__.py")).touch()
    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, "devicetype-images")):
        os.makedirs(os.path.join(settings.MEDIA_ROOT, "devicetype-images"))
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, "image-attachments")):
        os.makedirs(os.path.join(settings.MEDIA_ROOT, "image-attachments"))
    if not os.path.exists(settings.STATIC_ROOT):
        os.makedirs(settings.STATIC_ROOT)

    #
    # Databases
    #

    # If metrics are enabled and postgres is the backend, set the driver to the
    # one provided by django-prometheus.
    if settings.METRICS_ENABLED and "postgres" in settings.DATABASES["default"]["ENGINE"]:
        settings.DATABASES["default"]["ENGINE"] = "django_prometheus.db.backends.postgresql"

    # Create secondary db connection for job logging. This still writes to the default db, but because it's a separate
    # connection, it allows allows us to "escape" from transaction.atomic() and ensure that job log entries are saved
    # to the database even when the rest of the job transaction is rolled back.
    settings.DATABASES["job_logs"] = settings.DATABASES["default"].copy()
    # When running unit tests, treat it as a mirror of the default test DB, not a separate test DB of its own
    settings.DATABASES["job_logs"]["TEST"] = {"MIRROR": "default"}

    #
    # Media storage
    #

    if settings.STORAGE_BACKEND is not None:
        settings.DEFAULT_FILE_STORAGE = settings.STORAGE_BACKEND

        # django-storages
        if settings.STORAGE_BACKEND.startswith("storages."):

            try:
                import storages.utils
            except ModuleNotFoundError as e:
                if getattr(e, "name") == "storages":
                    raise ImproperlyConfigured(
                        f"STORAGE_BACKEND is set to {settings.STORAGE_BACKEND} but django-storages is not present. It "
                        f"can be installed by running 'pip install django-storages'."
                    )
                raise e

            # Monkey-patch django-storages to fetch settings from STORAGE_CONFIG or fall back to settings
            def _setting(name, default=None):
                if name in settings.STORAGE_CONFIG:
                    return settings.STORAGE_CONFIG[name]
                return getattr(settings, name, default)

            storages.utils.setting = _setting

    #
    # Plugins
    #

    # Process the plugins and manipulate the specified config settings that are
    # passed in.
    load_plugins(settings)


if __name__ == "__main__":
    main()
