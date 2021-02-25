import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field

from nautobot.ipam.fields import IPAddressField, IPNetworkField
from nautobot.ipam.models import IPAddress
from nautobot.ipam.filters import IPAddressFilterSet
from nautobot.extras.graphql.types import TagType  # noqa: F401


@convert_django_field.register(IPAddressField)
def convert_field_to_string(field, registry=None):
    """Convert IPAddressField to String."""
    return graphene.String()


@convert_django_field.register(IPNetworkField)
def convert_field_to_string(field, registry=None):  # noqa: F811
    """Convert IPNetworkField to String."""
    return graphene.String()


class IPAddressType(DjangoObjectType):
    """Graphql Type Object for IPAddress model."""

    class Meta:
        model = IPAddress
        filterset_class = IPAddressFilterSet
