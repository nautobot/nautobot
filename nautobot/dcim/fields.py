from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from netaddr import AddrFormatError, EUI, mac_unix_expanded

from nautobot.ipam.constants import BGP_ASN_MAX, BGP_ASN_MIN
from nautobot.utilities.deprecation import class_deprecated_in_favor_of
from nautobot.utilities.fields import JSONArrayField
from .lookups import PathContains


class ASNField(models.BigIntegerField):
    description = "32-bit ASN field"
    default_validators = [
        MinValueValidator(BGP_ASN_MIN),
        MaxValueValidator(BGP_ASN_MAX),
    ]

    def formfield(self, **kwargs):
        defaults = {
            "min_value": BGP_ASN_MIN,
            "max_value": BGP_ASN_MAX,
        }
        defaults.update(**kwargs)
        return super().formfield(**defaults)


class mac_unix_expanded_uppercase(mac_unix_expanded):
    word_fmt = "%.2X"


class MACAddressCharField(models.CharField):
    description = "MAC Address Varchar field"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 18
        super().__init__(*args, **kwargs)
        for validator in list(self.validators):
            # CharField will automatically add a MaxLengthValidator, but that doesn't work with EUI objects
            if isinstance(validator, MaxLengthValidator):
                self.validators.remove(validator)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def python_type(self):
        return EUI

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = value.strip()
        try:
            return EUI(value, version=48, dialect=mac_unix_expanded_uppercase)
        except AddrFormatError:
            raise ValidationError(f"Invalid MAC address format: {value}")

    def get_prep_value(self, value):
        if not value:
            return None
        return str(self.to_python(value))


# 2.0 TODO: remove this class, it's unused in core and plugins shouldn't be using it in their models
@class_deprecated_in_favor_of(MACAddressCharField)
class MACAddressField(models.Field):
    description = "PostgreSQL-only MAC Address field"

    def python_type(self):
        return EUI

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return value
        try:
            return EUI(value, version=48, dialect=mac_unix_expanded_uppercase)
        except AddrFormatError:
            raise ValidationError(f"Invalid MAC address format: {value}")

    def db_type(self, connection):
        return "macaddr"

    def get_prep_value(self, value):
        if not value:
            return None
        return str(self.to_python(value))


class JSONPathField(JSONArrayField):
    """
    An ArrayField which holds a set of objects, each identified by a (type, ID) tuple.
    """

    def __init__(self, **kwargs):
        kwargs["base_field"] = models.CharField(max_length=40)
        super().__init__(**kwargs)


JSONPathField.register_lookup(PathContains)
