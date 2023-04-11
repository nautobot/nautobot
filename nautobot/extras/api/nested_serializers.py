from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import ContentTypeField
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.serializers import BaseModelSerializer, PolymorphicProxySerializer, WritableNestedSerializer
from nautobot.core.api.utils import get_serializer_for_model, get_serializers_for_models
from nautobot.core.models.utils import get_all_concrete_models
from nautobot.extras import choices, models

__all__ = [
    "NestedDynamicGroupSerializer",
    "NestedDynamicGroupMembershipSerializer",
    "NestedScheduledJobCreationSerializer",
    "NestedSecretsGroupAssociationSerializer",
    "NestedSecretSerializer",
]


class NestedDynamicGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroup-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.all(),
    )

    class Meta:
        model = models.DynamicGroup
        fields = ["id", "url", "name", "content_type"]


class NestedDynamicGroupMembershipSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroupmembership-detail")
    group = NestedDynamicGroupSerializer()
    parent_group = NestedDynamicGroupSerializer()

    class Meta:
        model = models.DynamicGroupMembership
        fields = ["id", "url", "group", "parent_group", "operator", "weight"]


class NestedScheduledJobCreationSerializer(BaseModelSerializer):
    """
    Nested serializer specifically for use with `JobInputSerializer.schedule`.

    We don't use `WritableNestedSerializer` here because this is not used to look up
    an existing `ScheduledJob`, but instead used to specify parameters for creating one.
    """

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:scheduledjob-detail")
    name = serializers.CharField(max_length=255, required=False)
    start_time = serializers.DateTimeField(format=None, required=False)

    class Meta:
        model = models.ScheduledJob
        fields = ["url", "name", "start_time", "interval", "crontab"]

    def validate(self, data):
        data = super().validate(data)

        if data["interval"] in choices.JobExecutionType.SCHEDULE_CHOICES:
            if "name" not in data:
                raise serializers.ValidationError({"name": "Please provide a name for the job schedule."})

            if ("start_time" not in data and data["interval"] != choices.JobExecutionType.TYPE_CUSTOM) or (
                "start_time" in data and data["start_time"] < models.ScheduledJob.earliest_possible_time()
            ):
                raise serializers.ValidationError(
                    {
                        "start_time": "Please enter a valid date and time greater than or equal to the current date and time."
                    }
                )

            if data["interval"] == choices.JobExecutionType.TYPE_CUSTOM:
                if data.get("crontab") is None:
                    raise serializers.ValidationError({"crontab": "Please enter a valid crontab."})
                try:
                    models.ScheduledJob.get_crontab(data["crontab"])
                except Exception as e:
                    raise serializers.ValidationError({"crontab": e})

        return data


class NestedSecretSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secret-detail")

    class Meta:
        model = models.Secret
        fields = ["id", "url", "name"]


class NestedSecretsGroupAssociationSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secretsgroupassociation-detail")

    secret = NestedSecretSerializer()

    class Meta:
        model = models.SecretsGroupAssociation
        fields = ["id", "url", "access_type", "secret_type", "secret"]
