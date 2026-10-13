import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import _lazy_re_compile, BaseValidator, RegexValidator, URLValidator

from nautobot.core.utils.regex import regex_search


class EnhancedURLValidator(URLValidator):
    """
    Extends Django's built-in URLValidator to permit the use of hostnames with no domain extension and enforce allowed
    schemes specified in the configuration.
    """

    fqdn_re = URLValidator.hostname_re + URLValidator.domain_re + URLValidator.tld_re
    host_res = [
        URLValidator.ipv4_re,
        URLValidator.ipv6_re,
        fqdn_re,
        URLValidator.hostname_re,
    ]
    regex = _lazy_re_compile(
        r"^(?:[a-z0-9\.\-\+]*)://"  # Scheme (enforced separately)
        r"(?:\S+(?::\S*)?@)?"  # HTTP basic authentication
        r"(?:" + "|".join(host_res) + ")"  # IPv4, IPv6, FQDN, or hostname
        r"(?::\d{2,5})?"  # Port number
        r"(?:[/?#][^\s]*)?"  # Path
        r"\Z",
        re.IGNORECASE,
    )

    schemes = settings.ALLOWED_URL_SCHEMES

    def __getattribute__(self, name):
        """Dynamically fetch schemes each time it's accessed."""
        if name == "schemes":
            self.schemes = settings.ALLOWED_URL_SCHEMES  # Always return the latest list
        return super().__getattribute__(name)


class ExclusionValidator(BaseValidator):
    """
    Ensure that a field's value is not equal to any of the specified values.
    """

    message = "This value may not be %(show_value)s."

    def compare(self, a, b):
        return a in b


class ValidRegexValidator(RegexValidator):
    """
    Checks that the value is a valid regular expression.

    Don't confuse this with `RegexValidator`, which *uses* a regex to validate a value.
    """

    message = "%(value)r is not a valid regular expression."
    code = "regex_invalid"

    def __call__(self, value):
        try:
            return re.compile(value)
        except (re.error, TypeError):
            raise ValidationError(self.message, code=self.code, params={"value": value})


class TimeLimitedRegexValidator(RegexValidator):
    """
    Drop-in replacement for Django's `RegexValidator` that bounds how long matching may run.

    Django's `RegexValidator` matches with a stdlib `re` pattern, which cannot be interrupted, so a
    pattern subject to catastrophic backtracking consumes worker time without limit. This subclass
    matches via `nautobot.core.utils.regex.regex_search()`, which aborts once the bound is exceeded
    and raises `RegexTimeoutError`, itself a `ValidationError`.
    """

    def __init__(self, regex=None, message=None, code=None, inverse_match=None, flags=None, timeout=None):
        if flags:
            # `re` and `regex` disagree on several flag integers (`re.ASCII` and `regex.V1` are both
            # 256), so a stdlib flag cannot be forwarded safely. Inline flags work as expected.
            raise ValueError(
                f"{type(self).__name__} does not support `flags`; use an inline flag such as `(?i)` in the pattern."
            )
        # Capture the pattern as a string before `super().__init__()` replaces `self.regex` with a
        # lazily compiled stdlib pattern object.
        pattern = self.regex if regex is None else regex
        self.pattern = getattr(pattern, "pattern", pattern)
        super().__init__(regex=regex, message=message, code=code, inverse_match=inverse_match, flags=flags)
        self.timeout = timeout

    def __call__(self, value):
        matched = regex_search(self.pattern, str(value), timeout=self.timeout)
        invalid_input = matched if self.inverse_match else not matched
        if invalid_input:
            raise ValidationError(self.message, code=self.code, params={"value": value})


validate_regex = ValidRegexValidator()
