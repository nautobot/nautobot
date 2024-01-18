"""Utilities for working with log messages and similar features."""

import logging
import re

from django.conf import settings
import nh3

from nautobot.utilities import constants


logger = logging.getLogger(__name__)


def sanitize(string, replacement="(redacted)"):
    """
    Make an attempt at stripping potentially-sensitive information from the given string.

    Obviously this will never be 100% foolproof but we can at least try.

    Uses settings.SANITIZER_PATTERNS as the list of (regexp, repl) tuples to apply.
    """
    # Don't allow regex match groups to be referenced in the replacement string!
    assert not re.search(r"\\\d|\\g<\d+>", replacement)

    for sanitizer, repl in settings.SANITIZER_PATTERNS:
        try:
            string = sanitizer.sub(repl.format(replacement=replacement), string)
        except re.error:
            logger.error('Error in string sanitization using "%s"', sanitizer)

    return string


def clean_html(html):
    """Use nh3/ammonia to strip out all HTML tags and attributes except those explicitly permitted."""
    return nh3.clean(
        html,
        tags=constants.HTML_ALLOWED_TAGS,
        attributes=constants.HTML_ALLOWED_ATTRIBUTES,
        url_schemes=set(settings.ALLOWED_URL_SCHEMES),
    )
