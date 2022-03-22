import graphene_django_optimizer as gql_optimizer

from dummy_plugin.models import AnotherDummyModel


class AnotherDummyType(gql_optimizer.OptimizedDjangoObjectType):
    class Meta:
        model = AnotherDummyModel
        exclude = ["number"]


graphql_types = [AnotherDummyType]
