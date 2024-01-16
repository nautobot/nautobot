"""Utilities for working with log messages and similar features."""

import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)


def sanitize(string, replacement="(redacted)"):
    """
    Make an attempt at stripping potentially-sensitive information from the given string or iterable of strings.

    Obviously this will never be 100% foolproof but we can at least try.

    Uses settings.SANITIZER_PATTERNS as the list of (regexp, repl) tuples to apply.
    """
    if isinstance(string, (list, tuple)):
        new_string = []
        for item in string:
            if isinstance(item, (list, tuple, bytes, str)):
                new_string.append(sanitize(item))
            else:
                # Pass through anything that isn't a string or iterable of strings
                new_string.append(item)
        if isinstance(string, tuple):
            new_string = tuple(string)
        return new_string

    if isinstance(string, bytes):
        return sanitize(string.decode("utf-8")).encode("utf-8")

    if isinstance(string, str):
        # Don't allow regex match groups to be referenced in the replacement string!
        if re.search(r"\\\d|\\g<\d+>", replacement):
            raise RuntimeError("Invalid replacement string! Must not contain regex match group references.")

        for sanitizer, repl in settings.SANITIZER_PATTERNS:
            try:
                string = sanitizer.sub(repl.format(replacement=replacement), string)
            except re.error:
                logger.error('Error in string sanitization using "%s"', sanitizer)

    return string
