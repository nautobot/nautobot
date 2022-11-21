import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import JSONField
from rest_framework.reverse import reverse
from rest_framework.serializers import ValidationError

from nautobot.core.api import ValidatedModelSerializer
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import Relationship, RelationshipAssociation
from nautobot.utilities.api import get_serializer_for_model


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
        # Dictionary, keyed by relationship slug
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "required": ["id", "url", "name", "type"],
            "properties": {
                "id": {"type": "string", "format": "uuid", "readOnly": True},
                "url": {"type": "string", "format": "uri", "readOnly": True},
                "name": {"type": "string", "readOnly": True},
                "type": {"type": "string", "readOnly": True, "example": "one-to-many"},
                "source": {"type": "object", "properties": side_data_schema},
                "destination": {"type": "object", "properties": side_data_schema},
                "peer": {"type": "object", "properties": side_data_schema},
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
                        "id": str(relationship.id),
                        "url": reverse(
                            "extras-api:relationship-detail",
                            kwargs={"pk": relationship.id},
                            request=self.parent.context.get("request"),
                        ),
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

        logger.debug("to_representation(%s) -> %s", value, data)
        return data

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
        relationship_slugs = [relationship.slug for relationship in relationships]
        for relationship_slug in data:
            if relationship_slug not in relationship_slugs:
                raise ValidationError(
                    f'"{relationship_slug}" is not a relationship on {self.parent.Meta.model._meta.label}'
                )

        for relationship in relationships:
            if relationship.slug not in data:
                # No changes to any associations for this relationship, can disregard it
                del output_data[relationship]
                continue

            relationship_data = data[relationship.slug]

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
                        f'"objects" must be specified under ["{relationship.slug}"]["{other_side}"] when present'
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
                other_side_serializer = None
                if other_side_model is None:
                    raise ValidationError(f"Model {other_type} is not currently installed, cannot look it up")
                try:
                    other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                except SerializerNotFound as exc:
                    raise ValidationError(
                        f"No Nested{other_side_model}Serializer found, cannot deserialize it"
                    ) from exc

                for object_data in objects_data:
                    serializer_instance = other_side_serializer(data=object_data, context=self.context)
                    # may raise ValidationError, let it bubble up if so
                    serializer_instance.is_valid()

                    # We don't check/enforce relationship source_filter/destination_filter here, as that'll be handled
                    # later by `RelationshipAssociation.validated_save()` in RelationshipModelSerializerMixin.
                    output_data[relationship][other_side].append(serializer_instance.data)

        logger.debug("to_internal_value(%s) -> %s", data, output_data)
        return {self.field_name: output_data}


class RelationshipModelSerializerMixin(ValidatedModelSerializer):
    """Extend ValidatedModelSerializer with a `relationships` field."""

    relationships = RelationshipsDataField(required=False, source="*")

    def create(self, validated_data):
        relationships_data = validated_data.pop("relationships", {})
        required_relationships_errors = self.Meta().model.required_related_objects_errors(
            output_for="api", initial_data=relationships_data
        )
        if required_relationships_errors:
            raise ValidationError({"relationships": required_relationships_errors})
        instance = super().create(validated_data)
        if relationships_data:
            try:
                self._save_relationships(instance, relationships_data)
            except DjangoValidationError as error:
                raise ValidationError(str(error))
        return instance

    def update(self, instance, validated_data):
        relationships_key_specified = "relationships" in self.context["request"].data
        relationships_data = validated_data.pop("relationships", {})
        required_relationships_errors = self.Meta().model.required_related_objects_errors(
            output_for="api",
            initial_data=relationships_data,
            relationships_key_specified=relationships_key_specified,
            instance=instance,
        )
        if required_relationships_errors:
            raise ValidationError({"relationships": required_relationships_errors})

        instance = super().update(instance, validated_data)
        if relationships_data:
            self._save_relationships(instance, relationships_data)
        return instance

    def _save_relationships(self, instance, relationships):
        """Create/update RelationshipAssociations corresponding to a model instance."""
        # relationships has already passed RelationshipsDataField.to_internal_value(), so we can skip some try/excepts
        logger.debug("_save_relationships: %s : %s", instance, relationships)
        for relationship, relationship_data in relationships.items():

            for other_side in ["source", "destination", "peer"]:
                if other_side not in relationship_data:
                    continue

                other_type = getattr(relationship, f"{other_side}_type")
                other_side_model = other_type.model_class()
                other_side_serializer = get_serializer_for_model(other_side_model, prefix="Nested")
                serializer_instance = other_side_serializer(context={"request": self.context.get("request")})

                expected_objects_data = relationship_data[other_side]
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
                    if "request" in self.context and not self.context["request"].user.has_perm(
                        "extras.add_relationshipassociation"
                    ):
                        raise PermissionDenied("This user does not have permission to create RelationshipAssociations.")
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
                    logger.debug("Created %s", assoc)

                for remove_assoc in remove_assocs:
                    if "request" in self.context and not self.context["request"].user.has_perm(
                        "extras.delete_relationshipassociation"
                    ):
                        raise PermissionDenied("This user does not have permission to delete RelationshipAssociations.")
                    logger.debug("Deleting %s", remove_assoc)
                    remove_assoc.delete()

    def get_field_names(self, declared_fields, info):
        """Ensure that "relationships" is always included as an opt-in field."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "relationships", opt_in_only=True)
        return fields
