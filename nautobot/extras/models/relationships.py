import logging
from collections import OrderedDict
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import ValidationError
from django.db import models
from django.db.models import Q

from nautobot.extras.choices import RelationshipTypeChoices, RelationshipSideChoices
from nautobot.extras.utils import FeatureQuery
from nautobot.extras.models import ChangeLoggedModel
from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.utilities.utils import get_filterset_for_model
from nautobot.utilities.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)
from nautobot.utilities.querysets import RestrictedQuerySet


logger = logging.getLogger(__name__)


VALID_SIDES = [item[0] for item in RelationshipSideChoices.CHOICES]


class RelationshipModel(models.Model):
    """
    Abstract class for any model which may have custom relationships associated with it.
    """

    class Meta:
        abstract = True

    # Define GenericRelations so that deleting a RelationshipModel instance
    # cascades to deleting any RelationshipAssociations that were using this instance,
    # and also for convenience in looking up the RelationshipModels associated to any given RelationshipAssociation
    source_for_associations = GenericRelation(
        "extras.RelationshipAssociation",
        content_type_field="source_type",
        object_id_field="source_id",
        related_query_name="source_%(app_label)s_%(class)s",  # e.g. 'source_dcim_site', 'source_ipam_vlan'
    )
    destination_for_associations = GenericRelation(
        "extras.RelationshipAssociation",
        content_type_field="destination_type",
        object_id_field="destination_id",
        related_query_name="destination_%(app_label)s_%(class)s",  # e.g. 'destination_dcim_rack'
    )

    def get_relationships(self, include_hidden=False):
        """
        Return a dictionary of queryset for all custom relationships

        Returns:
            response {
                "source": {
                    <relationship #1>: <queryset #1>,
                    <relationship #2>: <queryset #2>,
                },
                "destination": {
                    <relationship #3>: <queryset #3>,
                    <relationship #4>: <queryset #4>,
                },
                "peer": {
                    <relationship #5>: <queryset #5>,
                    <relationship #6>: <queryset #6>,
                },
            }
        """
        src_relationships, dst_relationships = Relationship.objects.get_for_model(self)
        content_type = ContentType.objects.get_for_model(self)

        sides = {
            RelationshipSideChoices.SIDE_SOURCE: src_relationships,
            RelationshipSideChoices.SIDE_DESTINATION: dst_relationships,
        }

        resp = {
            RelationshipSideChoices.SIDE_SOURCE: OrderedDict(),
            RelationshipSideChoices.SIDE_DESTINATION: OrderedDict(),
            RelationshipSideChoices.SIDE_PEER: OrderedDict(),
        }
        for side, relationships in sides.items():
            for relationship in relationships:
                if getattr(relationship, f"{side}_hidden") and not include_hidden:
                    continue

                # Determine if the relationship is applicable to this object based on the filter
                # To resolve the filter we are using the FilterSet for the given model
                # If there is no match when we query the primary key of the device along with the filter
                # Then the relationship is not applicable to this object
                if getattr(relationship, f"{side}_filter"):
                    filterset = get_filterset_for_model(self._meta.model)
                    if filterset:
                        filter_params = getattr(relationship, f"{side}_filter")
                        if not filterset(filter_params, self._meta.model.objects.filter(id=self.id)).qs.exists():
                            continue

                # Construct the queryset to query all RelationshipAssociation for this object and this relationship
                query_params = {"relationship": relationship}
                if not relationship.symmetric:
                    # Query for RelationshipAssociations that this object is on the expected side of
                    query_params[f"{side}_id"] = self.pk
                    query_params[f"{side}_type"] = content_type

                    resp[side][relationship] = RelationshipAssociation.objects.filter(**query_params)
                else:
                    # Query for RelationshipAssociations involving this object, regardless of side
                    resp[RelationshipSideChoices.SIDE_PEER][relationship] = RelationshipAssociation.objects.filter(
                        (
                            Q(source_id=self.pk, source_type=content_type)
                            | Q(destination_id=self.pk, destination_type=content_type)
                        ),
                        **query_params,
                    )

        return resp

    def get_relationships_data(self):
        """
        Return a dictionary of relationships with the label and the value or the queryset for each.

        Returns:
            response {
                "source": {
                    <relationship #1>: {
                        "label": "...",
                        "peer_type": <ContentType>,
                        "has_many": False,
                        "value": <model>,
                        "url": "...",
                    },
                    <relationship #2>: {
                        "label": "...",
                        "peer_type": <ContentType>,
                        "has_many": True,
                        "value": None,
                        "queryset": <queryset #2>
                    },
                },
                "destination": {
                    (same format as source)
                },
                "peer": {
                    (same format as source)
                },
            }
        """

        relationships_by_side = self.get_relationships()

        resp = {
            RelationshipSideChoices.SIDE_SOURCE: OrderedDict(),
            RelationshipSideChoices.SIDE_DESTINATION: OrderedDict(),
            RelationshipSideChoices.SIDE_PEER: OrderedDict(),
        }
        for side, relationships in relationships_by_side.items():
            for relationship, queryset in relationships.items():

                peer_side = RelationshipSideChoices.OPPOSITE[side]

                resp[side][relationship] = {
                    "label": relationship.get_label(side),
                    "value": None,
                }
                if not relationship.symmetric:
                    resp[side][relationship]["peer_type"] = getattr(relationship, f"{peer_side}_type")
                else:
                    # Symmetric relationship - source_type == destination_type, so it doesn't matter which we choose
                    resp[side][relationship]["peer_type"] = getattr(relationship, f"source_type")

                resp[side][relationship]["has_many"] = relationship.has_many(peer_side)

                if resp[side][relationship]["has_many"]:
                    resp[side][relationship]["queryset"] = queryset
                else:
                    association = queryset.first()
                    if not association:
                        continue

                    peer = association.get_peer(self)

                    resp[side][relationship]["value"] = peer
                    resp[side][relationship]["url"] = peer.get_absolute_url()

        return resp


class RelationshipManager(models.Manager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_model(self, model):
        """
        Return all Relationships assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return (
            self.get_queryset().filter(source_type=content_type),
            self.get_queryset().filter(destination_type=content_type),
        )


class Relationship(BaseModel, ChangeLoggedModel):

    name = models.CharField(max_length=100, unique=True, help_text="Internal relationship name")
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)
    type = models.CharField(
        max_length=50,
        choices=RelationshipTypeChoices,
        default=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        help_text="Cardinality of this relationship",
    )

    #
    # Source
    #
    source_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name="source_relationships",
        verbose_name="Source Object",
        limit_choices_to=FeatureQuery("relationships"),
        help_text="The source object type to which this relationship applies.",
    )
    source_label = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Source Label",
        help_text="Label for related destination objects, as displayed on the source object.",
    )
    source_hidden = models.BooleanField(
        default=False,
        verbose_name="Hide for source object",
        help_text="Hide this relationship on the source object.",
    )
    source_filter = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text="Queryset filter matching the applicable source objects of the selected type",
    )

    #
    # Destination
    #
    destination_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name="destination_relationships",
        verbose_name="Destination Object",
        limit_choices_to=FeatureQuery("relationships"),
        help_text="The destination object type to which this relationship applies.",
    )
    destination_label = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Destination Label",
        help_text="Label for related source objects, as displayed on the destination object.",
    )
    destination_hidden = models.BooleanField(
        default=False,
        verbose_name="Hide for destination object",
        help_text="Hide this relationship on the destination object.",
    )
    destination_filter = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text="Queryset filter matching the applicable destination objects of the selected type",
    )

    objects = RelationshipManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name.replace("_", " ")

    @property
    def symmetric(self):
        return self.type in (
            RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
            RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        )

    def get_label(self, side):
        """Return the label for a given side, source or destination.

        If the label is not returned, return the verbose_name_plural of the other object
        """

        if side not in VALID_SIDES:
            raise ValueError(f"side value can only be: {','.join(VALID_SIDES)}")

        # Peer "side" implies symmetric relationship, where source and dest are equivalent
        if side == RelationshipSideChoices.SIDE_PEER:
            side = RelationshipSideChoices.SIDE_SOURCE

        if getattr(self, f"{side}_label"):
            return getattr(self, f"{side}_label")

        if side == RelationshipSideChoices.SIDE_SOURCE:
            destination_model = self.destination_type.model_class()
            if self.type in (
                RelationshipTypeChoices.TYPE_MANY_TO_MANY,
                RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
                RelationshipTypeChoices.TYPE_ONE_TO_MANY,
            ):
                return destination_model._meta.verbose_name_plural
            else:
                return destination_model._meta.verbose_name

        elif side == RelationshipSideChoices.SIDE_DESTINATION:
            source_model = self.source_type.model_class()
            if self.type in (
                RelationshipTypeChoices.TYPE_MANY_TO_MANY,
                RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
            ):
                return source_model._meta.verbose_name_plural
            else:
                return source_model._meta.verbose_name

        return None

    def has_many(self, side):
        """Return True if the given side of the relationship can support multiple objects."""

        if side not in VALID_SIDES:
            raise ValueError(f"side value can only be: {','.join(VALID_SIDES)}")

        if self.type in (
            RelationshipTypeChoices.TYPE_MANY_TO_MANY,
            RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        ):
            return True

        if self.type in (RelationshipTypeChoices.TYPE_ONE_TO_ONE, RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC):
            return False

        # ONE_TO_MANY
        return side == RelationshipSideChoices.SIDE_DESTINATION

    def to_form_field(self, side):
        """
        Return a form field suitable for setting a Relationship's value for an object.
        """

        if side not in VALID_SIDES:
            raise ValueError(f"side value can only be: {','.join(VALID_SIDES)}")

        peer_side = RelationshipSideChoices.OPPOSITE[side]

        if peer_side != RelationshipSideChoices.SIDE_PEER:
            object_type = getattr(self, f"{peer_side}_type")
            filters = getattr(self, f"{peer_side}_filter") or {}
        else:
            # Symmetric relationship - source and dest fields are presumed identical, so just use source
            object_type = getattr(self, f"source_type")
            filters = getattr(self, f"source_filter") or {}

        queryset = object_type.model_class().objects.all()

        field_class = None
        if self.has_many(peer_side):
            field_class = DynamicModelMultipleChoiceField
        else:
            field_class = DynamicModelChoiceField

        field = field_class(queryset=queryset, query_params=filters)
        field.model = self
        field.required = False
        field.label = self.get_label(side)
        if self.description:
            field.help_text = self.description

        return field

    def clean(self):

        # Check if source and destination filters are valid
        for side in ["source", "destination"]:
            if not getattr(self, f"{side}_filter"):
                continue

            filter = getattr(self, f"{side}_filter")
            side_model = getattr(self, f"{side}_type").model_class()
            model_name = side_model._meta.label
            if not isinstance(filter, dict):
                raise ValidationError({f"{side}_filter": f"Filter for {model_name} must be a dictionary"})

            filterset_class = get_filterset_for_model(side_model)
            if not filterset_class:
                raise ValidationError(
                    {
                        f"{side}_filter": f"Filters are not supported for {model_name} object (Unable to find a FilterSet)"
                    }
                )
            filterset = filterset_class(filter, side_model.objects.all())

            error_messages = []
            if filterset.errors:
                for key in filterset.errors:
                    error_messages.append(f"'{key}': " + ", ".join(filterset.errors[key]))

            filterset_params = set(filterset.get_filters().keys())
            for key in filter.keys():
                if key not in filterset_params:
                    error_messages.append(f"'{key}' is not a valid filter parameter for {model_name} object")

            if error_messages:
                raise ValidationError({f"{side}_filter": error_messages})

        if self.symmetric:
            # For a symmetric relation, source and destination attributes must be equivalent if specified
            error_messages = {}
            if self.source_type != self.destination_type:
                error_messages["destination_type"] = "Must match source_type for a symmetric relationship"
            if self.source_label != self.destination_label:
                if not self.source_label:
                    self.source_label = self.destination_label
                elif not self.destination_label:
                    self.destination_label = self.source_label
                else:
                    error_messages["destination_label"] = "Must match source_label for a symmetric relationship"
            if self.source_hidden != self.destination_hidden:
                error_messages["destination_hidden"] = "Must match source_hidden for a symmetric relationship"
            if self.source_filter != self.destination_filter:
                if not self.source_filter:
                    self.source_filter = self.destination_filter
                elif not self.destination_filter:
                    self.destination_filter = self.source_filter
                else:
                    error_messages["destination_filter"] = "Must match source_filter for a symmetric relationship"

            if error_messages:
                raise ValidationError(error_messages)

        # If the model already exist, ensure that it's not possible to modify the source or destination type
        if self.present_in_database:
            nbr_existing_cras = RelationshipAssociation.objects.filter(relationship=self).count()

            if nbr_existing_cras and self.__class__.objects.get(pk=self.pk).type != self.type:
                raise ValidationError(
                    "Not supported to change the type of the relationship when some associations"
                    " are present in the database, delete all associations first before modifying the type."
                )

            if nbr_existing_cras and self.__class__.objects.get(pk=self.pk).source_type != self.source_type:
                raise ValidationError(
                    "Not supported to change the type of the source object when some associations"
                    " are present in the database, delete all associations first before modifying the source type."
                )

            elif nbr_existing_cras and self.__class__.objects.get(pk=self.pk).destination_type != self.destination_type:
                raise ValidationError(
                    "Not supported to change the type of the destination object when some associations"
                    " are present in the database, delete all associations first before modifying the destination type."
                )


class RelationshipAssociation(BaseModel):
    relationship = models.ForeignKey(to="extras.Relationship", on_delete=models.CASCADE, related_name="associations")

    source_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE, related_name="+")
    source_id = models.UUIDField()
    source = GenericForeignKey(ct_field="source_type", fk_field="source_id")

    destination_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE, related_name="+")
    destination_id = models.UUIDField()
    destination = GenericForeignKey(ct_field="destination_type", fk_field="destination_id")

    class Meta:
        unique_together = (
            "relationship",
            "source_type",
            "source_id",
            "destination_type",
            "destination_id",
        )

    def __str__(self):
        if self.relationship.symmetric:
            return "{} <-> {} - {}".format(self.source, self.destination, self.relationship)
        else:
            return "{} -> {} - {}".format(self.source, self.destination, self.relationship)

    def get_peer(self, obj):

        if obj == self.source:
            return self.destination

        elif obj == self.destination:
            return self.source

    def clean(self):

        if self.source_type != self.relationship.source_type:
            raise ValidationError(
                {"source_type": f"source_type has a different value than defined in {self.relationship}"}
            )

        if self.destination_type != self.relationship.destination_type:
            raise ValidationError(
                {"destination_type": f"destination_type has a different value than defined in {self.relationship}"}
            )

        if self.source_type == self.destination_type and self.source_id == self.destination_id:
            raise ValidationError({"destination_id": "An object cannot form a RelationshipAssociation with itself"})

        if self.relationship.symmetric:
            # Check for a "duplicate" record that exists with source and destination swapped
            if RelationshipAssociation.objects.filter(
                relationship=self.relationship,
                destination_id=self.source_id,
                source_id=self.destination_id,
            ).exists():
                raise ValidationError(
                    {
                        "__all__": f"A {self.relationship} association already exists between {self.source} and {self.destination}"
                    }
                )

        # Check if a similar relationship association already exists in violation of relationship type cardinality
        if self.relationship.type not in (
            RelationshipTypeChoices.TYPE_MANY_TO_MANY,
            RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        ):
            # Either one-to-many or one-to-one, in either case don't allow multiple sources to the same destination
            if RelationshipAssociation.objects.filter(
                relationship=self.relationship,
                destination_type=self.destination_type,
                destination_id=self.destination_id,
            ).exists():
                raise ValidationError(
                    {
                        "destination": f"Unable to create more than one {self.relationship} association to {self.destination} (destination)"
                    }
                )

            if self.relationship.type in (
                RelationshipTypeChoices.TYPE_ONE_TO_ONE,
                RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
            ):
                # Don't allow multiple destinations from the same source
                if RelationshipAssociation.objects.filter(
                    relationship=self.relationship,
                    source_type=self.source_type,
                    source_id=self.source_id,
                ).exists():
                    raise ValidationError(
                        {
                            "source": f"Unable to create more than one {self.relationship} association to {self.source} (source)"
                        }
                    )

            if self.relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC:
                # Handle the case where the source and destination fields (which are interchangeable for a symmetric
                # relationship) are swapped around - sneaky!
                if RelationshipAssociation.objects.filter(
                    relationship=self.relationship,
                    destination_id=self.source_id,
                ).exists():
                    raise ValidationError(
                        {
                            "source": f"Unable to create more than one {self.relationship} association involving {self.source} (peer)"
                        }
                    )
                if RelationshipAssociation.objects.filter(
                    relationship=self.relationship,
                    source_id=self.destination_id,
                ).exists():
                    raise ValidationError(
                        {
                            "destination": f"Unable to create more than one {self.relationship} association involving {self.destination} (peer)"
                        }
                    )
