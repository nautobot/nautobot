from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework.serializers import SerializerMethodField
from rest_framework.fields import CreateOnlyDefault, Field

from nautobot.core.api import ValidatedModelSerializer
from nautobot.extras.models import CustomField


#
# Custom fields
#


def should_use_custom_field_slug(request=None):
    if request is None:
        # Default behavior for backwards compatibility
        return False
    major_version, minor_version = request.version.split(".", 1)
    # Use slug for API versions 1.4 or greater
    use_slug = int(major_version) > 1 or int(minor_version) >= 4
    return use_slug


class CustomFieldDefaultValues:
    """
    Return a dictionary of all CustomFields assigned to the parent model and their default values.
    """

    requires_context = True

    def __call__(self, serializer_field):
        self.model = serializer_field.parent.Meta.model
        use_slug = should_use_custom_field_slug(serializer_field.context.get("request"))

        # Retrieve the CustomFields for the parent model
        content_type = ContentType.objects.get_for_model(self.model)
        fields = CustomField.objects.filter(content_types=content_type)

        # Populate the default value for each CustomField
        value = {}
        for field in fields:
            key = field.slug if use_slug else field.name
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
        if should_use_custom_field_slug(self.context.get("request")):
            # 1.4+ behavior
            # 2.0 TODO: #824 use cf.slug as lookup key instead of cf.name
            return {cf.slug: obj.get(cf.name) for cf in self._get_custom_fields()}
        else:
            # Legacy behavior
            return {cf.name: obj.get(cf.name) for cf in self._get_custom_fields()}

    def to_internal_value(self, data):
        """Support updates to individual fields on an existing instance without needing to provide the entire dict."""
        if should_use_custom_field_slug(self.context.get("request")):
            # Map slugs to names for the backend data
            # 2.0 TODO: #824 remove this translation
            new_data = {}
            custom_fields = CustomField.objects.filter(slug__in=data.keys())
            for cf in custom_fields.iterator():
                new_data[cf.name] = data[cf.slug]
            data = new_data

        # If updating an existing instance, start with existing _custom_field_data
        if self.parent.instance:
            data = {**self.parent.instance._custom_field_data, **data}

        return data


# TODO: should be CustomFieldModelSerializerMixin
class CustomFieldModelSerializer(ValidatedModelSerializer):
    """
    Extends ModelSerializer to render any CustomFields and their values associated with an object.
    """

    computed_fields = SerializerMethodField(read_only=True)
    custom_fields = CustomFieldsDataField(
        source="_custom_field_data",
        default=CreateOnlyDefault(CustomFieldDefaultValues()),
    )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_computed_fields(self, obj):
        return obj.get_computed_fields()

    def get_field_names(self, declared_fields, info):
        """Ensure that "custom_fields" and "computed_fields" are always included appropriately."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "custom_fields")
        self.extend_field_names(fields, "computed_fields", opt_in_only=True)
        return fields
