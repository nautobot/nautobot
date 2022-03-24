from rest_framework import serializers

from nautobot.core.api import ValidatedModelSerializer, WritableNestedSerializer

from example_plugin.models import ExampleModel


class ExampleModelSerializer(ValidatedModelSerializer):
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
