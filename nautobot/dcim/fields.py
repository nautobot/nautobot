from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from nautobot.core.models.fields import JSONArrayField
from nautobot.ipam.constants import BGP_ASN_MAX, BGP_ASN_MIN
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


class JSONPathField(JSONArrayField):
    """
    An ArrayField which holds a set of objects, each identified by a (type, ID) tuple.
    """

    def __init__(self, **kwargs):
        kwargs["base_field"] = models.CharField(max_length=40)
        super().__init__(**kwargs)


JSONPathField.register_lookup(PathContains)
