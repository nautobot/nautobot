"""
Utilities and primitives for the `nautobot-server` CLI command.
"""

import argparse
import importlib.util
import os
import sys

import django
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, CommandParser, execute_from_command_line
from django.core.management.utils import get_random_secret_key
from jinja2 import BaseLoader, Environment

from nautobot.core.events import load_event_brokers
from nautobot.core.settings_funcs import is_truthy
from nautobot.extras.plugins.utils import load_plugins

CONFIG_TEMPLATE = os.path.join(os.path.dirname(__file__), "../templates/nautobot_config.py.j2")

DESCRIPTION = """
Nautobot server management utility.

Type '%(prog)s help' to display a list of included sub-commands.

Type '%(prog)s init' to generate a new configuration.
"""

USAGE = """%(prog)s --help
       %(prog)s --version
       %(prog)s init [--disable-installation-metrics] [CONFIG_PATH]
       %(prog)s help [SUBCOMMAND]
       %(prog)s [-c CONFIG_PATH] SUBCOMMAND ..."""


def _preprocess_settings(settings, config_path):
    """
    After loading nautobot_config.py and nautobot.core.settings, but before starting Django, modify the settings module.

    - Set settings.SETTINGS_PATH for ease of reference
    - Handle `EXTRA_*` settings
    - Create Nautobot storage directories if they don't already exist
    - Change database backends to django-prometheus if appropriate
    - Set up 'job_logs' database mirror
    - Handle our custom `STORAGE_BACKEND` setting.
    - Load plugins based on settings.PLUGINS (potentially affecting INSTALLED_APPS, MIDDLEWARE, and CONSTANCE_CONFIG)
    - Load event brokers based on settings.EVENT_BROKERS
    """
    settings.SETTINGS_PATH = config_path

    # Any setting that starts with EXTRA_ and matches a setting that is a list or tuple
    # will automatically append the values to the current setting.
    # "It might make sense to make this less magical"
    extras = {}
    for setting in dir(settings):
        if setting == setting.upper() and setting.startswith("EXTRA_"):
            base_setting = setting[6:]
            if isinstance(getattr(settings, base_setting), (list, tuple)):
                extras[base_setting] = getattr(settings, setting)
    for base_setting, extra_values in extras.items():
        base_value = getattr(settings, base_setting)
        setattr(settings, base_setting, base_value + type(base_value)(extra_values))

    #
    # Storage directories
    #
    os.makedirs(settings.GIT_ROOT, exist_ok=True)
    os.makedirs(settings.JOBS_ROOT, exist_ok=True)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "devicetype-images"), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "image-attachments"), exist_ok=True)
    os.makedirs(settings.STATIC_ROOT, exist_ok=True)

    #
    # Databases
    #

    # If metrics are enabled and postgres is the backend, set the driver to the
    # one provided by django-prometheus.
    if settings.METRICS_ENABLED:
        if "postgres" in settings.DATABASES["default"]["ENGINE"]:
            settings.DATABASES["default"]["ENGINE"] = "django_prometheus.db.backends.postgresql"
        elif "mysql" in settings.DATABASES["default"]["ENGINE"]:
            settings.DATABASES["default"]["ENGINE"] = "django_prometheus.db.backends.mysql"

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

    #
    # Event Broker
    #

    load_event_brokers(settings.EVENT_BROKERS)


def load_settings(config_path):
    """Load nautobot_config.py or its equivalent into memory as a `nautobot_config` pseudo-module."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found at {config_path} - "
            "Please provide a valid --config-path path, or use 'nautobot-server init' to create a new configuration."
        )
    spec = importlib.util.spec_from_file_location("nautobot_config", config_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["nautobot_config"] = module
    spec.loader.exec_module(module)
    _preprocess_settings(module, config_path)


class _VerboseHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Argparse Formatter that includes newlines and shows argument defaults."""


class _VersionAction(argparse.Action):
    """Print Nautobot and Django versions."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("nargs", 0)
        kwargs.setdefault("default", argparse.SUPPRESS)
        kwargs.setdefault("type", None)
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string):
        from nautobot import __version__

        print(f"Nautobot version: {__version__}")
        print(f"Django version: {django.__version__}")
        print(f"Configuration file: {namespace.config_path}")
        parser.exit(0)


def _init_settings(args):
    """Create a new nautobot_config.py or equivalent."""
    config_path = os.path.expanduser(args.config_path)

    if os.path.exists(config_path):
        print(
            f"A configuration already exists at {config_path}. Please back it up and remove it, or choose another path."
        )
        sys.exit(1)

    if not sys.__stdin__.isatty():
        # Non-interactive invocation
        installation_metrics_enabled = not args.disable_installation_metrics
    elif args.disable_installation_metrics is True:
        installation_metrics_enabled = False
    else:
        # Prompt user
        installation_metrics_enabled = None
        while installation_metrics_enabled is None:
            response = input(
                "Nautobot would like to send anonymized installation metrics to the project's maintainers.\n"
                "These metrics include the installed Nautobot version, the Python version in use, an anonymous\n"
                '"deployment ID", and a list of one-way-hashed names of enabled Nautobot Apps and their versions.\n'
                "Allow Nautobot to send these metrics? [y/n]: "
            )
            try:
                installation_metrics_enabled = is_truthy(response)
            except ValueError:
                print("Please enter 'y' or 'n'.")

    if installation_metrics_enabled:
        print("Installation metrics will be sent when running 'nautobot-server post_upgrade'. Thank you!")
    else:
        print("Installation metrics will not be sent by default.")

    # Create the config
    context = {
        "installation_metrics_enabled": installation_metrics_enabled,
        "secret_key": get_random_secret_key(),
    }
    environment = Environment(loader=BaseLoader, keep_trailing_newline=True, autoescape=True)
    with open(CONFIG_TEMPLATE) as fh:
        template = environment.from_string(fh.read())
    config = template.render(**context)

    dirname = os.path.dirname(config_path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(config_path, "w") as fh:
        fh.write(config)

    print(f"Configuration file created at {config_path}")


def get_config_path():
    """Get the default Nautobot config file path based on the NAUTOBOT_CONFIG or NAUTOBOT_ROOT environment variables."""
    return os.getenv(
        "NAUTOBOT_CONFIG",
        os.path.join(
            os.getenv("NAUTOBOT_ROOT", os.path.expanduser("~/.nautobot")),
            "nautobot_config.py",
        ),
    )


def main():
    """Run administrative tasks."""
    # Point Django to our 'nautobot_config' pseudo-module that we'll load from the provided config path
    os.environ["DJANGO_SETTINGS_MODULE"] = "nautobot_config"

    default_config_path = get_config_path()

    # Intercept certain CLI parameters and arguments before they reach Django
    parser = CommandParser(
        description=DESCRIPTION,
        usage=USAGE,
        formatter_class=_VerboseHelpFormatter,
    )
    parser.add_argument(
        "-c", "--config-path", default=default_config_path, help="Path to the Nautobot configuration file"
    )
    parser.add_argument("--version", action=_VersionAction, help="Show version numbers and exit")

    # Parse out the `--config` argument here and capture the rest of the CLI args
    args, unparsed_args = parser.parse_known_args()

    # `nautobot-server init` needs to be handled here, rather than as a Django management subcommand,
    # because Django commands need the settings to already exist and be valid, which we don't have yet at this point!
    # We also handle `nautobot-server version` just so it's consistent with `nautobot-server --version`.
    # We do *not* handle `nautobot-server help` as that will still let the user access the Django help,
    # versus `nautobot-server --help` which only shows the help for `nautobot-server` itself.
    subparsers = parser.add_subparsers(
        dest="subcommand", help="Subcommand to execute", metavar="SUBCOMMAND", required=False
    )

    init_parser = subparsers.add_parser("init", help="Initialize a new Nautobot configuration file")
    init_parser.add_argument(
        "--disable-installation-metrics",
        action="store_true",
        help="Disable sending of anonymized installation metrics for this configuration",
    )
    init_parser.add_argument("config_path", default=None, nargs="?", help="Path to write generated configuration file")
    version_parser = subparsers.add_parser("version", help="Show version numbers and exit")

    try:
        # Handle the special 'init' and 'version' subcommands
        subcommand_and_args = parser.parse_args(unparsed_args)

        if subcommand_and_args.subcommand == "init":
            # Support both "nautobot-server init CONFIG_PATH" and "nautobot-server --config-path CONFIG_PATH init"
            # In the (gross) case of "nautobot-server --config-path PATH_A init PATH_B", PATH_B will win out
            if not subcommand_and_args.config_path:
                subcommand_and_args.config_path = args.config_path
            _init_settings(subcommand_and_args)
        elif subcommand_and_args.subcommand == "version":
            subcommand_and_args.config_path = args.config_path
            _VersionAction(["version"], None)(version_parser, subcommand_and_args, [], "version")
        else:  # No subcommand specified
            parser.print_help()
        parser.exit(0)

    except CommandError as err:
        # Other Django subcommands will be reported as "invalid choice" since all our parser knows are `init`/`version`
        if "invalid choice" not in str(err):
            raise

    # If we get here, it's a regular Django management command - so load in the nautobot_config.py then hand off
    load_settings(args.config_path)
    execute_from_command_line([sys.argv[0], *unparsed_args])


if __name__ == "__main__":
    main()
