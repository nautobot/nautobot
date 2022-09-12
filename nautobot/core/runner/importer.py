"""
logan.importer
~~~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see LICENSE for more details.
"""

import sys

from importlib import import_module
from .settings import load_settings, create_module


def execfile(afile, globalz=None, localz=None):
    with open(afile, "r") as fh:
        exec(fh.read(), globalz, localz)


installed = False


def install(name, config_path, default_settings, **kwargs):
    """Install our custom module importer logic.

    Args:
      name (str): Module name to handle specially (e.g., "nautobot_config")
      config_path (str): Absolute path to the module in question (e.g., "/opt/nautobot/nautobot_config.py")
      default_settings (str): Settings module name to inherit settings from (e.g., "nautobot.core.settings")
    """
    global installed

    if installed:
        # TODO: reinstall
        return

    # Ensure that our custom importer for the config module takes precedence over standard Python import machinery
    sys.meta_path.insert(0, LoganImporter(name, config_path, default_settings, **kwargs))
    installed = True


class ConfigurationError(Exception):
    pass


class LoganImporter:
    """Implementation of importlib.abc.MetaPathFinder interface."""

    def __init__(self, name, config_path, default_settings=None, allow_extras=True, callback=None):
        """Instantiate the custom meta path finder.

        Args:
          name (str): Module name to handle specially (e.g., "nautobot_config")
          config_path (str): Absolute path to the module in question (e.g., "/opt/nautobot/nautobot_config.py")
          default_settings (str): Settings module name to inherit settings from (e.g., "nautobot.core.settings")
          allow_extras (bool): Whether to allow extension of settings variables via "EXTRA_<setting>" values
          callback (func): Callback function to invoke after loading the module into settings
        """
        self.name = name
        self.config_path = config_path
        self.default_settings = default_settings
        self.allow_extras = allow_extras
        self.callback = callback
        self.validate()

    def __repr__(self):
        return f"<{type(self)} for '{self.name}' ({self.config_path})>"

    def validate(self):
        # TODO(dcramer): is there a better way to handle validation so it
        # is lazy and actually happens in LoganLoader?
        try:
            execfile(self.config_path, {"__file__": self.config_path})
        except Exception as e:
            exc_info = sys.exc_info()
            raise ConfigurationError(str(e), exc_info[2])

    def find_module(self, fullname, path=None):
        """Meta path finder API function implementation.

        Ref: https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_module

        TODO: find_module() API is deprecated, convert this to find_spec() instead.
        """
        # Only find/load the module matching self.name - otherwise let the standard Python import machinery handle it
        if fullname != self.name:
            return None

        return LoganLoader(
            name=self.name,
            config_path=self.config_path,
            default_settings=self.default_settings,
            allow_extras=self.allow_extras,
            callback=self.callback,
        )


class LoganLoader:
    """Implementation of importlib.abc.Loader interface."""

    def __init__(self, name, config_path, default_settings=None, allow_extras=True, callback=None):
        self.name = name
        self.config_path = config_path
        self.default_settings = default_settings
        self.allow_extras = allow_extras
        self.callback = callback

    def load_module(self, fullname):
        """Loader API function implementation.

        TODO: load_module() API is deprecated, convert this to create_module()/exec_module() instead.
        """
        try:
            return self._load_module(fullname)
        except Exception as e:
            exc_info = sys.exc_info()
            raise ConfigurationError(str(e), exc_info[2])

    def _load_module(self, fullname):
        # TODO: is this needed?
        if fullname in sys.modules:
            return sys.modules[fullname]  # pragma: no cover

        if self.default_settings:
            default_settings_mod = import_module(self.default_settings)
        else:
            default_settings_mod = None

        settings_mod = create_module(self.name)

        # Django doesn't play too nice without the config file living as a real file, so let's fake it.
        settings_mod.__file__ = self.config_path

        # install the default settings for this app
        load_settings(default_settings_mod, allow_extras=self.allow_extras, settings=settings_mod)

        # install the custom settings for this app
        load_settings(self.config_path, allow_extras=self.allow_extras, settings=settings_mod)

        if self.callback:
            self.callback(settings_mod)

        return settings_mod
