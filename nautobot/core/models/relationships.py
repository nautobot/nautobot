from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

from nautobot.core.utils import get_filterset_for_model, get_route_for_model


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
        # Avoid circular import
        from nautobot.extras.choices import RelationshipSideChoices
        from nautobot.extras.models import Relationship, RelationshipAssociation

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
        # Avoid circular import
        from nautobot.extras.choices import RelationshipSideChoices
        from nautobot.extras.models.relationships import logger

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
        # Avoid circular import
        from nautobot.extras.choices import RelationshipSideChoices
        from nautobot.extras.models import Relationship, RelationshipAssociation

        required_relationships = Relationship.objects.get_required_for_model(cls)
        relationships_field_errors = {}
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
                    filter_kwargs = {"relationship": relation, f"{relation.required_on}_id": instance.pk}
                    if RelationshipAssociation.objects.filter(**filter_kwargs).exists():
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
                            f'You need to specify ["relationships"]["{relation.slug}"]["{opposite_side}"]["objects"].'
                        )

            if len(field_errors[field_key]) > 0:
                relationships_field_errors[field_key] = field_errors[field_key]

        return relationships_field_errors
