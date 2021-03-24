from django.core.exceptions import ValidationError
from django.db import models
from django.utils.datastructures import DictWrapper
from netaddr import AddrFormatError, IPNetwork, IPAddress

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
        try:
            value = int.from_bytes(value, "big")
            return str(IPAddress(value))
        except AddrFormatError:
            raise ValidationError("Invalid IP address format: {}".format(value))
        except (TypeError, ValueError) as e:
            raise ValidationError(e)

    def form_class(self):
        return IPNetworkFormField

    def formfield(self, **kwargs):
        defaults = {"form_class": self.form_class()}
        defaults.update(kwargs)
        return super().formfield(**defaults)
