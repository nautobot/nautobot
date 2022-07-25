import logging

from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import JSONField
from rest_framework.serializers import ValidationError

from nautobot.core.api import ValidatedModelSerializer
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import Relationship, RelationshipAssociation
from nautobot.utilities.api import get_serializer_for_model


logger = logging.getLogger(__name__)


nested_abstract_serializer = {
    "type": "object",
    "required": False,
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
        # Dictionary, keyed by relationship slug
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid", "readOnly": True},
                "url": {"type": "string", "format": "uri", "readOnly": True},
                "name": {"type": "string", "readOnly": True},
                "type": {"type": "string", "readOnly": True, "example": "one-to-many"},
                "source": {"type": "object", "required": False, "properties": side_data_schema},
                "destination": {"type": "object", "required": False, "properties": side_data_schema},
                "peer": {"type": "object", "required": False, "properties": side_data_schema},
            },
        },
    }
)
class RelationshipsDataField(JSONField):
    """
    Represent the set of all Relationships defined for a given model,
    and all RelationshipAssociations per Relationship that apply to a specific instance of that model.

    This is patterned after the CustomField handling in nautobot.extras.api.customfields.CustomFieldsDataField,
    including the ability to make point updates to individual relationships of an existing instance without needing
    to provide the entire dict of all relationships and associations.
    """

    def to_representation(self, value):
        """
        Get a JSON representation of all relationships and associations applicable to this model.

        Returns:
            {
                "<relationship-slug>": {
                    "id": ...,
                    "url": ...,
                    "name": ...,
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
                "<relationship-slug>": {
                    ...
                },
                ...
            }
        """
        data = {}
        relationships_data = value.get_relationships(include_hidden=True)
        for this_side, relationships in relationships_data.items():
            for relationship, associations in relationships.items():
                data.setdefault(
                    relationship.slug,
                    {
                        "id": relationship.id,
                        "url": reverse("extras-api:relationship-detail", kwargs={"pk": relationship.id}),
                        "name": relationship.name,
                        "type": relationship.type,
                    },
                )
                other_side = RelationshipSideChoices.OPPOSITE[this_side]
                data[relationship.slug][other_side] = {"label": relationship.get_label(this_side)}

                other_type = getattr(relationship, f"{other_side}_type")
                data[relationship.slug][other_side]["object_type"] = f"{other_type.app_label}.{other_type.model}"

                # Get the nested serializer, if any, for the objects of other_type.
                # This may fail, such as in the case of a plugin that has models but doesn't implement serializers,
                # or in the case of a relationship involving models from a plugin that's not currently enabled.
                other_side_serializer = None
                other_side_model = other_type.model_class()
                if other_side_model is not None:
                    try:
                        other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                    except SerializerNotFound:
                        pass

                other_objects = [assoc.get_peer(value) for assoc in associations if assoc.get_peer(value) is not None]

                if other_side_serializer is not None:
                    data[relationship.slug][other_side]["objects"] = [
                        other_side_serializer(other_obj, context=self.context).data for other_obj in other_objects
                    ]
                else:
                    # Simulate a serializer that contains nothing but the id field.
                    data[relationship.slug][other_side]["objects"] = [
                        {"id": other_obj.id} for other_obj in other_objects
                    ]

        logger.info("to_representation(%s) -> %s", value, data)
        return data

    def to_internal_value(self, data):
        """
        Allow for updates to some relationships without overriding others.
        """
        output_data = self.to_representation(self.parent.instance) if self.parent.instance is not None else {}
        for relationship_slug, relationship_data in data.items():
            if relationship_slug not in output_data:
                raise ValidationError(f'"{relationship_slug}" is not a relationship on {self.parent.Meta.model}')

            # no need for ObjectDoesNotExist check here since the output_data check above guarantees its existence
            relationship = Relationship.objects.get(slug=relationship_slug)

            for other_side in ["source", "destination", "peer"]:
                if other_side not in relationship_data:
                    continue

                if other_side not in output_data[relationship_slug]:
                    raise ValidationError(
                        f'"{other_side}" is not a valid side for "{relationship_slug}" on {self.parent.Meta.model}'
                    )

                objects_data = relationship_data[other_side].get("objects", [])
                if not isinstance(objects_data, (list, tuple)):
                    raise ValidationError('"objects" must be a list, not a single value')
                output_data[relationship_slug][other_side]["objects"] = []
                if not objects_data:
                    continue

                # Object validation time!

                if len(objects_data) > 1 and not relationship.has_many(other_side):
                    raise ValidationError(
                        f'For "{relationship_slug}", "{other_side}" objects must include at most a single object'
                    )

                other_type = getattr(relationship, f"{other_side}_type")
                other_side_model = other_type.model_class()
                other_side_serializer = None
                if other_side_model is None:
                    raise ValidationError(f"Model {other_type} is not currently installed, cannot look it up")
                try:
                    other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                except SerializerNotFound as exc:
                    raise ValidationError(
                        f"No {other_side_model}NestedSerializer found, cannot deserialize it"
                    ) from exc

                for object_data in objects_data:
                    serializer_instance = other_side_serializer(data=object_data, context=self.context)
                    # may raise ValidationError, let it bubble up if so
                    serializer_instance.is_valid()

                    # TODO: check relationship filter? It'll be caught by RelationshipAssociation.clean() later if not
                    output_data[relationship_slug][other_side]["objects"].append(serializer_instance.data)

        logger.info("to_internal_value(%s) -> %s", data, output_data)
        return {self.field_name: output_data}


class RelationshipModelSerializerMixin(ValidatedModelSerializer):
    """Extend ValidatedModelSerializer with a `relationships` field."""

    relationships = RelationshipsDataField(required=False, source="*")

    def create(self, validated_data):
        relationships = validated_data.pop("relationships", {})
        instance = super().create(validated_data)
        if relationships:
            self._save_relationships(instance, relationships)
        return instance

    def update(self, instance, validated_data):
        relationships = validated_data.pop("relationships", {})
        instance = super().update(instance, validated_data)
        if relationships:
            self._save_relationships(instance, relationships)
        return instance

    def _save_relationships(self, instance, relationships):
        """Create/update RelationshipAssociations corresponding to a model instance."""
        # relationships has already passed RelationshipsDataField.to_internal_value(), so we can skip some try/excepts
        for relationship_slug, relationship_data in relationships.items():
            relationship = Relationship.objects.get(slug=relationship_slug)

            for other_side in ["source", "destination", "peer"]:
                if other_side not in relationship_data:
                    continue

                other_type = getattr(relationship, f"{other_side}_type")
                other_side_model = other_type.model_class()
                other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                serializer_instance = other_side_serializer(context={"request": None})

                expected_objects_data = relationship_data[other_side].get("objects", [])
                expected_objects = [
                    serializer_instance.to_internal_value(object_data) for object_data in expected_objects_data
                ]

                this_side = RelationshipSideChoices.OPPOSITE[other_side]

                if this_side != RelationshipSideChoices.SIDE_PEER:
                    existing_associations = relationship.associations.filter(**{f"{this_side}_id": instance.pk})
                    existing_objects = [assoc.get_peer(instance) for assoc in existing_associations]
                else:
                    existing_associations_1 = relationship.associations.filter(source_id=instance.pk)
                    existing_objects_1 = [assoc.get_peer(instance) for assoc in existing_associations_1]
                    existing_associations_2 = relationship.associations.filter(destination_id=instance.pk)
                    existing_objects_2 = [assoc.get_peer(instance) for assoc in existing_associations_2]
                    existing_associations = list(existing_associations_1) + list(existing_associations_2)
                    existing_objects = existing_objects_1 + existing_objects_2

                add_objects = []
                remove_assocs = []

                for obj, assoc in zip(existing_objects, existing_associations):
                    if obj not in expected_objects:
                        remove_assocs.append(assoc)
                for obj in expected_objects:
                    if obj not in existing_objects:
                        add_objects.append(obj)

                for add_object in add_objects:
                    if other_side != RelationshipSideChoices.SIDE_SOURCE:
                        assoc = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=instance.id,
                            destination_type=relationship.destination_type,
                            destination_id=add_object.id,
                        )
                    else:
                        assoc = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=add_object.id,
                            destination_type=relationship.destination_type,
                            destination_id=instance.id,
                        )
                    assoc.validated_save()  # enforce relationship filter logic, etc.
                    logger.info("Created %s", assoc)

                for remove_assoc in remove_assocs:
                    logger.info("Deleting %s", remove_assoc)
                    remove_assoc.delete()

    def get_field_names(self, declared_fields, info):
        """Ensure that "relationships" is always included as an opt-in field."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "relationships", opt_in_only=True)
        return fields
