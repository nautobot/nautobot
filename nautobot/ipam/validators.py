from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator, RegexValidator
import netaddr


def ip_address_list_validator(values):
    """Validate a list of IPv4 or IPv6 addresses with optional masks."""
    for value in values:
        try:
            netaddr.IPNetwork(value)
        except (netaddr.AddrFormatError, ValueError) as error:
            raise ValidationError(
                "Enter a valid IPv4 or IPv6 address, optionally including a mask.", code="invalid"
            ) from error


def prefix_validator(prefix):
    if prefix.ip != prefix.cidr.ip:
        raise ValidationError(f"{prefix} is not a valid prefix. Did you mean {prefix.cidr}?")


class MaxPrefixLengthValidator(BaseValidator):
    message = "The prefix length must be less than or equal to %(limit_value)s."
    code = "max_prefix_length"

    def compare(self, a, b):
        return a.prefixlen > b


class MinPrefixLengthValidator(BaseValidator):
    message = "The prefix length must be greater than or equal to %(limit_value)s."
    code = "min_prefix_length"

    def compare(self, a, b):
        return a.prefixlen < b


DNSValidator = RegexValidator(
    regex="^[0-9A-Za-z._-]+$",
    message="Only alphanumeric characters, hyphens, periods, and underscores are allowed in DNS names",
    code="invalid",
)
