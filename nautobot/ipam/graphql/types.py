import graphene
from graphene_django import DjangoObjectType

from nautobot.ipam import models, filters
from nautobot.extras.graphql.types import TagType  # noqa: F401


class AggregateType(DjangoObjectType):
    """Graphql Type Object for Aggregate model."""

    prefix = graphene.String()

    class Meta:
        model = models.Aggregate
        filterset_class = filters.AggregateFilterSet


class IPAddressType(DjangoObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()

    class Meta:
        model = models.IPAddress
        filterset_class = filters.IPAddressFilterSet


class PrefixType(DjangoObjectType):
    """Graphql Type Object for Prefix model."""

    prefix = graphene.String()

    class Meta:
        model = models.Prefix
        filterset_class = filters.PrefixFilterSet
