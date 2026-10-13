"""Timeout-bounded regular expression matching.

Nautobot matches operator-supplied patterns, such as `CustomField.validation_regex`, against
arbitrary user-supplied data on the request path. Python's standard `re` module offers no way to
bound backtracking, so a pattern that backtracks catastrophically consumes worker time without
limit when evaluated against a non-matching subject (ReDoS, CWE-1333). The third-party `regex`
module supports a per-call `timeout`, so every "stored pattern versus request data" match is routed
through this module.

Import the functions rather than the module (`from nautobot.core.utils.regex import regex_search`)
so that the name does not shadow the third-party `regex` package at the call site.
"""

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
import regex

logger = logging.getLogger(__name__)


class InvalidRegexError(ValidationError):
    """A stored regular expression could not be compiled, so the value under test is rejected."""


class RegexTimeoutError(ValidationError):
    """Matching exceeded the allowed time, so the value under test is rejected."""


def compile_regex(pattern):
    """Compile `pattern` with the `regex` module, which supports bounded matching.

    Args:
        pattern (str): The regular expression to compile.

    Returns:
        (regex.Pattern): The compiled pattern.

    Raises:
        InvalidRegexError: If `pattern` is not a valid regular expression.
    """
    try:
        return regex.compile(pattern)
    except (regex.error, TypeError, ValueError, RecursionError) as exc:
        raise InvalidRegexError(f"{pattern!r} is not a valid regular expression: {exc}", code="regex_invalid") from exc


def _bounded(operation, pattern, value, timeout):
    """Run `operation` with a time bound, translating an overrun into a `RegexTimeoutError`."""
    # Read here rather than bound as a default argument so that `override_settings` takes effect.
    timeout = settings.REGEX_TIMEOUT if timeout is None else timeout
    try:
        return operation(value, timeout=timeout)
    except TimeoutError as exc:
        # Logged as well as raised: the validation error reaches the user who submitted the value,
        # but it is the operator who has to find and fix the stored pattern.
        logger.error("Regular expression %r exceeded the %s second matching timeout and was aborted.", pattern, timeout)
        raise RegexTimeoutError(
            f"Matching against the regular expression {pattern!r} exceeded {timeout} second(s) and was aborted; "
            "the pattern may be subject to catastrophic backtracking. Please simplify the expression.",
            code="regex_timeout",
        ) from exc


def regex_search(pattern, value, *, timeout=None):
    """As `re.search()`, but abort the attempt after `timeout` seconds.

    Args:
        pattern (str): The regular expression to match with.
        value (str): The value to match against.
        timeout (float): Seconds to allow; defaults to the `REGEX_TIMEOUT` setting.

    Returns:
        (regex.Match): The match, or `None` if `value` does not match.

    Raises:
        InvalidRegexError: If `pattern` is not a valid regular expression.
        RegexTimeoutError: If matching did not complete within `timeout`.

    Both exceptions are `ValidationError` subclasses, so a caller that does not catch them fails
    closed: the value under test is rejected rather than silently accepted. Callers outside a
    validation context should catch them explicitly.
    """
    return _bounded(compile_regex(pattern).search, pattern, value, timeout)


def regex_match(pattern, value, *, timeout=None):
    """As `re.match()`, but abort the attempt after `timeout` seconds.

    See `regex_search()` for the arguments, return value and exceptions.
    """
    return _bounded(compile_regex(pattern).match, pattern, value, timeout)
