from rest_framework import serializers

from nautobot.apps.api import WritableNestedSerializer, NautobotModelSerializer

from example_plugin.models import AnotherExampleModel, ExampleModel, ValueModel, ClassificationGroupsModel


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


class ValueModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:valuemodel-detail")

    class Meta:
        model = ValueModel
        fields = ["url", "id", "name", "value", "value_type"]


class NestedValueModelSerializer(WritableNestedSerializer):
    """Used for nested representations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:valuemodel-detail")

    class Meta:
        model = ValueModel
        fields = ["url", "id", "name"]


class ClassificationGroupsModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:example_plugin-api:classificationgroupsmodel-detail"
    )

    class Meta:
        model = ClassificationGroupsModel
        fields = ["url", "id", "name", "asset_tag", "environment", "network"]


class NestedClassificationGroupsModelSerializer(WritableNestedSerializer):
    """Used for nested representations."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:example_plugin-api:classificationgroupsmodel-detail"
    )

    class Meta:
        model = ClassificationGroupsModel
        fields = ["url", "id", "name"]
