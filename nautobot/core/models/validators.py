import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import _lazy_re_compile, BaseValidator, RegexValidator, URLValidator


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


validate_regex = ValidRegexValidator()
