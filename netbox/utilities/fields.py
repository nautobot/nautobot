from django.db import models


class NullableCharField(models.CharField):
    description = "Stores empty values as NULL rather than ''"

    def to_python(self, value):
        if isinstance(value, models.CharField):
            return value
        return value or ''

    def get_prep_value(self, value):
        return value or None
