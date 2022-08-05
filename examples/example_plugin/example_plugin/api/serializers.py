from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.extras.api.serializers import NautobotModelSerializer

from example_plugin.models import ExampleModel


class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:examplemodel-detail")

    class Meta:
        model = ExampleModel
        fields = ["url", "id", "name", "number"]


class NestedExampleModelSerializer(WritableNestedSerializer):
    """Used for nested representations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:examplemodel-detail")

    class Meta:
        model = ExampleModel
        fields = ["url", "id", "name"]
