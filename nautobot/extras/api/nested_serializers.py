from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from nautobot.core.api import ChoiceField, ContentTypeField, WritableNestedSerializer
from nautobot.extras import choices, models
from nautobot.users.api.nested_serializers import NestedUserSerializer

__all__ = [
    "NestedConfigContextSerializer",
    "NestedConfigContextSchemaSerializer",
    "NestedCustomFieldSerializer",
    "NestedCustomLinkSerializer",
    "NestedExportTemplateSerializer",
    "NestedGitRepositorySerializer",
    "NestedGraphQLQuerySerializer",
    "NestedImageAttachmentSerializer",
    "NestedJobResultSerializer",
    "NestedRelationshipSerializer",
    "NestedRelationshipAssociationSerializer",
    "NestedStatusSerializer",
    "NestedTagSerializer",
    "NestedWebhookSerializer",
]


class NestedCustomFieldSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfield-detail")

    class Meta:
        model = models.CustomField
        fields = ["id", "url", "name"]


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


class NestedImageAttachmentSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:imageattachment-detail")

    class Meta:
        model = models.ImageAttachment
        fields = ["id", "url", "name", "image"]


class NestedTagSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:tag-detail")

    class Meta:
        model = models.Tag
        fields = ["id", "url", "name", "slug", "color"]


class NestedJobResultSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobresult-detail")
    status = ChoiceField(choices=choices.JobResultStatusChoices)
    user = NestedUserSerializer(read_only=True)

    class Meta:
        model = models.JobResult
        fields = ["url", "created", "completed", "user", "status"]


class NestedCustomLinkSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customlink-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.all(),
    )

    class Meta:
        model = models.CustomLink
        fields = ["content_type", "id", "name", "url"]


class NestedWebhookSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:webhook-detail")

    class Meta:
        model = models.Webhook
        fields = ["id", "url", "name"]


class NestedStatusSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:status-detail")

    class Meta:
        model = models.Status
        fields = ["id", "url", "name", "slug"]


class NestedRelationshipSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:relationship-detail")

    class Meta:
        model = models.Relationship
        fields = ["id", "url", "name", "slug"]


class NestedGraphQLQuerySerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:graphqlquery-detail")

    class Meta:
        model = models.GraphQLQuery
        fields = ["id", "url", "name"]


class NestedRelationshipAssociationSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:relationshipassociation-detail")

    class Meta:
        model = models.RelationshipAssociation
        fields = ["id", "url", "relationship", "source_id", "destination_id"]
