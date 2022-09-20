"""
logan.runner
~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see NOTICE for more details.
"""

import argparse
import os
import re
import sys

from django.core import management

from nautobot import __version__
from . import importer
from .settings import create_default_settings


__configured = False


def sanitize_name(project):
    project = project.replace(" ", "-")
    return re.sub("[^A-Z0-9a-z_-]", "-", project)


def parse_command_args(args):
    """
    This parses the arguments and returns a tuple containing:

    (args, command, command_args)

    For example, "--config=bar start --with=baz" would return:

    (['--config=bar'], 'start', ['--with=baz'])
    """
    index = None
    for arg_i, arg in enumerate(args):
        if not arg.startswith("-"):
            index = arg_i
            break

    # Unable to parse any arguments
    if index is None:
        return (args, None, [])

    return (args[:index], args[index], args[(index + 1) :])


def is_configured():
    global __configured
    return __configured


def configure_app(
    config_path=None,
    project=None,
    default_config_path=None,
    default_settings=None,
    settings_initializer=None,
    settings_envvar=None,
    initializer=None,
    allow_extras=True,
    config_module_name=None,
    runner_name=None,
    on_configure=None,
):
    """
    :param project: should represent the canonical name for the project, generally
        the same name it assigned in distutils.
    :param default_config_path: the default location for the configuration file.
    :param default_settings: default settings to load (think inheritance).
    :param settings_initializer: a callback function which should return a string
        representing the default settings template to generate.
    :param initializer: a callback function which will be executed before the command
        is executed. It is passed a dictionary of various configuration attributes.
    """
    global __configured

    project_filename = sanitize_name(project)

    if default_config_path is None:
        default_config_path = f"~/{project_filename}/{project_filename}.conf.py"

    if settings_envvar is None:
        settings_envvar = project_filename.upper() + "_CONF"

    if config_module_name is None:
        config_module_name = project_filename + "_config"

    # normalize path
    if settings_envvar in os.environ:
        default_config_path = os.getenv(settings_envvar)
    else:
        default_config_path = os.path.normpath(os.path.abspath(os.path.expanduser(default_config_path)))

    if not config_path:
        config_path = default_config_path

    config_path = os.path.expanduser(config_path)

    if not os.path.exists(config_path):
        if runner_name:
            raise ValueError(f"Configuration file does not exist. Use '{runner_name} init' to initialize the file.")
        raise ValueError(f"Configuration file does not exist at {config_path}")

    os.environ["DJANGO_SETTINGS_MODULE"] = config_module_name

    def settings_callback(settings):
        if initializer is None:
            return

        try:
            initializer(
                {
                    "project": project,
                    "config_path": config_path,
                    "settings": settings,
                }
            )
        except Exception:
            # XXX: Django doesn't like various errors in this path
            import traceback

            traceback.print_exc()
            sys.exit(1)

    importer.install(
        config_module_name,
        config_path,
        default_settings,
        allow_extras=allow_extras,
        callback=settings_callback,
    )

    __configured = True

    # HACK(dcramer): we need to force access of django.conf.settings to
    # ensure we don't hit any import-driven recursive behavior
    from django.conf import settings

    hasattr(settings, "INSTALLED_APPS")

    if on_configure:
        on_configure(
            {
                "project": project,
                "config_path": config_path,
                "settings": settings,
            }
        )


class VerboseHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Argparse Formatter that includes newlines and shows argument defaults."""


def run_app(**kwargs):
    sys_args = sys.argv

    # The established command for running this program
    runner_name = os.path.basename(sys_args[0])

    default_config_path = kwargs.get("default_config_path")

    # Primary parser
    parser = management.CommandParser(
        description=kwargs.pop("description"),
        formatter_class=VerboseHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="CONFIG",
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )

    # This block of code here is done in this way because of the built in Django
    # management command parsing not playing well unless you have a Django
    # config with SECRET_KEY defined.

    # Parse out `--config` here first capturing any unparsed args for passing to
    # Django parser.
    args, unparsed_args = parser.parse_known_args()

    # Now add the sub-parser for "init" command
    subparsers = parser.add_subparsers(help=False, dest="command", metavar="")
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new configuration",
    )
    init_parser.add_argument(
        "config_path",
        default=default_config_path,
        nargs="?",
        help="Path to output generated configuration file",
    )

    # Try to use our parser first, to process custom arguments
    try:
        args = parser.parse_args()
        command = args.command
        command_args = sys.argv[1:]

    # Fallback to passing through to Django management commands
    # except RuntimeError as err:
    except management.CommandError as err:
        if "invalid choice" not in str(err):
            raise

        # Rewrite sys_args to have the unparsed args (if any)
        sys_args = sys_args[:1] + unparsed_args
        _, command, command_args = parse_command_args(sys_args[1:])

    # If we don't get a command of some sort, print help and exit dirty
    if not command:
        parser.print_help()
        parser.exit(1)

    # The `init` command is reserved for initializing configuration
    if command == "init":
        settings_initializer = kwargs.get("settings_initializer")

        config_path = os.path.expanduser(args.config_path)

        # Check if the config already exists; alert user and exit if exists.
        if os.path.exists(config_path):
            print(
                f"A configuration already exists at {config_path}. Please backup and remove it or choose another path."
            )
            return

        # Create the config
        try:
            create_default_settings(config_path, settings_initializer)
        except OSError as e:
            raise e.__class__(f"Unable to write default settings file to {config_path}")

        print(f"Configuration file created at {config_path}")

        return

    # Fetch config path from `--config` if provided, otherwise we want it to
    # default to None so that the underlying machinery in `configure_app` will
    # process default path or environment variable.
    config_path = args.config

    # Overlay our config w/ defaults
    try:
        configure_app(config_path=config_path, **kwargs)
    except ValueError as err:
        parser.exit(status=2, message=str(err) + "\n")

    # Call Django management command
    management.execute_from_command_line([runner_name, command] + command_args)

    # Exit cleanly
    sys.exit(0)


if __name__ == "__main__":
    run_app()
