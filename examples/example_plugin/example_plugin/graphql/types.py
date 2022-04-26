import graphene_django_optimizer as gql_optimizer

from example_plugin.models import AnotherExampleModel


class AnotherExampleModelType(gql_optimizer.OptimizedDjangoObjectType):
    class Meta:
        model = AnotherExampleModel
        exclude = ["number"]


graphql_types = [AnotherExampleModelType]
