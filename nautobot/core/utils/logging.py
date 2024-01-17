"""Utilities for working with log messages and similar features."""

import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)


def sanitize(dirty, replacement="(redacted)"):
    """
    Make an attempt at stripping potentially-sensitive information from the given string, bytes or iterable thereof.

    Obviously this will never be 100% foolproof but we can at least try.

    Uses settings.SANITIZER_PATTERNS as the list of (regexp, repl) tuples to apply.
    """
    # Don't allow regex match groups to be referenced in the replacement string!
    if re.search(r"\\\d|\\g<\d+>", replacement):
        raise RuntimeError("Invalid replacement string! Must not contain regex match group references.")

    if isinstance(dirty, (list, tuple)):
        clean = []
        for item in dirty:
            if isinstance(item, (list, tuple, bytes, str)):
                clean.append(sanitize(item))
            else:
                # Pass through anything that isn't a string or iterable of strings
                clean.append(item)
        if isinstance(dirty, tuple):
            clean = tuple(clean)
        return clean

    if isinstance(dirty, bytes):
        return sanitize(dirty.decode("utf-8")).encode("utf-8")

    if isinstance(dirty, str):
        clean = dirty
        for sanitizer, repl in settings.SANITIZER_PATTERNS:
            try:
                clean = sanitizer.sub(repl.format(replacement=replacement), clean)
            except re.error:
                logger.error('Error in string sanitization using "%s"', sanitizer)

        return clean

    logger.warning("No sanitizer support for %s data", type(dirty))
    return dirty
