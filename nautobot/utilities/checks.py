import re

from django.conf import settings
from django.core.checks import register, Error, Tags


@register(Tags.security)
def check_sanitizer_patterns(app_configs, **kwargs):
    errors = []
    for entry in settings.SANITIZER_PATTERNS:
        if (
            not isinstance(entry, (tuple, list))
            or len(entry) != 2
            or not isinstance(entry[0], re.Pattern)
            or not isinstance(entry[1], str)
        ):
            errors.append(
                Error(
                    "Invalid entry in settings.SANITIZER_PATTERNS",
                    hint="Each entry must be a list or tuple of (compiled regexp, replacement string)",
                    obj=entry,
                    id="nautobot.utilities.E001",
                )
            )
            continue

        sanitizer, repl = entry
        try:
            sanitizer.sub(repl.format(replacement="(REDACTED)"), "Hello world!")
        except re.error as exc:
            errors.append(
                Error(
                    "Entry in settings.SANITIZER_PATTERNS not usable for sanitization",
                    hint=str(exc),
                    obj=entry,
                    id="nautobot.utilities.E002",
                )
            )

    return errors
