import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import JSONField
from rest_framework.reverse import reverse
from rest_framework.serializers import ValidationError

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.mixins import WritableSerializerMixin
from nautobot.core.api.utils import (
    get_relation_info_for_nested_serializers,
    get_serializer_for_model,
    nested_serializer_factory,
)
from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import Relationship

logger = logging.getLogger(__name__)


nested_abstract_serializer = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "url": {"type": "string", "format": "uri", "readOnly": True},
        "display": {"type": "string", "readOnly": True},
    },
    "additionalProperties": True,
}


side_data_schema = {
    "label": {"type": "string", "readOnly": True},
    "object_type": {"type": "string", "readOnly": True, "example": "dcim.site"},
    "objects": {"type": "array", "items": nested_abstract_serializer},
}


@extend_schema_field(
    {
        # Dictionary, keyed by relationship key
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "required": ["id", "url", "label", "type"],
            "properties": {
                "id": {"type": "string", "format": "uuid", "readOnly": True},
                "url": {"type": "string", "format": "uri", "readOnly": True},
                "label": {"type": "string", "readOnly": True},
                "type": {"type": "string", "readOnly": True, "example": "one-to-many"},
                "source": {"type": "object", "properties": side_data_schema},
                "destination": {"type": "object", "properties": side_data_schema},
                "peer": {"type": "object", "properties": side_data_schema},
            },
        },
    }
)
class RelationshipsDataField(WritableSerializerMixin, JSONField):
    """
    Represent the set of all Relationships defined for a given model,
    and all RelationshipAssociations per Relationship that apply to a specific instance of that model.

    This is patterned after the CustomField handling in nautobot.extras.api.customfields.CustomFieldsDataField,
    including the ability to make point updates to individual relationships of an existing instance without needing
    to provide the entire dict of all relationships and associations.
    """

    queryset = None

    def to_representation(self, value):
        """
        Get a JSON representation of all relationships and associations applicable to this model.

        Returns:
            {
                "<relationship_key>": {
                    "id": ...,
                    "url": ...,
                    "label": ...,
                    "type": "one-to-one|one-to-many|many-to-many|...",
                    # if this model can be the destination of the relationship:
                    "source": {
                        "label": ...,
                        "object_type": "dcim.device|ipam.ipaddress|...",
                        "objects": [{...}, {...}, ...],
                    },
                    # if this model can be the source of the relationship:
                    "destination": {
                        "label": ...,
                        "object_type": "dcim.device|ipam.ipaddress|...",
                        "objects": [{...}, {...}, ...],
                    },
                    # if this relationship is symmetric, instead of source/destination above:
                    "peer": {
                        "label": ...,
                        "object_type": "dcim.device|ipam.ipaddress|...",
                        "objects": [{...}, {...}, ...],
                    },
                },
                "<relationship_key>": {
                    ...
                },
                ...
            }
        """
        data = {}
        relationships_data = value.get_relationships(include_hidden=True)
        for this_side, relationships in relationships_data.items():
            for relationship, associations in relationships.items():
                depth = int(self.context.get("depth", 0))
                data.setdefault(
                    relationship.key,
                    {
                        "id": str(relationship.id),
                        "url": reverse(
                            "extras-api:relationship-detail",
                            kwargs={"pk": relationship.id},
                            request=self.parent.context.get("request"),
                        ),
                        "label": relationship.label,
                        "type": relationship.type,
                    },
                )
                other_side = RelationshipSideChoices.OPPOSITE[this_side]
                data[relationship.key][other_side] = {"label": relationship.get_label(this_side)}

                other_type = getattr(relationship, f"{other_side}_type")
                data[relationship.key][other_side]["object_type"] = f"{other_type.app_label}.{other_type.model}"

                # Get the nested serializer, if any, for the objects of other_type.
                # This may fail, such as in the case of a plugin that has models but doesn't implement serializers,
                # or in the case of a relationship involving models from a plugin that's not currently enabled.
                other_side_serializer = None
                other_side_model = other_type.model_class()

                other_objects = [assoc.get_peer(value) for assoc in associations if assoc.get_peer(value) is not None]
                if other_side_model is not None:
                    try:
                        depth = int(self.context.get("depth", 0))
                        if depth != 0:
                            if associations and other_objects:
                                relation_info = get_relation_info_for_nested_serializers(
                                    associations[0], other_objects[0], f"{other_side}"
                                )
                                other_side_serializer, field_kwargs = self.build_nested_field(
                                    f"{other_side}", relation_info, depth
                                )
                    except SerializerNotFound:
                        pass

                if other_side_serializer is not None:
                    data[relationship.key][other_side]["objects"] = [
                        other_side_serializer(
                            other_obj, context={"request": self.context.get("request")}, **field_kwargs
                        ).data
                        for other_obj in other_objects
                    ]
                else:
                    # Simulate a serializer that contains nothing but the id field.
                    data[relationship.key][other_side]["objects"] = [
                        {"id": other_obj.id} for other_obj in other_objects
                    ]

        logger.debug("to_representation(%s) -> %s", value, data)
        return data

    def build_nested_field(self, field_name, relation_info, nested_depth):
        return nested_serializer_factory(relation_info, nested_depth)

    def to_internal_value(self, data):
        """
        Allow for updates to some relationships without overriding others.

        Returns:
            <self.field_name>: {
                <relationship>: {
                    "source": [<object>, <object>,...]
                },
                <relationship>: {
                    "destination": [<object>, <object>,...]
                },
                <relationship>: {
                    "destination": [<object>, ...],
                    "source": [...],
                },
                <relationship>: {
                    "peer": [<object>, <object>, ...],
                },
            }
        """
        # Set up the skeleton of the output data for all relevant relationships
        output_data = {}
        ct = ContentType.objects.get_for_model(self.parent.Meta.model)
        relationships = Relationship.objects.filter(Q(source_type=ct) | Q(destination_type=ct))
        for relationship in relationships:
            output_data[relationship] = {}
            if relationship.source_type == ct and not relationship.symmetric:
                output_data[relationship]["destination"] = []
            if relationship.destination_type == ct and not relationship.symmetric:
                output_data[relationship]["source"] = []
            if relationship.symmetric:
                output_data[relationship]["peer"] = []

        # Input validation - prevent referencing a relationship that doesn't exist or apply
        relationship_keys = [relationship.key for relationship in relationships]
        for relationship_key in data:
            if relationship_key not in relationship_keys:
                raise ValidationError(
                    f'"{relationship_key}" is not a relationship on {self.parent.Meta.model._meta.label}'
                )

        for relationship in relationships:
            if relationship.key not in data:
                # No changes to any associations for this relationship, can disregard it
                del output_data[relationship]
                continue

            relationship_data = data[relationship.key]

            for other_side in ["source", "destination", "peer"]:
                if other_side not in relationship_data:
                    # No changes to this side of the association for this relationship, can disregard it
                    if other_side in output_data[relationship]:
                        del output_data[relationship][other_side]
                    continue

                # Input validation - prevent referencing a side of the relationship that isn't relevant to this model
                if other_side not in output_data[relationship]:
                    raise ValidationError(
                        f'"{other_side}" is not a valid side for "{relationship}" '
                        f"on {self.parent.Meta.model._meta.label}"
                    )

                # Don't allow omitting 'objects' altogether as a shorthand for deleting all associations
                if "objects" not in relationship_data[other_side]:
                    raise ValidationError(
                        f'"objects" must be specified under ["{relationship.key}"]["{other_side}"] when present'
                    )
                objects_data = relationship_data[other_side]["objects"]
                if not isinstance(objects_data, (list, tuple)):
                    raise ValidationError('"objects" must be a list, not a single value')

                if not objects_data:
                    # Empty list -- delete all associations for this relationship, nothing further to handle below
                    continue

                # Don't allow multiple objects for a one-to-* relationship!
                if len(objects_data) > 1 and not relationship.has_many(other_side):
                    raise ValidationError(
                        f'For "{relationship}", "{other_side}" objects must include at most a single object'
                    )

                # Object lookup time!
                other_type = getattr(relationship, f"{other_side}_type")
                other_side_model = other_type.model_class()
                self.queryset = other_side_model.objects
                other_side_serializer = None
                if other_side_model is None:
                    raise ValidationError(f"Model {other_type} is not currently installed, cannot look it up")
                try:
                    other_side_serializer = get_serializer_for_model(other_side_model)
                except SerializerNotFound as exc:
                    raise ValidationError(
                        f"No Nested{other_side_model}Serializer found, cannot deserialize it"
                    ) from exc

                depth = int(self.context.get("depth", 0))

                if depth != 0:
                    for object_data in objects_data:
                        serializer_instance = other_side_serializer(data=object_data, context=self.context)
                        # may raise ValidationError, let it bubble up if so
                        serializer_instance.is_valid(raise_exception=True)

                        # We don't check/enforce relationship source_filter/destination_filter here, as that'll be handled
                        # later by `RelationshipAssociation.validated_save()` in RelationshipModelSerializerMixin.
                        output_data[relationship][other_side].append(serializer_instance.data)
                else:
                    for object_data in objects_data:
                        instance = super().to_internal_value(object_data)
                        output_data[relationship][other_side].append({"id": instance.id})
        logger.debug("to_internal_value(%s) -> %s", data, output_data)
        return {self.field_name: output_data}
