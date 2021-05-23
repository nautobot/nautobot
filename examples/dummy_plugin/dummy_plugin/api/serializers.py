from rest_framework import serializers

from nautobot.core.api import ValidatedModelSerializer

from dummy_plugin.models import DummyModel


class DummySerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:dummy_plugin-api:dummymodel-detail"
    )

    class Meta:
        model = DummyModel
        fields = ("url", "id", "name", "number")
