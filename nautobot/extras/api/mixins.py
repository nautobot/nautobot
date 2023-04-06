import logging

from django.contrib.contenttypes.models import ContentType

from nautobot.core.api import (
    BaseModelSerializer,
    ContentTypeField,
)
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.extras.api.fields import RoleSerializerField
from nautobot.extras.utils import FeatureQuery

logger = logging.getLogger(__name__)


class RoleModelSerializerMixin(BaseModelSerializer):
    """Mixin to add `role` choice field to model serializers."""

    role = RoleSerializerField(required=False)


class StatusModelSerializerMixin(BaseModelSerializer):
    """Mixin to add `status` choice field to model serializers."""

    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("statuses").get_query()),
        required=False,
        many=True,
    )

    def get_field_names(self, declared_fields, info):
        """Ensure that "status" field is always present."""
        fields = list(super().get_field_names(declared_fields, info))
        if self.__class__.__name__ == "NestedSerializer":
            return fields
        self.extend_field_names(fields, "status")
        return fields


class TaggedModelSerializerMixin(BaseModelSerializer):
    def get_field_names(self, declared_fields, info):
        """Ensure that 'tags' field is always present."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "tags")
        return fields

    def create(self, validated_data):
        tags = validated_data.pop("tags", None)
        instance = super().create(validated_data)

        if tags is not None:
            return self._save_tags(instance, tags)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        # Cache tags on instance for change logging
        instance._tags = tags or []

        instance = super().update(instance, validated_data)

        if tags is not None:
            return self._save_tags(instance, tags)
        return instance

    def _save_tags(self, instance, tags):
        if tags:
            instance.tags.set([t.name for t in tags])
        else:
            instance.tags.clear()

        return instance


# TODO: remove in 2.2
@class_deprecated_in_favor_of(TaggedModelSerializerMixin)
class TaggedObjectSerializer(TaggedModelSerializerMixin):
    pass
