import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field, convert_field_to_string

from nautobot.ipam import models, filters, fields
from nautobot.extras.graphql.types import TagType  # noqa: F401


# Register VarbinaryIPField to be converted to a string type
convert_django_field.register(fields.VarbinaryIPField)(convert_field_to_string)


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
