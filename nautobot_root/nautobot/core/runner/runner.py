"""
logan.runner
~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see NOTICE for more details.
"""

from __future__ import absolute_import, print_function

from django.core import management
import optparse
import os
import re
import sys

from . import importer
from .settings import create_default_settings


try:
    raw_input
except NameError:  # PYthon 3
    raw_input = input


__configured = False


def sanitize_name(project):
    project = project.replace(' ', '-')
    return re.sub('[^A-Z0-9a-z_-]', '-', project)


def parse_args(args):
    """
    This parses the arguments and returns a tuple containing:

    (args, command, command_args)

    For example, "--config=bar start --with=baz" would return:

    (['--config=bar'], 'start', ['--with=baz'])
    """
    index = None
    for arg_i, arg in enumerate(args):
        if not arg.startswith('-'):
            index = arg_i
            break

    # Unable to parse any arguments
    if index is None:
        return (args, None, [])

    return (args[:index], args[index], args[(index + 1):])


def is_configured():
    global __configured
    return __configured


def configure_app(config_path=None, project=None, default_config_path=None,
                  default_settings=None, settings_initializer=None,
                  settings_envvar=None, initializer=None, allow_extras=True,
                  config_module_name=None, runner_name=None, on_configure=None):
    """
    :param project: should represent the canonical name for the project, generally
        the same name it assigned in distutils.
    :param default_config_path: the default location for the configuration file.
    :param default_settings: default settings to load (think inheritence).
    :param settings_initializer: a callback function which should return a string
        representing the default settings template to generate.
    :param initializer: a callback function which will be executed before the command
        is executed. It is passed a dictionary of various configuration attributes.
    """
    global __configured

    project_filename = sanitize_name(project)

    if default_config_path is None:
        default_config_path = '~/%s/%s.conf.py' % (project_filename, project_filename)

    if settings_envvar is None:
        settings_envvar = project_filename.upper() + '_CONF'

    if config_module_name is None:
        config_module_name = project_filename + '_config'

    # normalize path
    if settings_envvar in os.environ:
        default_config_path = os.environ.get(settings_envvar)
    else:
        default_config_path = os.path.normpath(os.path.abspath(os.path.expanduser(default_config_path)))

    if not config_path:
        config_path = default_config_path

    config_path = os.path.expanduser(config_path)

    if not os.path.exists(config_path):
        if runner_name:
            raise ValueError("Configuration file does not exist. Use '%s init' to initialize the file." % (runner_name,))
        raise ValueError("Configuration file does not exist at %r" % (config_path,))

    os.environ['DJANGO_SETTINGS_MODULE'] = config_module_name

    def settings_callback(settings):
        if initializer is None:
            return

        try:
            initializer({
                'project': project,
                'config_path': config_path,
                'settings': settings,
            })
        except Exception:
            # XXX: Django doesn't like various errors in this path
            import sys
            import traceback
            traceback.print_exc()
            sys.exit(1)

    importer.install(
        config_module_name, config_path, default_settings,
        allow_extras=allow_extras, callback=settings_callback)

    __configured = True

    # HACK(dcramer): we need to force access of django.conf.settings to
    # ensure we don't hit any import-driven recursive behavior
    from django.conf import settings
    hasattr(settings, 'INSTALLED_APPS')

    if on_configure:
        on_configure({
            'project': project,
            'config_path': config_path,
            'settings': settings,
        })


def run_app(**kwargs):
    sys_args = sys.argv

    # The established command for running this program
    runner_name = os.path.basename(sys_args[0])

    args, command, command_args = parse_args(sys_args[1:])

    if not command:
        print("usage: %s [--config=/path/to/settings.py] [command] [options]" % runner_name)
        sys.exit(1)

    default_config_path = kwargs.get('default_config_path')

    parser = optparse.OptionParser()

    # The ``init`` command is reserved for initializing configuration
    if command == 'init':
        (options, opt_args) = parser.parse_args()

        settings_initializer = kwargs.get('settings_initializer')

        config_path = os.path.expanduser(' '.join(opt_args[1:]) or default_config_path)

        if os.path.exists(config_path):
            resp = None
            while resp not in ('Y', 'n'):
                resp = raw_input('File already exists at %r, overwrite? [nY] ' % config_path)
                if resp == 'n':
                    print("Aborted!")
                    return

        try:
            create_default_settings(config_path, settings_initializer)
        except OSError as e:
            raise e.__class__('Unable to write default settings file to %r' % config_path)

        print("Configuration file created at %r" % config_path)

        return

    parser.add_option('--config', metavar='CONFIG')

    (options, logan_args) = parser.parse_args(args)

    config_path = options.config

    configure_app(config_path=config_path, **kwargs)

    management.execute_from_command_line([runner_name, command] + command_args)

    sys.exit(0)


if __name__ == '__main__':
    run_app()
