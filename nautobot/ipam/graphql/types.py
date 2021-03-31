import graphene

from graphene_django import DjangoObjectType

from nautobot.ipam.models import IPAddress
from nautobot.ipam.filters import IPAddressFilterSet
from nautobot.extras.graphql.types import TagType  # noqa: F401


class IPAddressType(DjangoObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()

    class Meta:
        model = IPAddress
        filterset_class = IPAddressFilterSet
