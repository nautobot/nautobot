from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address, validate_ipv6_address
from netaddr import IPAddress, IPNetwork, AddrFormatError


#
# Form fields
#


class IPAddressFormField(forms.CharField):
    default_error_messages = {
        "invalid": "Enter a valid IPv4 or IPv6 address (without a mask).",
    }

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, IPAddress):
            return value

        # netaddr is a bit too liberal with what it accepts as a valid IP address. For example, '1.2.3' will become
        # IPAddress('1.2.0.3'). Here, we employ Django's built-in IPv4 and IPv6 address validators as a sanity check.
        try:
            validate_ipv4_address(value)
        except ValidationError:
            try:
                validate_ipv6_address(value)
            except ValidationError:
                raise ValidationError("Invalid IPv4/IPv6 address format: {}".format(value))

        try:
            return IPAddress(value)
        except ValueError:
            raise ValidationError("This field requires an IP address without a mask.")
        except AddrFormatError:
            raise ValidationError("Please specify a valid IPv4 or IPv6 address.")


class IPNetworkFormField(forms.Field):
    default_error_messages = {
        "invalid": "Enter a valid IPv4 or IPv6 address (with CIDR mask).",
    }

    def __init__(self, allow_zero_prefix=True, *args, **kwargs):
        """Initialize any arguments that will be used for field validation.

        Args:
            allow_zero_prefix (bool, optional): Use for IPAddress validation to invalidate /0 CIDR masks. Defaults to True.
        """
        self.allow_zero_prefix = allow_zero_prefix
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, IPNetwork):
            return value

        # Ensure that a subnet mask has been specified. This prevents IPs from defaulting to a /32 or /128.
        if len(value.split("/")) != 2:
            raise ValidationError("CIDR mask (e.g. /24) is required.")

        try:
            address = IPNetwork(value)
        except AddrFormatError:
            raise ValidationError("Please specify a valid IPv4 or IPv6 address.")

        # If we're expecting an IPAddress, we set self.allow_zero_prefix to false
        # to validate that IP address does not have a 0 CIDR mask
        if not self.allow_zero_prefix and address.prefixlen == 0:
            raise ValidationError("Cannot create IP address with /0 mask.")

        return address
