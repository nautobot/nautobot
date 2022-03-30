from drf_yasg.inspectors import (
    FieldInspector,
    NotHandled,
)

from nautobot.core.api import (
    SerializedPKRelatedField,
)


class SerializedPKRelatedFieldInspector(FieldInspector):
    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)
        if isinstance(field, SerializedPKRelatedField):
            return self.probe_field_inspectors(field.serializer(), ChildSwaggerType, use_references)

        return NotHandled
