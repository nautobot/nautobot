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


common_serializer_properties = {
    "id": {"type": "string", "format": "uuid", "readOnly": True},
    "url": {"type": "string", "format": "uri", "readOnly": True},
    "name": {"type": "string", "readOnly": True},
    "type": {"type": "string", "readOnly": True, "example": "one-to-many"},
}


@extend_schema_field(
    {
        "type": "object",
        "additionalProperties": {
            "allOf": [
                {
                    "type": "object",
                    "properties": common_serializer_properties,
                },
                {
                    "anyOf": [
                        {
                            "allOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "source_type": {"type": "string", "readOnly": True, "example": "dcim.site"},
                                        "source_label": {"type": "string", "readOnly": True},
                                    }
                                },
                                {
                                    "oneOf": [
                                        {"type": "object", "properties": {"source": nested_abstract_serializer}},
                                        {"type": "object", "properties": {"sources": {"type": "array", "items": nested_abstract_serializer}}},
                                    ],
                                },
                            ],
                        },
                        {
                            "allOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "destination_type": {"type": "string", "readOnly": True, "example": "dcim.site"},
                                        "destination_label": {"type": "string", "readOnly": True},
                                    },
                                },
                                {
                                    "oneOf": [
                                        {"type": "object", "properties": {"destination": nested_abstract_serializer}},
                                        {"type": "object", "properties": {"destinations": {"type": "array", "items": nested_abstract_serializer}}},
                                    ],
                                },
                            ],
                        },
                        {
                            "allOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "peer_type": {"type": "string", "readOnly": True, "example": "dcim.site"},
                                        "peer_label": {"type": "string", "readOnly": True},
                                    },
                                },
                                {
                                    "oneOf": [
                                        {"type": "object", "properties": {"peer": nested_abstract_serializer}},
                                        {"type": "object", "properties": {"peers": {"type": "array", "items": nested_abstract_serializer}}},
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
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
                    "source_type": "dcim.device|ipam.ipaddress|...",
                    "source_label": ...,
                    "sources": [{...}, {...}, {...}],  # if the source is a "many" side
                    "source": {...},  # if the source is a "one" side
                    # if this model can be the source of the relationship:
                    "destination_type": "dcim.device|ipam.ipaddress|...",
                    "destination_label": ...,
                    "destinations": [{...}, {...}, {...}],  # if the destination is a "many" side
                    "destination": {...},  # if the destination is a "one" side
                    # if this relationship is symmetric, instead of source/destination above:
                    "peer_type": "dcim.device|ipam.ipaddress|...",
                    "peer_label": ...,
                    "peers": [{...}, {...}, {...}],  # if the peer is a "many" side
                    "peer": {...},  # if the peer is a "one" side
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
                data[relationship.slug][f"{other_side}_label"] = relationship.get_label(this_side)

                other_side_type = getattr(relationship, f"{other_side}_type")
                other_side_serializer = None
                other_side_model = other_side_type.model_class()
                if other_side_model is not None:
                    try:
                        other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                    except SerializerNotFound:
                        try:
                            other_side_serializer = get_serializer_for_model(other_side_model)
                        except SerializerNotFound:
                            pass

                data[relationship.slug][f"{other_side}_type"] = f"{other_side_type.app_label}.{other_side_type.model}"


                if relationship.has_many(other_side):
                    other_objects = [assoc.get_peer(obj) for assoc in associations if assoc.get_peer(obj) is not None]

                    if other_side_serializer:
                        data[relationship.slug][f"{other_side}s"] = [
                            other_side_serializer(other_obj, context=self.context).data for other_obj in other_objects
                        ]
                    else:
                        data[relationship.slug][f"{other_side}s"] = [{"id": other_obj.id} for other_obj in other_objects]
                else:
                    if not associations.exists():
                        data[relationship.slug][other_side] = None
                    else:
                        other_obj = associations.first().get_peer(obj)
                        if other_obj is None:
                            data[relationship.slug][other_side] = None
                        if other_side_serializer:
                            data[relationship.slug][other_side] = other_side_serializer(other_obj, context=self.context).data
                        else:
                            data[relationship.slug][other_side] = {"id": other_obj.id}

        logger.info("to_representation(%s) -> %s", obj, data)
        return data

    def to_internal_value(self, data):
        """
        Convert specified data dictionary to a dict of Relationships with dicts of Nautobot data model instances.

        Returns:
            {
                <Relationship instance>: {
                    "source": <model instance>,
                },
                <Relationship instance>: {
                    "sources": [<model instance>, <model instance>, ...],
                    "destinations": [<model instance>, <model instance>, ...],
                },
                <Relationship instance>: {
                    "peers": [<model instance>, <model instance>, ...],
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

            for key in ["source", "sources", "destination", "destinations", "peer", "peers"]:
                if key not in relationship_data:
                    continue
                if key.endswith("s"):
                    other_side = key[:-1]
                    has_many = True
                else:
                    other_side = key
                    has_many = False
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

                if has_many and not relationship.has_many(other_side):
                    raise ValidationError(f"For {relationship}, {other_side} must be a single value, not a list")
                elif not has_many and relationship.has_many(other_side):
                    raise ValidationError(f"For {relationship}, {other_side}s must be a list, not a single value")

                if has_many and not isinstance(relationship_data[key], (list, tuple)):
                    raise ValidationError(f"{key} must be a list, not a single value")
                elif not has_many and isinstance(relationship_data[key], (list, tuple)):
                    raise ValidationError(f"{key} must be a single value, not a list")

                other_side_type = getattr(relationship, f"{other_side}_type")
                other_side_model = other_side_type.model_class()
                try:
                    other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                except SerializerNotFound:
                    try:
                        other_side_serializer = get_serializer_for_model(other_side_model)
                    except SerializerNotFound:
                        other_side_serializer = None

                if has_many:
                    related_objects = []
                    for entry in relationship_data[key]:
                        if other_side_serializer:
                            related_object = other_side_serializer(context=self.context).to_internal_value(entry)
                        else:
                            try:
                                if isinstance(entry, dict):
                                    related_object = other_side_model.objects.get(**entry)
                                else:
                                    related_object = other_side_model.objects.get(pk=entry)
                            except other_side_model.DoesNotExist:
                                raise ValidationError(f"Related object not found for {relationship} {key} {entry}")
                            except MultipleObjectsReturned:
                                raise ValidationError(f"Multiple objects found for {relationship} {key} {entry}")
                        related_objects.append(related_object)
                    output_data[relationship][key] = related_objects
                else:
                    if other_side_serializer:
                        related_object = other_side_serializer(context=self.context).to_internal_value(relationship_data[key])
                    else:
                        try:
                            if isinstance(relationship_data[key], dict):
                                related_object = other_side_model.objects.get(**relationship_data[key])
                            else:
                                related_object = other_side_model.objects.get(pk=relationship_data[key])
                        except other_side_model.DoesNotExist:
                            raise ValidationError(
                                f"Related object not found for {relationship} {key} {relationship_data[key]}"
                            )
                        except MultipleObjectsReturned:
                            raise ValidationError(
                                f"Multiple objects found for {relationship} {key} {relationship_data[key]}"
                            )
                    output_data[relationship][key] = related_object

        logger.info("to_internal_value(%s) -> %s", data, output_data)
        return output_data


class RelationshipModelSerializerMixin(ValidatedModelSerializer):
    """Extend ValidatedModelSerializer with a `relationships` field."""
    relationships = RelationshipsDataField(required=False, source="*")

    def save(self):
        """Create/update RelationshipAssociations corresponding to a model instance."""
        instance = super().save()
        for relationship, relationship_data in self.validated_data["relationships"].items():
            for key, expected_objects in relationship_data.items():
                if key.endswith("s"):
                    other_side = key[:-1]
                else:
                    other_side = key
                    expected_objects = [expected_objects]
                this_side = RelationshipSideChoices.OPPOSITE[other_side]

                add_objects = []
                remove_assocs = []

                if this_side != RelationshipSideChoices.SIDE_PEER:
                    existing_associations = relationship.associations.filter(**{f"{this_side}_id": instance.pk})
                    existing_objects = [getattr(assoc, other_side) for assoc in existing_associations]
                else:
                    existing_associations_1 = relationship.associations.filter(source_id=instance.pk)
                    existing_objects_1 = [assoc.destination for assoc in existing_associations_1]
                    existing_associations_2 = relationship.associations.filter(destination_id=instance.pk)
                    existing_objects_2 = [assoc.source for assoc in existing_associations_2]
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

