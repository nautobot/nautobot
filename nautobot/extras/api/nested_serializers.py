from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import ChoiceField, ContentTypeField
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.serializers import BaseModelSerializer, PolymorphicProxySerializer, WritableNestedSerializer
from nautobot.core.api.utils import get_serializer_for_model, get_serializers_for_models
from nautobot.core.models.utils import get_all_concrete_models
from nautobot.extras import choices, models
from nautobot.users.api.nested_serializers import NestedUserSerializer

__all__ = [
    "NestedComputedFieldSerializer",
    "NestedConfigContextSerializer",
    "NestedConfigContextSchemaSerializer",
    "NestedCustomFieldSerializer",
    "NestedCustomLinkSerializer",
    "NestedDynamicGroupSerializer",
    "NestedExportTemplateSerializer",
    "NestedGitRepositorySerializer",
    "NestedGraphQLQuerySerializer",
    "NestedImageAttachmentSerializer",
    "NestedJobSerializer",
    "NestedJobLogEntrySerializer",
    "NestedJobResultSerializer",
    "NestedNoteSerializer",
    "NestedRelationshipSerializer",
    "NestedRelationshipAssociationSerializer",
    "NestedRoleSerializer",
    "NestedScheduledJobSerializer",
    "NestedSecretsGroupAssociationSerializer",
    "NestedSecretSerializer",
    "NestedSecretsGroupSerializer",
    "NestedStatusSerializer",
    "NestedTagSerializer",
    "NestedWebhookSerializer",
    "NestedJobHookSerializer",
]


class NestedComputedFieldSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:computedfield-detail")
    content_type = ContentTypeField(queryset=ContentType.objects.all())

    class Meta:
        model = models.ComputedField
        fields = ["id", "url", "content_type", "label"]


class NestedConfigContextSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:configcontext-detail")

    class Meta:
        model = models.ConfigContext
        fields = ["id", "url", "name"]


class NestedConfigContextSchemaSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:configcontextschema-detail")

    class Meta:
        model = models.ConfigContextSchema
        fields = ["id", "url", "name", "slug"]


class NestedCustomFieldSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfield-detail")

    class Meta:
        model = models.CustomField
        fields = ["id", "url", "key"]


class NestedCustomFieldChoiceSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfieldchoice-detail")

    class Meta:
        model = models.CustomFieldChoice
        fields = ["id", "url"]


class NestedCustomLinkSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customlink-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.all(),
    )

    class Meta:
        model = models.CustomLink
        fields = ["content_type", "id", "name", "url"]


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


class NestedExportTemplateSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:exporttemplate-detail")

    class Meta:
        model = models.ExportTemplate
        fields = ["id", "url", "name"]


class NestedGitRepositorySerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:gitrepository-detail")

    class Meta:
        model = models.GitRepository
        fields = ["id", "url", "name"]


class NestedGraphQLQuerySerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:graphqlquery-detail")

    class Meta:
        model = models.GraphQLQuery
        fields = ["id", "url", "name"]


class NestedImageAttachmentSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:imageattachment-detail")

    class Meta:
        model = models.ImageAttachment
        fields = ["id", "url", "name", "image"]


class NestedJobSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:job-detail")

    class Meta:
        model = models.Job
        fields = ["id", "url", "source", "module_name", "job_class_name", "grouping", "name", "slug"]


class NestedJobHookSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobhook-detail")

    class Meta:
        model = models.JobHook
        fields = ["id", "url", "name"]


class NestedJobButtonSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobbutton-detail")

    class Meta:
        model = models.JobButton
        fields = ["id", "url", "name"]


class NestedJobLogEntrySerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:joblogentry-detail")

    class Meta:
        model = models.JobLogEntry
        fields = [
            "id",
            "url",
            "absolute_url",
            "created",
            "grouping",
            "log_level",
            "log_object",
            "message",
        ]


class NestedJobResultSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobresult-detail")
    status = ChoiceField(choices=choices.JobResultStatusChoices)
    user = NestedUserSerializer(read_only=True)

    class Meta:
        model = models.JobResult
        fields = ["id", "url", "name", "date_created", "date_done", "user", "status"]


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


class NestedRelationshipSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:relationship-detail")

    class Meta:
        model = models.Relationship
        fields = ["id", "url", "name", "slug"]


class NestedRelationshipAssociationSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:relationshipassociation-detail")

    class Meta:
        model = models.RelationshipAssociation
        fields = ["id", "url", "relationship", "source_id", "destination_id"]


class NestedRoleSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:role-detail")

    class Meta:
        model = models.Role
        fields = ["id", "url", "name", "slug"]


class NestedScheduledJobSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:scheduledjob-detail")
    name = serializers.CharField(max_length=255, required=False)
    start_time = serializers.DateTimeField(format=None, required=False)

    class Meta:
        model = models.ScheduledJob
        fields = ["url", "name", "start_time", "interval", "crontab"]


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


class NestedSecretsGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secretsgroup-detail")

    class Meta:
        model = models.SecretsGroup
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


class NestedTagSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:tag-detail")

    class Meta:
        model = models.Tag
        fields = ["id", "url", "name", "slug", "color"]


class NestedWebhookSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:webhook-detail")

    class Meta:
        model = models.Webhook
        fields = ["id", "url", "name"]
