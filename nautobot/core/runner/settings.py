"""
logan.settings
~~~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see NOTICE for more details.
"""

import importlib.machinery
import importlib.util
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
    spec = importlib.machinery.ModuleSpec(name, None)
    mod = importlib.util.module_from_spec(spec)
    if install:
        sys.modules[name] = mod
    return mod


def load_settings(mod_or_filename, silent=False, allow_extras=True, settings=django_settings):
    if isinstance(mod_or_filename, str):
        spec = importlib.util.spec_from_file_location("temp_config", mod_or_filename)
        conf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conf)
    else:
        conf = mod_or_filename

    return add_settings(conf, allow_extras=allow_extras, settings=settings)


def add_settings(mod, allow_extras=True, settings=django_settings):
    """
    Adds all settings that are part of ``mod`` to the global settings object.

    Special cases ``EXTRA_{settings name}`` to append the specified applications to the
    list of ``{settings name}``.  For example, ``EXTRA_INSTALLED_APPS`` will be appended to the list
    of ``INSTALLED_APPS``.
    """
    extras = {}

    for setting in dir(mod):
        if setting == setting.upper():
            setting_value = getattr(mod, setting)
            if setting in TUPLE_SETTINGS and isinstance(setting_value, str):
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
