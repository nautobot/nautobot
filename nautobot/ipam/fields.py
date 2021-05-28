from django.core.exceptions import ValidationError
from django.db import models
from django.utils.datastructures import DictWrapper
import netaddr

from .formfields import IPNetworkFormField


class VarbinaryIPField(models.BinaryField):
    """
    IP network address
    """

    description = "IP network address"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
            value = int.from_bytes(value, "big")
        except TypeError:
            pass  # It's a string

        try:
            return netaddr.IPAddress(value)
        except netaddr.AddrFormatError:
            raise ValidationError("Invalid IP address format: {}".format(value))
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

    def formfield(self, **kwargs):
        defaults = {"form_class": self.form_class()}
        defaults.update(kwargs)
        return super().formfield(**defaults)
