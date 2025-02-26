from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address, validate_ipv6_address
from django.db.models import Q
from netaddr import AddrFormatError, IPAddress, IPNetwork

from nautobot.core.forms.fields import MultiMatchModelMultipleChoiceField
from nautobot.core.utils.data import is_uuid

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
                raise ValidationError(f"Invalid IPv4/IPv6 address format: {value}")

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

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, IPNetwork):
            return value

        # Ensure that a subnet mask has been specified. This prevents IPs from defaulting to a /32 or /128.
        if len(value.split("/")) != 2:
            raise ValidationError("CIDR mask (e.g. /24) is required.")

        try:
            return IPNetwork(value)
        except AddrFormatError:
            raise ValidationError("Please specify a valid IPv4 or IPv6 address.")


class PrefixFilterFormField(MultiMatchModelMultipleChoiceField):
    @property
    def filter(self):
        from nautobot.ipam.filters import PrefixFilter  # avoid circular definition

        return PrefixFilter

    def _check_values(self, values):  # pylint: disable=arguments-renamed
        null_value_present = self.null_label is not None and values and self.null_value in values
        if null_value_present:
            values = [v for v in values if v != self.null_value]
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            values = frozenset(values)
        except TypeError:
            raise ValidationError(self.error_messages["invalid_list"], code="invalid_list")
        pk_values = set()
        prefix_queries = []
        for value in values:
            if is_uuid(value):
                pk_values.add(value)
                query = Q(pk=value)
            else:
                ipnetwork = IPNetwork(value)
                query = Q(
                    network=ipnetwork.network,
                    prefix_length=ipnetwork.prefixlen,
                    broadcast=ipnetwork.broadcast or ipnetwork[-1],
                )
                prefix_queries.append(query)
            if not self.queryset.filter(query).exists():
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": value},
                )
        aggregate_query = Q(pk__in=pk_values)
        for prefix_query in prefix_queries:
            aggregate_query |= prefix_query
        qs = self.queryset.filter(aggregate_query)
        result = list(qs)
        if null_value_present:
            result.append(self.null_value)
        return result
