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
        kwargs["max_length"] = 16
        super().__init__(**kwargs)

    def db_type(self, connection):
        engine = connection.settings_dict["ENGINE"]

        # Use 'bytea' type for Postgres.
        if "postgres" in engine:
            return super().db_type(connection)

        # Or 'varbinary' for everyone else.
        max_length = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        return "varbinary(%(max_length)s)" % max_length

    def value_to_string(self, obj):
        """IPField is serialized as str(IPAddress())"""
        value = self.value_from_object(obj)
        if not value:
            return value

        return str(self._parse_ip_address(value))

    def _parse_ip_address(self, value):
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
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, netaddr.IPAddress):
            return value

        if value is None:
            return value

        return str(self._parse_ip_address(value))

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return value

        # Parse the address and then pack it to binary
        value = self._parse_ip_address(value).packed

        # Use defaults for Postgres
        engine = connection.settings_dict["ENGINE"]
        if "postgres" in engine:
            return super().get_db_prep_value(value, connection, prepared)

        return value

    def form_class(self):
        return IPNetworkFormField

    def formfield(self, **kwargs):
        defaults = {"form_class": self.form_class()}
        defaults.update(kwargs)
        return super().formfield(**defaults)
