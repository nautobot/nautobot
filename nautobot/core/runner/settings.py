"""
logan.settings
~~~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see NOTICE for more details.
"""

from __future__ import absolute_import

try:
    unicode
except NameError:
    basestring = unicode = str  # Python 3

try:
    execfile
except NameError:  # Python3

    def execfile(afile, globalz=None, localz=None):
        with open(afile, "r") as fh:
            exec(fh.read(), globalz, localz)


import errno
import imp
import os
import sys
from django.conf import settings as django_settings

__all__ = ("create_default_settings", "load_settings")

TUPLE_SETTINGS = ("INSTALLED_APPS", "TEMPLATE_DIRS")


def create_default_settings(filepath, settings_initializer):
    if settings_initializer is not None:
        output = settings_initializer()
    else:
        output = ""

    dirname = os.path.dirname(filepath)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(filepath, "w") as fp:
        fp.write(output)


def create_module(name, install=True):
    mod = imp.new_module(name)
    if install:
        sys.modules[name] = mod
    return mod


def load_settings(mod_or_filename, silent=False, allow_extras=True, settings=django_settings):
    if isinstance(mod_or_filename, basestring):
        conf = create_module("temp_config", install=False)
        conf.__file__ = mod_or_filename
        try:
            execfile(mod_or_filename, conf.__dict__)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return settings
            e.strerror = "Unable to load configuration file (%s)" % e.strerror
            raise
    else:
        conf = mod_or_filename

    add_settings(conf, allow_extras=allow_extras, settings=settings)


def add_settings(mod, allow_extras=True, settings=django_settings):
    """
    Adds all settings that are part of ``mod`` to the global settings object.

    Special cases ``EXTRA_APPS`` to append the specified applications to the
    list of ``INSTALLED_APPS``.
    """
    extras = {}

    for setting in dir(mod):
        if setting == setting.upper():
            setting_value = getattr(mod, setting)
            if setting in TUPLE_SETTINGS and type(setting_value) == str:
                setting_value = (setting_value,)  # In case the user forgot the comma.

            # Any setting that starts with EXTRA_ and matches a setting that is a list or tuple
            # will automatically append the values to the current setting.
            # It might make sense to make this less magical
            if setting.startswith("EXTRA_"):
                base_setting = setting.split("EXTRA_", 1)[-1]
                if isinstance(getattr(settings, base_setting), (list, tuple)):
                    extras[base_setting] = setting_value
                    continue

            setattr(settings, setting, setting_value)

    for key, value in extras.items():
        curval = getattr(settings, key)
        setattr(settings, key, curval + type(curval)(value))
