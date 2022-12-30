from rest_framework import serializers

from nautobot.apps.api import WritableNestedSerializer, NautobotModelSerializer

from example_plugin.models import AnotherExampleModel, ExampleModel


class AnotherExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        fields = ["url", "id", "name", "number"]


class NestedAnotherExampleModelSerializer(WritableNestedSerializer):
    """Used for nested representations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        fields = ["url", "id", "name"]


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
