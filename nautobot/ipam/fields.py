from django.core.exceptions import ValidationError
from django.db import models
import netaddr

from .formfields import IPNetworkFormField
from . import lookups


class VarbinaryIPField(models.BinaryField):
    """
    IP network address
    """

    description = "IP network address"

    def db_type(self, connection):
        """Returns the correct field type for a given database vendor."""

        # Use 'bytea' type for PostgreSQL.
        if connection.vendor == "postgresql":
            return "bytea"

        # Or 'varbinary' for everyone else.
        return "varbinary(16)"

    def value_to_string(self, obj):
        """IPField is serialized as str(IPAddress())"""
        value = self.value_from_object(obj)
        if not value:
            return value

        return str(self._parse_address(value))

    def _parse_address(self, value):
        """
        Parse `str`, `bytes` (varbinary), or `netaddr.IPAddress to `netaddr.IPAddress`.
        """
        try:
            int_value = int.from_bytes(value, "big")
            # Distinguish between
            # \x00\x00\x00\x01 (IPv4 0.0.0.1) and
            # \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01 (IPv6 ::1), among other cases
            version = 4 if len(value) == 4 else 6
            value = int_value
        except TypeError:
            version = None  # It's a string, IP version should be self-evident

        try:
            return netaddr.IPAddress(value, version=version)
        except netaddr.AddrFormatError:
            raise ValidationError(f"Invalid IP address format: {value}")
        except (TypeError, ValueError) as e:
            raise ValidationError(e)

    def from_db_value(self, value, expression, connection):
        """Converts DB (varbinary) to Python (str)."""
        return self.to_python(value)

    def to_python(self, value):
        """Converts `value` to Python (str)."""
        if isinstance(value, netaddr.IPAddress):
            return str(value)

        if value is None:
            return value

        return str(self._parse_address(value))

    def get_db_prep_value(self, value, connection, prepared=False):
        """Converts Python (str) to DB (varbinary)."""
        if value is None:
            return value

        # Parse the address and then pack it to binary.
        value = self._parse_address(value).packed

        # Use defaults for PostgreSQL
        if connection.vendor == "postgresql":
            return super().get_db_prep_value(value, connection, prepared)

        return value

    def form_class(self):
        return IPNetworkFormField

    def formfield(self, *args, **kwargs):
        defaults = {"form_class": self.form_class()}
        defaults.update(kwargs)
        return super().formfield(*args, **defaults)


VarbinaryIPField.register_lookup(lookups.IExact)
VarbinaryIPField.register_lookup(lookups.EndsWith)
VarbinaryIPField.register_lookup(lookups.IEndsWith)
VarbinaryIPField.register_lookup(lookups.StartsWith)
VarbinaryIPField.register_lookup(lookups.IStartsWith)
VarbinaryIPField.register_lookup(lookups.Regex)
VarbinaryIPField.register_lookup(lookups.IRegex)
VarbinaryIPField.register_lookup(lookups.NetContained)
VarbinaryIPField.register_lookup(lookups.NetContainedOrEqual)
VarbinaryIPField.register_lookup(lookups.NetContains)
VarbinaryIPField.register_lookup(lookups.NetContainsOrEquals)
VarbinaryIPField.register_lookup(lookups.NetEquals)
VarbinaryIPField.register_lookup(lookups.NetHost)
VarbinaryIPField.register_lookup(lookups.NetIn)
VarbinaryIPField.register_lookup(lookups.NetHostContained)
VarbinaryIPField.register_lookup(lookups.NetFamily)
