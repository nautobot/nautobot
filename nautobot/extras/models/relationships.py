import logging

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.safestring import mark_safe

from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.extras.choices import RelationshipTypeChoices, RelationshipRequiredSideChoices, RelationshipSideChoices
from nautobot.extras.utils import FeatureQuery, extras_features
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.models.mixins import NotesMixin
from nautobot.utilities.utils import get_filterset_for_model, get_route_for_model, slugify_dashes_to_underscores
from nautobot.utilities.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    widgets,
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

    @property
    def associations(self):
        return list(self.source_for_associations.all()) + list(self.destination_for_associations.all())

    def get_relationships(self, include_hidden=False, advanced_ui=None):
        """
        Return a dictionary of RelationshipAssociation querysets for all custom relationships

        Returns:
            response {
                "source": {
                    <Relationship instance #1>: <RelationshipAssociation queryset #1>,
                    <Relationship instance #2>: <RelationshipAssociation queryset #2>,
                },
                "destination": {
                    <Relationship instance #3>: <RelationshipAssociation queryset #3>,
                    <Relationship instance #4>: <RelationshipAssociation queryset #4>,
                },
                "peer": {
                    <Relationship instance #5>: <RelationshipAssociation queryset #5>,
                    <Relationship instance #6>: <RelationshipAssociation queryset #6>,
                },
            }
        """
        src_relationships, dst_relationships = Relationship.objects.get_for_model(self)
        if advanced_ui is not None:
            src_relationships = src_relationships.filter(advanced_ui=advanced_ui)
            dst_relationships = dst_relationships.filter(advanced_ui=advanced_ui)
        content_type = ContentType.objects.get_for_model(self)

        sides = {
            RelationshipSideChoices.SIDE_SOURCE: src_relationships,
            RelationshipSideChoices.SIDE_DESTINATION: dst_relationships,
        }

        resp = {
            RelationshipSideChoices.SIDE_SOURCE: {},
            RelationshipSideChoices.SIDE_DESTINATION: {},
            RelationshipSideChoices.SIDE_PEER: {},
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

    def get_relationships_data(self, **kwargs):
        """
        Return a dictionary of relationships with the label and the value or the queryset for each.

        Used for rendering relationships in the UI; see nautobot/core/templates/inc/relationships_table_rows.html

        Returns:
            response {
                "source": {
                    <Relationship instance #1>: {   # one-to-one relationship that self is the source of
                        "label": "...",
                        "peer_type": <ContentType>,
                        "has_many": False,
                        "value": <model instance>,     # single destination for this relationship
                        "url": "...",
                    },
                    <Relationship instance #2>: {   # one-to-many or many-to-many relationship that self is a source for
                        "label": "...",
                        "peer_type": <ContentType>,
                        "has_many": True,
                        "value": None,
                        "queryset": <RelationshipAssociation queryset #2>   # set of destinations for the relationship
                    },
                },
                "destination": {
                    (same format as "source" dict - relationships that self is the destination of)
                },
                "peer": {
                    (same format as "source" dict - symmetric relationships that self is involved in)
                },
            }
        """

        relationships_by_side = self.get_relationships(**kwargs)

        resp = {
            RelationshipSideChoices.SIDE_SOURCE: {},
            RelationshipSideChoices.SIDE_DESTINATION: {},
            RelationshipSideChoices.SIDE_PEER: {},
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
                    resp[side][relationship]["peer_type"] = getattr(relationship, "source_type")

                resp[side][relationship]["has_many"] = relationship.has_many(peer_side)

                if resp[side][relationship]["has_many"]:
                    resp[side][relationship]["queryset"] = queryset
                else:
                    resp[side][relationship]["url"] = None
                    association = queryset.first()
                    if not association:
                        continue

                    peer = association.get_peer(self)

                    resp[side][relationship]["value"] = peer
                    if hasattr(peer, "get_absolute_url"):
                        resp[side][relationship]["url"] = peer.get_absolute_url()
                    else:
                        logger.warning("Peer object %s has no get_absolute_url() method", peer)

        return resp

    def get_relationships_data_basic_fields(self):
        """
        Same docstring as get_relationships_data() above except this only returns relationships
        where advanced_ui==False for displaying in the main object detail tab on the object's page
        """
        return self.get_relationships_data(advanced_ui=False)

    def get_relationships_data_advanced_fields(self):
        """
        Same docstring as get_relationships_data() above except this only returns relationships
        where advanced_ui==True for displaying in the 'Advanced' tab on the object's page
        """
        return self.get_relationships_data(advanced_ui=True)

    @classmethod
    def required_related_objects_errors(
        cls, output_for="ui", initial_data=None, relationships_key_specified=False, instance=None
    ):
        """
        Args:
            output_for: either "ui" or "api" depending on usage
            initial_data: submitted form/serializer data to validate against
            relationships_key_specified: if the "relationships" key was provided or not
            instance: an optional model instance to validate against
        Returns:
            List of field error dicts if any are found
        """

        required_relationships = Relationship.objects.get_required_for_model(cls)
        relationships_field_errors = []
        for relation in required_relationships:

            opposite_side = RelationshipSideChoices.OPPOSITE[relation.required_on]

            if relation.skip_required(cls, opposite_side):
                continue

            if relation.has_many(opposite_side):
                num_required_verbose = "at least one"
            else:
                num_required_verbose = "a"

            if output_for == "api":
                # If this is a model instance and the relationships json data key is missing, check to see if
                # required relationship associations already exist, and continue (ignore validation) if so
                if (
                    getattr(instance, "present_in_database", False) is True
                    and initial_data.get(relation, {}).get(opposite_side, {}) == {}
                    and not relationships_key_specified
                ):
                    if (
                        RelationshipAssociation.objects.filter(**{f"{relation.required_on}_id": instance.pk}).count()
                        > 0
                    ):
                        continue

            required_model_class = getattr(relation, f"{opposite_side}_type").model_class()
            required_model_meta = required_model_class._meta
            cr_field_name = f"cr_{relation.slug}__{opposite_side}"
            name_plural = cls._meta.verbose_name_plural
            field_key = relation.slug if output_for == "api" else cr_field_name
            field_errors = {field_key: []}

            if not required_model_class.objects.exists():

                hint = (
                    f"You need to create {num_required_verbose} {required_model_meta.verbose_name} "
                    f"before instantiating a {cls._meta.verbose_name}."
                )

                if output_for == "ui":
                    try:
                        add_url = reverse(get_route_for_model(required_model_class, "add"))
                        hint = (
                            f"<a target='_blank' href='{add_url}'>Click here</a> to create "
                            f"a {required_model_meta.verbose_name}."
                        )
                    except NoReverseMatch:
                        pass

                elif output_for == "api":
                    try:
                        api_post_url = reverse(get_route_for_model(required_model_class, "list", api=True))
                        hint = f"Create a {required_model_meta.verbose_name} by posting to {api_post_url}"
                    except NoReverseMatch:
                        pass

                error_message = mark_safe(
                    f"{name_plural[0].upper()}{name_plural[1:]} require "
                    f"{num_required_verbose} {required_model_meta.verbose_name}, but no "
                    f"{required_model_meta.verbose_name_plural} exist yet. {hint}"
                )
                field_errors[field_key].append(error_message)

            if initial_data is not None:

                supplied_data = []

                if output_for == "ui":
                    supplied_data = initial_data.get(field_key, [])
                elif output_for == "api":
                    supplied_data = initial_data.get(relation, {}).get(opposite_side, {})

                if not supplied_data:
                    if output_for == "ui":
                        field_errors[field_key].append(
                            f"You need to select {num_required_verbose} {required_model_meta.verbose_name}."
                        )
                    elif output_for == "api":
                        field_errors[field_key].append(
                            f'You need to specify relationships["{relation.slug}"]["{opposite_side}"]["objects"].'
                        )

            if len(field_errors[field_key]) > 0:
                relationships_field_errors.append(field_errors)

        return relationships_field_errors


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

    def get_required_for_model(self, model):
        """
        Return a queryset with all required Relationships on the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.get_queryset().filter(
            Q(source_type=content_type, required_on=RelationshipRequiredSideChoices.SOURCE_SIDE_REQUIRED)
            | Q(destination_type=content_type, required_on=RelationshipRequiredSideChoices.DESTINATION_SIDE_REQUIRED)
        )


class Relationship(BaseModel, ChangeLoggedModel, NotesMixin):

    name = models.CharField(max_length=100, unique=True, help_text="Name of the relationship as displayed to users")
    slug = AutoSlugField(
        populate_from="name",
        slugify_function=slugify_dashes_to_underscores,
        help_text="Internal relationship name. Please use underscores rather than dashes in this slug.",
    )
    description = models.CharField(max_length=200, blank=True)
    type = models.CharField(
        max_length=50,
        choices=RelationshipTypeChoices,
        default=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        help_text="Cardinality of this relationship",
    )
    required_on = models.CharField(
        max_length=12,
        choices=RelationshipRequiredSideChoices,
        default=RelationshipRequiredSideChoices.NEITHER_SIDE_REQUIRED,
        help_text="Objects on the specified side MUST implement this relationship. "
        "Not permitted for symmetric relationships.",
        blank=True,
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
        help_text="Filterset filter matching the applicable source objects of the selected type",
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
        help_text="Filterset filter matching the applicable destination objects of the selected type",
    )
    advanced_ui = models.BooleanField(
        default=False,
        verbose_name="Move to Advanced tab",
        help_text="Hide this field from the object's primary information tab. "
        'It will appear in the "Advanced" tab instead.',
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

    @property
    def peer_type(self):
        """Virtual attribute for symmetric relationships only."""
        if self.symmetric:
            return self.source_type
        return None

    def get_absolute_url(self):
        return reverse("extras:relationship", args=[self.slug])

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
            if not destination_model:  # perhaps a plugin was uninstalled?
                return str(self)
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
            if not source_model:  # perhaps a plugin was uninstalled?
                return str(self)
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
            object_type = getattr(self, "source_type")
            filters = getattr(self, "source_filter") or {}

        model_class = object_type.model_class()
        if model_class:
            queryset = model_class.objects.all()
        else:  # maybe a relationship to a model that no longer exists, such as a removed plugin?
            queryset = None

        field_class = None
        if queryset:
            if self.has_many(peer_side):
                field_class = DynamicModelMultipleChoiceField
            else:
                field_class = DynamicModelChoiceField

            field = field_class(queryset=queryset, query_params=filters)
        else:
            field = forms.MultipleChoiceField(widget=widgets.StaticSelect2Multiple)

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

            filter_ = getattr(self, f"{side}_filter")
            side_model = getattr(self, f"{side}_type").model_class()
            if not side_model:  # can happen if for example a plugin providing the model was uninstalled
                raise ValidationError({f"{side}_type": "Unable to locate model class"})
            model_name = side_model._meta.label
            if not isinstance(filter_, dict):
                raise ValidationError({f"{side}_filter": f"Filter for {model_name} must be a dictionary"})

            filterset_class = get_filterset_for_model(side_model)
            if not filterset_class:
                raise ValidationError(
                    {
                        f"{side}_filter": f"Filters are not supported for {model_name} object (Unable to find a FilterSet)"
                    }
                )
            filterset = filterset_class(filter_, side_model.objects.all())

            error_messages = []
            if filterset.errors:
                for key in filterset.errors:
                    # When settings.STRICT_FILTERING is True, any extraneous filter parameters will result in
                    # filterset.errors[key] = ["Unknown filter field"]
                    # This is redundant with our custom (more specific) error message added below from filterset_params
                    # So discard such a message if present.
                    errors_list = [error for error in filterset.errors[key] if "Unknown filter field" not in str(error)]
                    if errors_list:
                        error_messages.append(f"'{key}': " + ", ".join(errors_list))

            filterset_params = set(filterset.filters.keys())
            for key in filter_.keys():
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

            # Marking a relationship as required is unsupported for symmetric relationships
            if self.required_on != "":
                error_messages["required_on"] = "Symmetric relationships cannot be marked as required."

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

    def skip_required(self, referenced_instance_or_class, side):
        """
        This takes an instance or class and a side and checks if it should
        be skipped or not when validating required relationships.
        It will skip when any of the following conditions are True:
         - a relationship is marked as symmetric
         - if a required model class is None (if it doesn't exist yet -- unimplemented/uninstalled plugins for instance)

        Args:
            referenced_instance_or_class: model instance or class
            side: side of the relationship being checked

        Returns: Bool
        """

        # Not enforcing required symmetric relationships
        if self.symmetric:
            return True

        required_model_class = getattr(self, f"{RelationshipSideChoices.OPPOSITE[side]}_type").model_class()
        # Handle the case where required_model_class is None (e.g., relationship to a plugin
        # model for a plugin that's not installed at present):
        if required_model_class is None:
            logger.info("Relationship enforcement skipped as required model class doesn't exist yet.")
            return True

        return False


@extras_features("custom_validators")
class RelationshipAssociation(BaseModel):
    relationship = models.ForeignKey(to="extras.Relationship", on_delete=models.CASCADE, related_name="associations")

    source_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE, related_name="+")
    source_id = models.UUIDField(db_index=True)
    source = GenericForeignKey(ct_field="source_type", fk_field="source_id")

    destination_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE, related_name="+")
    destination_id = models.UUIDField(db_index=True)
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
        arrow = "<->" if self.relationship.symmetric else "->"
        return f"{self.get_source() or 'unknown'} {arrow} {self.get_destination() or 'unknown'} - {self.relationship}"

    def _get_genericforeignkey(self, name):
        """
        Backend for get_source and get_destination methods.

        In the case where we have a RelationshipAssociation to a plugin-provided model, but the plugin is
        not presently installed/enabled, dereferencing the peer GenericForeignKey will throw an AttributeError:
            AttributeError: 'NoneType' object has no attribute '_base_manager'
        because ContentType.model_class() returned None unexpectedly.

        This method handles that exception and returns None in such a case.
        """
        if name not in ["source", "destination"]:
            raise RuntimeError(f"Called for unexpected attribute {name}")
        try:
            return getattr(self, name)
        except AttributeError:
            logger.error(
                "Unable to locate RelationshipAssociation %s (of type %s). Perhaps a plugin is missing?",
                name,
                getattr(self, f"{name}_type"),
            )

        return None

    def get_source(self):
        """Accessor for self.source - returns None if the object cannot be located."""
        return self._get_genericforeignkey("source")

    def get_destination(self):
        """Accessor for self.destination - returns None if the object cannot be located."""
        return self._get_genericforeignkey("destination")

    def get_peer(self, obj):
        """
        Get the object on the opposite side of this RelationshipAssociation from the provided `obj`.

        If obj is not involved in this RelationshipAssociation, or if the peer object is not locatable, returns None.
        """
        if obj == self.get_source():
            return self.get_destination()
        elif obj == self.get_destination():
            return self.get_source()

        return None

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
                        "__all__": (
                            f"A {self.relationship} association already exists between "
                            f"{self.get_source() or self.source_id} and "
                            f"{self.get_destination() or self.destination_id}"
                        )
                    }
                )

        # Check if a similar relationship association already exists in violation of relationship type cardinality
        if self.relationship.type not in (
            RelationshipTypeChoices.TYPE_MANY_TO_MANY,
            RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        ):
            # Either one-to-many or one-to-one, in either case don't allow multiple sources to the same destination
            if (
                RelationshipAssociation.objects.filter(
                    relationship=self.relationship,
                    destination_type=self.destination_type,
                    destination_id=self.destination_id,
                )
                .exclude(pk=self.pk)
                .exists()
            ):
                raise ValidationError(
                    {
                        "destination": (
                            f"Unable to create more than one {self.relationship} association to "
                            f"{self.get_destination() or self.destination_id} (destination)"
                        )
                    }
                )

            if self.relationship.type in (
                RelationshipTypeChoices.TYPE_ONE_TO_ONE,
                RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
            ):
                # Don't allow multiple destinations from the same source
                if (
                    RelationshipAssociation.objects.filter(
                        relationship=self.relationship,
                        source_type=self.source_type,
                        source_id=self.source_id,
                    )
                    .exclude(pk=self.pk)
                    .exists()
                ):
                    raise ValidationError(
                        {
                            "source": (
                                f"Unable to create more than one {self.relationship} association from "
                                f"{self.get_source() or self.source_id} (source)"
                            )
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
                            "source": (
                                f"Unable to create more than one {self.relationship} association involving "
                                f"{self.get_source() or self.source_id} (peer)"
                            )
                        }
                    )
                if RelationshipAssociation.objects.filter(
                    relationship=self.relationship,
                    source_id=self.destination_id,
                ).exists():
                    raise ValidationError(
                        {
                            "destination": (
                                f"Unable to create more than one {self.relationship} association involving "
                                f"{self.get_destination() or self.destination_id} (peer)"
                            )
                        }
                    )

        if self.relationship.destination_filter or self.relationship.source_filter:
            self._validate_relationship_filter_restriction()

    def _validate_relationship_filter_restriction(self):
        """Validate relationship association do not violate filter restrictions"""
        sides = []

        if self.relationship.destination_filter:
            sides.append("destination")

        if self.relationship.source_filter:
            sides.append("source")

        for side_name in sides:
            side = getattr(self, side_name)  # destination / source
            side_filter = getattr(self.relationship, f"{side_name}_filter")

            filterset_class = get_filterset_for_model(side.__class__)
            filterset = filterset_class(side_filter, side.__class__.objects.all())
            queryset = filterset.qs.filter(id=side.id)

            if queryset.exists() is False:
                raise ValidationError(
                    {side_name: (f"{side} violates {self.relationship} {side_name}_filter restriction")}
                )
