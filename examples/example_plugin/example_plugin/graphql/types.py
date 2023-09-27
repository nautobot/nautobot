from nautobot.apps.graphql import OptimizedNautobotObjectType

from example_plugin.models import AnotherExampleModel


class AnotherExampleModelType(OptimizedNautobotObjectType):
    class Meta:
        model = AnotherExampleModel
        exclude = ["number"]


graphql_types = [AnotherExampleModelType]
