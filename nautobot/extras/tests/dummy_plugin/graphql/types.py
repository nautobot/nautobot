from graphene_django import DjangoObjectType
from nautobot.extras.tests.dummy_plugin.models import AnotherDummyModel


class AnotherDummyType(DjangoObjectType):
    class Meta:
        model = AnotherDummyModel
        exclude = ["number"]


graphql_types = [AnotherDummyType]
