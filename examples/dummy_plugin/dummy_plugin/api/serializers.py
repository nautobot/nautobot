from rest_framework import serializers

from nautobot.core.api import ValidatedModelSerializer, WritableNestedSerializer

from dummy_plugin.models import DummyModel


class DummyModelSerializer(ValidatedModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:dummy_plugin-api:dummymodel-detail")

    class Meta:
        model = DummyModel
        fields = ["url", "id", "name", "number"]


class NestedDummyModelSerializer(WritableNestedSerializer):
    """Used for nested representations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:dummy_plugin-api:dummymodel-detail")

    class Meta:
        model = DummyModel
        fields = ["url", "id", "name"]
