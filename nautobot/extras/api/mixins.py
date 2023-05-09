import logging


from nautobot.core.api import (
    BaseModelSerializer,
)

logger = logging.getLogger(__name__)


class TaggedModelSerializerMixin(BaseModelSerializer):
    def get_field_names(self, declared_fields, info):
        """Ensure that 'tags' field is always present except on nested serializers."""
        fields = list(super().get_field_names(declared_fields, info))
        if not self.is_nested:
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
