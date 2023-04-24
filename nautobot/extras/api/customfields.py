from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import Field

from nautobot.extras.models import CustomField


#
# Custom fields
#


class CustomFieldDefaultValues:
    """
    Return a dictionary of all CustomFields assigned to the parent model and their default values.
    """

    requires_context = True

    def __call__(self, serializer_field):
        self.model = serializer_field.parent.Meta.model

        # Retrieve the CustomFields for the parent model
        content_type = ContentType.objects.get_for_model(self.model)
        fields = CustomField.objects.filter(content_types=content_type)

        # Populate the default value for each CustomField
        value = {}
        for field in fields:
            key = field.key
            if field.default is not None:
                value[key] = field.default
            else:
                value[key] = None

        return value


@extend_schema_field(OpenApiTypes.OBJECT)
class CustomFieldsDataField(Field):
    def _get_custom_fields(self):
        """
        Cache CustomFields assigned to this model to avoid redundant database queries
        """
        if not hasattr(self, "_custom_fields"):
            content_type = ContentType.objects.get_for_model(self.parent.Meta.model)
            self._custom_fields = CustomField.objects.filter(content_types=content_type)
        return self._custom_fields

    def to_representation(self, obj):
        return {cf.key: obj.get(cf.key) for cf in self._get_custom_fields()}

    def to_internal_value(self, data):
        """Support updates to individual fields on an existing instance without needing to provide the entire dict."""

        # If updating an existing instance, start with existing _custom_field_data
        if self.parent.instance:
            data = {**self.parent.instance._custom_field_data, **data}

        return data
