from rest_framework import serializers
from rest_framework.serializers import Serializer

from nautobot.apps.api import NautobotModelSerializer

from example_app.models import AnotherExampleModel, ExampleModel


class AnotherExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_app-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        fields = "__all__"


class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_app-api:examplemodel-detail")

    class Meta:
        model = ExampleModel
        fields = "__all__"


class ErrorSerializer(Serializer):
    """Serializer for the error view.

    This is necessary, because otherwise the REST API schema check test fails.
    """

