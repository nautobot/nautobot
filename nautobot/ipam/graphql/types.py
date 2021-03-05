import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field

from nautobot.ipam.fields import IPAddressField, IPNetworkField, VarbinaryIPField
from nautobot.ipam.models import IPAddress
from nautobot.ipam.filters import IPAddressFilterSet
from nautobot.extras.graphql.types import TagType  # noqa: F401


class IPAddressType(DjangoObjectType):
    """Graphql Type Object for IPAddress model."""

    class Meta:
        model = IPAddress
        filterset_class = IPAddressFilterSet
