"""
Stub "localization" formats module to re-enable support for settings like DATE_FORMAT, etc. when l10n is in effect.
"""

from django.conf import settings


def __getattr__(name):
    return getattr(settings, name)
