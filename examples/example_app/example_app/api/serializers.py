from rest_framework import serializers

from nautobot.apps.api import NautobotModelSerializer

from example_app.models import AnotherExampleModel, ExampleModel, ProxyExampleModel


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


class ProxyExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_app-api:proxyexamplemodel-detail")

    class Meta:
        model = ProxyExampleModel
        fields = "__all__"
