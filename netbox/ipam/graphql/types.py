import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field

from ipam.fields import IPAddressField, IPNetworkField
from ipam.models import IPAddress
from ipam.filters import IPAddressFilterSet
from extras.graphql.types import TagType


@convert_django_field.register(IPAddressField)
def convert_field_to_string(field, registry=None):
    """Convert IPAddressField to String."""
    return graphene.String()


@convert_django_field.register(IPNetworkField)
def convert_field_to_string(field, registry=None):
    """Convert IPNetworkField to String."""
    return graphene.String()


class IPAddressType(DjangoObjectType):
    """Graphql Type Object for IPAddress model."""
    class Meta:
        model = IPAddress
        filterset_class = IPAddressFilterSet
