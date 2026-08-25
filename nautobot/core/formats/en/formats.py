"""
Stub "localization" formats module to re-enable support for settings like DATE_FORMAT, etc. when l10n is in effect.
"""

from django.conf import settings

from nautobot.core.formats import PreferredTimeFormat

_TIME_FORMAT_SETTINGS = frozenset({"DATETIME_FORMAT", "SHORT_DATETIME_FORMAT", "TIME_FORMAT"})
_PREFERRED_LITERAL_FORMATS = frozenset({"Y-m-d H:i:s.u"})


def __getattr__(name):
    if name in _PREFERRED_LITERAL_FORMATS:
        return PreferredTimeFormat(name)

    value = getattr(settings, name)
    if name in _TIME_FORMAT_SETTINGS:
        return PreferredTimeFormat(value)
    return value
