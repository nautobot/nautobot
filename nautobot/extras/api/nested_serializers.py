from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import ContentTypeField
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.serializers import BaseModelSerializer, PolymorphicProxySerializer, WritableNestedSerializer
from nautobot.core.api.utils import get_serializer_for_model, get_serializers_for_models
from nautobot.core.models.utils import get_all_concrete_models
from nautobot.extras import choices, models
from nautobot.users.api.nested_serializers import NestedUserSerializer

__all__ = [
    "NestedDynamicGroupSerializer",
    "NestedDynamicGroupMembershipSerializer",
    "NestedNoteSerializer",
    "NestedRoleSerializer",
    "NestedScheduledJobCreationSerializer",
    "NestedSecretsGroupAssociationSerializer",
    "NestedSecretSerializer",
    "NestedStatusSerializer",
]


class NestedDynamicGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroup-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.all(),
    )

    class Meta:
        model = models.DynamicGroup
        fields = ["id", "url", "name", "slug", "content_type"]


class NestedDynamicGroupMembershipSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroupmembership-detail")
    group = NestedDynamicGroupSerializer()
    parent_group = NestedDynamicGroupSerializer()

    class Meta:
        model = models.DynamicGroupMembership
        fields = ["id", "url", "group", "parent_group", "operator", "weight"]


class NestedNoteSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:note-detail")
    user = NestedUserSerializer(read_only=True)
    assigned_object = serializers.SerializerMethodField()

    class Meta:
        model = models.Note
        fields = ["assigned_object", "id", "url", "note", "user", "slug"]

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="NoteAssignedObject",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(
                get_all_concrete_models(models.NotesMixin),
                prefix="Nested",
            ),
            allow_null=True,
        )
    )
    def get_assigned_object(self, obj):
        if obj.assigned_object is None:
            return None
        try:
            serializer = get_serializer_for_model(obj.assigned_object, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj.assigned_object, context=context).data
        except SerializerNotFound:
            return None


class NestedRoleSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:role-detail")

    class Meta:
        model = models.Role
        fields = ["id", "url", "name", "slug"]


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
        fields = ["id", "url", "name", "slug"]


class NestedSecretsGroupAssociationSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secretsgroupassociation-detail")

    secret = NestedSecretSerializer()

    class Meta:
        model = models.SecretsGroupAssociation
        fields = ["id", "url", "access_type", "secret_type", "secret"]


class NestedStatusSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:status-detail")

    class Meta:
        model = models.Status
        fields = ["id", "url", "name", "slug"]
