from django.contrib.contenttypes.models import ContentType
from rest_framework.serializers import SerializerMethodField
from rest_framework.fields import CreateOnlyDefault, Field

from nautobot.core.api import ValidatedModelSerializer
from nautobot.extras.api.nested_serializers import NestedCustomFieldSerializer
from nautobot.extras.choices import *
from nautobot.extras.models import CustomField, CustomFieldChoice


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
            if field.default is not None:
                value[field.name] = field.default
            else:
                value[field.name] = None

        return value


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
        return {cf.name: obj.get(cf.name) for cf in self._get_custom_fields()}

    def to_internal_value(self, data):
        # If updating an existing instance, start with existing _custom_field_data
        if self.parent.instance:
            data = {**self.parent.instance._custom_field_data, **data}

        return data


class CustomFieldModelSerializer(ValidatedModelSerializer):
    """
    Extends ModelSerializer to render any CustomFields and their values associated with an object.
    """

    computed_fields = SerializerMethodField(read_only=True)
    custom_fields = CustomFieldsDataField(
        source="_custom_field_data",
        default=CreateOnlyDefault(CustomFieldDefaultValues()),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance is not None:

            # Retrieve the set of CustomFields which apply to this type of object
            content_type = ContentType.objects.get_for_model(self.Meta.model)
            fields = CustomField.objects.filter(content_types=content_type)

            # Populate CustomFieldValues for each instance from database
            if type(self.instance) in (list, tuple):
                for obj in self.instance:
                    self._populate_custom_fields(obj, fields)
            else:
                self._populate_custom_fields(self.instance, fields)

    def _populate_custom_fields(self, instance, custom_fields):
        instance.custom_fields = {}
        for field in custom_fields:
            instance.custom_fields[field.name] = instance.cf.get(field.name)

    def get_computed_fields(self, obj):
        return obj.get_computed_fields()
