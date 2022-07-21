import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import CreateOnlyDefault, JSONField
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

    def to_representation(self, obj):
        """
        Get a dict representation of applicable Relationships and the objects associated by each such Relationship.

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
        relationships_data = obj.get_relationships(include_hidden=True)
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
                        try:
                            other_side_serializer = get_serializer_for_model(other_side_model)
                        except SerializerNotFound:
                            pass

                other_objects = [assoc.get_peer(obj) for assoc in associations if assoc.get_peer(obj) is not None]

                if other_side_serializer is not None:
                    data[relationship.slug][other_side]["objects"] = [
                        other_side_serializer(other_obj, context=self.context).data for other_obj in other_objects
                    ]
                else:
                    # Simulate a serializer that contains nothing but the id field.
                    data[relationship.slug][other_side]["objects"] = [
                        {"id": other_obj.id} for other_obj in other_objects
                    ]

        logger.info("to_representation(%s) -> %s", obj, data)
        return data

    def to_internal_value(self, data):
        """
        Convert specified data dictionary to a dict of Relationships with dicts of Nautobot data model instances.

        Returns:
            {
                <Relationship instance>: {
                    "source": [<model instance>],
                },
                <Relationship instance>: {
                    "source": [<model instance>, <model instance>, ...],
                    "destination": [<model instance>, <model instance>, ...],
                },
                <Relationship instance>: {
                    "peer": [<model instance>, <model instance>, ...],
                },
                ...
            }
        """
        output_data = {}
        for relationship_slug, relationship_data in data:
            try:
                relationship = Relationship.objects.get(slug=relationship_slug)
            except Relationship.DoesNotExist:
                raise ValidationError(f"No such relationship {relationship_slug}")

            output_data[relationship] = {}

            for other_side in ["source", "destination", "peer"]:
                if other_side not in relationship_data:
                    continue
                this_side = RelationshipSideChoices.OPPOSITE[other_side]

                # TODO cache content-type for efficiency
                if getattr(relationship, f"{this_side}_type") != ContentType.objects.get_for_model(
                    self.parent.Meta.model
                ):
                    raise ValidationError(
                        f"{self.parent.Meta.model} cannot be a {this_side} for Relationship {relationship}"
                    )
                # TODO validate relationship filters too?

                if this_side == RelationshipSideChoices.SIDE_PEER and not relationship.symmetric:
                    raise ValidationError(f"For {relationship}, must specify source(s)/destination(s), not peer(s)")
                elif this_side != RelationshipSideChoices.SIDE_PEER and relationship.symmetric:
                    raise ValidationError(f"For {relationship}, must specify peer(s), not source(s)/destination(s)")

                object_data = relationship_data[other_side].get("objects", [])
                if not isinstance(object_data, (list, tuple)):
                    raise ValidationError(f"{other_side} must be a list, not a single value")
                if len(object_data) > 1 and not relationship.has_many(other_side):
                    raise ValidationError(f"For {relationship}, {other_side} must include at most a single object")

                # As in to_representation() above, model_class() may fail if other_type is from a non-enabled plugin
                # and get_serializer_for_model() may fail if a plugin doesn't implement serializers.
                other_type = getattr(relationship, f"{other_side}_type")
                other_side_serializer = None
                other_side_model = other_type.model_class()

                related_objects = []
                for obj_data in object_data:
                    if other_side_model is None:
                        raise ValidationError(f"Model {other_type} is not available in the database, cannot look it up")
                    try:
                        if isinstance(obj_data, dict):
                            related_object = other_side_model.objects.get(**obj_data)
                        else:
                            related_object = other_side_model.objects.get(pk=obj_data)
                    except other_side_model.DoesNotExist:
                        raise ValidationError(f"Related object not found for {relationship} {other_type} {obj_data}")
                    except MultipleObjectsReturned:
                        raise ValidationError(f"Multiple objects found for {relationship} {other_type} {obj_data}")
                    except Exception as exc:  # TODO be more specific, what else can we likely encounter here?
                        raise ValidationError(str(exc))
                    related_objects.append(related_object)

                output_data[relationship][other_side] = related_objects

        logger.info("to_internal_value(%s) -> %s", data, output_data)
        return output_data


class RelationshipModelSerializerMixin(ValidatedModelSerializer):
    """Extend ValidatedModelSerializer with a `relationships` field."""

    relationships = RelationshipsDataField(required=False, source="*")

    def save(self):
        """Create/update RelationshipAssociations corresponding to a model instance."""
        instance = super().save()
        for relationship, relationship_data in self.validated_data["relationships"].items():
            for other_side, expected_objects in relationship_data.items():
                this_side = RelationshipSideChoices.OPPOSITE[other_side]

                add_objects = []
                remove_assocs = []

                if this_side != RelationshipSideChoices.SIDE_PEER:
                    existing_associations = relationship.associations.filter(**{f"{this_side}_id": instance.pk})
                    existing_objects = [assoc.get_peer(instance) for assoc in existing_associations]
                else:
                    existing_associations_1 = relationship.associations.filter(source_id=instance.pk)
                    existing_objects_1 = [assoc.get_peer(instance) for assoc in existing_associations_1]
                    existing_associations_2 = relationship.associations.filter(destination_id=instance.pk)
                    existing_objects_2 = [assoc.get_peer(instance) for assoc in existing_associations_2]
                    existing_associations = existing_associations_1 + existing_associations_2
                    existing_objects = existing_objects_1 + existing_objects_2

                for obj, assoc in zip(existing_objects, existing_associations):
                    if obj not in expected_objects:
                        remove_assocs.append(assoc)
                for obj in expected_objects:
                    if obj not in existing_objects:
                        add_objects.append(obj)

                for add_object in add_objects:
                    if other_side != RelationshipSideChoices.SIDE_SOURCE:
                        assoc = RelationshipAssociation.objects.create(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=instance.id,
                            destination_type=relationship.destination_type,
                            destination_id=related_object.id,
                        )
                    else:
                        assoc = RelationshipAssociation.objects.create(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=related_object.id,
                            destination_type=relationship.destination_type,
                            destination_id=instance.id,
                        )
                    logger.info("Created %s", assoc)

                for remove_assoc in remove_assocs:
                    logger.info("Deleting %s", remove_assoc)
                    remove_assoc.delete()
