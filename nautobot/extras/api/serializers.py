from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from drf_yasg.utils import swagger_serializer_method
from graphene_django.settings import graphene_settings
from graphql import get_default_backend
from graphql.error import GraphQLSyntaxError
from rest_framework import serializers

from nautobot.core.api import (
    ChoiceField,
    ContentTypeField,
    SerializedPKRelatedField,
    ValidatedModelSerializer,
)
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceSerializer,
    NestedDeviceRoleSerializer,
    NestedPlatformSerializer,
    NestedRackSerializer,
    NestedRegionSerializer,
    NestedSiteSerializer,
)
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Platform, Rack, Region, Site
from nautobot.extras.choices import *
from nautobot.extras.datasources import get_datasource_content_choices
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.api.fields import StatusSerializerField
from nautobot.extras.utils import FeatureQuery
from nautobot.tenancy.api.nested_serializers import (
    NestedTenantSerializer,
    NestedTenantGroupSerializer,
)
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.api.nested_serializers import NestedUserSerializer
from nautobot.utilities.api import get_serializer_for_model
from nautobot.virtualization.api.nested_serializers import (
    NestedClusterGroupSerializer,
    NestedClusterSerializer,
)
from nautobot.virtualization.models import Cluster, ClusterGroup
from .customfields import CustomFieldModelSerializer
from .fields import MultipleChoiceJSONField
from .nested_serializers import *


#
# Custom fields
#


class CustomFieldSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfield-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()),
        many=True,
    )
    type = ChoiceField(choices=CustomFieldTypeChoices)
    filter_logic = ChoiceField(choices=CustomFieldFilterLogicChoices, required=False)

    class Meta:
        model = CustomField
        fields = [
            "id",
            "url",
            "content_types",
            "type",
            "name",
            "label",
            "description",
            "required",
            "filter_logic",
            "default",
            "weight",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
        ]


class CustomFieldChoiceSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfieldchoice-detail")
    field = NestedCustomFieldSerializer()

    class Meta:
        model = CustomFieldChoice
        fields = ["id", "url", "field", "value", "weight"]


#
# Export templates
#


class ExportTemplateSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:exporttemplate-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()),
    )
    owner_content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("export_template_owners").get_query()),
        required=False,
        allow_null=True,
        default=None,
    )
    owner = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ExportTemplate
        fields = [
            "id",
            "url",
            "content_type",
            "owner_content_type",
            "owner_object_id",
            "owner",
            "name",
            "description",
            "template_code",
            "mime_type",
            "file_extension",
        ]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        serializer = get_serializer_for_model(obj.owner, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.owner, context=context).data


#
# Tags
#


class TagSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:tag-detail")
    tagged_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "color",
            "description",
            "tagged_items",
            "custom_fields",
            "created",
            "last_updated",
        ]


class TaggedObjectSerializer(serializers.Serializer):
    tags = NestedTagSerializer(many=True, required=False)

    def create(self, validated_data):
        tags = validated_data.pop("tags", None)
        instance = super().create(validated_data)

        if tags is not None:
            return self._save_tags(instance, tags)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        # Cache tags on instance for change logging
        instance._tags = tags or []

        instance = super().update(instance, validated_data)

        if tags is not None:
            return self._save_tags(instance, tags)
        return instance

    def _save_tags(self, instance, tags):
        if tags:
            instance.tags.set(*[t.name for t in tags])
        else:
            instance.tags.clear()

        return instance


#
# Git repositories
#


class GitRepositorySerializer(CustomFieldModelSerializer):
    """Git repositories defined as a data source."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:gitrepository-detail")
    token = serializers.CharField(source="_token", write_only=True, required=False)

    provided_contents = MultipleChoiceJSONField(
        choices=get_datasource_content_choices("extras.gitrepository"),
        allow_blank=True,
        required=False,
    )

    class Meta:
        model = GitRepository
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "remote_url",
            "branch",
            "token",
            "username",
            "current_head",
            "provided_contents",
            "created",
            "last_updated",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]

    def validate(self, data):
        """
        Add the originating Request as a parameter to be passed when creating/updating a GitRepository.
        """
        data["request"] = self.context["request"]
        return super().validate(data)


#
# Image attachments
#


class ImageAttachmentSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:imageattachment-detail")
    content_type = ContentTypeField(queryset=ContentType.objects.all())
    parent = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ImageAttachment
        fields = [
            "id",
            "url",
            "content_type",
            "object_id",
            "parent",
            "name",
            "image",
            "image_height",
            "image_width",
            "created",
        ]

    def validate(self, data):

        # Validate that the parent object exists
        try:
            data["content_type"].get_object_for_this_type(id=data["object_id"])
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                "Invalid parent object: {} ID {}".format(data["content_type"], data["object_id"])
            )

        # Enforce model validation
        super().validate(data)

        return data

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_parent(self, obj):

        # Static mapping of models to their nested serializers
        if isinstance(obj.parent, Device):
            serializer = NestedDeviceSerializer
        elif isinstance(obj.parent, Rack):
            serializer = NestedRackSerializer
        elif isinstance(obj.parent, Site):
            serializer = NestedSiteSerializer
        else:
            raise Exception("Unexpected type of parent object for ImageAttachment")

        return serializer(obj.parent, context={"request": self.context["request"]}).data


#
# Config contexts
#


class ConfigContextSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:configcontext-detail")
    owner_content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("config_context_owners").get_query()),
        required=False,
        allow_null=True,
        default=None,
    )
    owner = serializers.SerializerMethodField(read_only=True)
    schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)
    regions = SerializedPKRelatedField(
        queryset=Region.objects.all(),
        serializer=NestedRegionSerializer,
        required=False,
        many=True,
    )
    sites = SerializedPKRelatedField(
        queryset=Site.objects.all(),
        serializer=NestedSiteSerializer,
        required=False,
        many=True,
    )
    roles = SerializedPKRelatedField(
        queryset=DeviceRole.objects.all(),
        serializer=NestedDeviceRoleSerializer,
        required=False,
        many=True,
    )
    device_types = SerializedPKRelatedField(
        queryset=DeviceType.objects.all(),
        serializer=NestedDeviceRoleSerializer,
        required=False,
        many=True,
    )
    platforms = SerializedPKRelatedField(
        queryset=Platform.objects.all(),
        serializer=NestedPlatformSerializer,
        required=False,
        many=True,
    )
    cluster_groups = SerializedPKRelatedField(
        queryset=ClusterGroup.objects.all(),
        serializer=NestedClusterGroupSerializer,
        required=False,
        many=True,
    )
    clusters = SerializedPKRelatedField(
        queryset=Cluster.objects.all(),
        serializer=NestedClusterSerializer,
        required=False,
        many=True,
    )
    tenant_groups = SerializedPKRelatedField(
        queryset=TenantGroup.objects.all(),
        serializer=NestedTenantGroupSerializer,
        required=False,
        many=True,
    )
    tenants = SerializedPKRelatedField(
        queryset=Tenant.objects.all(),
        serializer=NestedTenantSerializer,
        required=False,
        many=True,
    )
    tags = serializers.SlugRelatedField(queryset=Tag.objects.all(), slug_field="slug", required=False, many=True)

    class Meta:
        model = ConfigContext
        fields = [
            "id",
            "url",
            "name",
            "owner_content_type",
            "owner_object_id",
            "owner",
            "weight",
            "description",
            "schema",
            "is_active",
            "regions",
            "sites",
            "roles",
            "device_types",
            "platforms",
            "cluster_groups",
            "clusters",
            "tenant_groups",
            "tenants",
            "tags",
            "data",
            "created",
            "last_updated",
        ]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        serializer = get_serializer_for_model(obj.owner, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.owner, context=context).data


#
# Config context Schemas
#


class ConfigContextSchemaSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:configcontextschema-detail")
    owner_content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("config_context_owners").get_query()),
        required=False,
        allow_null=True,
        default=None,
    )
    owner = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ConfigContextSchema
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "owner_content_type",
            "owner_object_id",
            "owner",
            "description",
            "data_schema",
            "created",
            "last_updated",
        ]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        serializer = get_serializer_for_model(obj.owner, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.owner, context=context).data


#
# Job Results
#


class JobResultSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobresult-detail")
    user = NestedUserSerializer(read_only=True)
    status = ChoiceField(choices=JobResultStatusChoices, read_only=True)
    obj_type = ContentTypeField(read_only=True)

    class Meta:
        model = JobResult
        fields = [
            "id",
            "url",
            "created",
            "completed",
            "name",
            "obj_type",
            "status",
            "user",
            "data",
            "job_id",
        ]


#
# Jobs (fka Custom Scripts, Reports)
#


class JobSerializer(serializers.Serializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="extras-api:job-detail",
        lookup_field="class_path",
        lookup_url_kwarg="class_path",
    )
    id = serializers.CharField(read_only=True, source="class_path")
    name = serializers.CharField(max_length=255, read_only=True)
    description = serializers.CharField(max_length=255, required=False, read_only=True)
    test_methods = serializers.ListField(child=serializers.CharField(max_length=255))
    vars = serializers.SerializerMethodField(read_only=True)
    result = NestedJobResultSerializer()

    def get_vars(self, instance):
        return {k: v.__class__.__name__ for k, v in instance._get_vars().items()}


class JobDetailSerializer(JobSerializer):
    result = JobResultSerializer()


class JobInputSerializer(serializers.Serializer):
    data = serializers.JSONField(required=False, default="")
    commit = serializers.BooleanField(required=False, default=None)


#
# Change logging
#


class ObjectChangeSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:objectchange-detail")
    user = NestedUserSerializer(read_only=True)
    action = ChoiceField(choices=ObjectChangeActionChoices, read_only=True)
    changed_object_type = ContentTypeField(read_only=True)
    changed_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ObjectChange
        fields = [
            "id",
            "url",
            "time",
            "user",
            "user_name",
            "request_id",
            "action",
            "changed_object_type",
            "changed_object_id",
            "changed_object",
            "object_data",
        ]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_changed_object(self, obj):
        """
        Serialize a nested representation of the changed object.
        """
        if obj.changed_object is None:
            return None

        try:
            serializer = get_serializer_for_model(obj.changed_object, prefix="Nested")
        except SerializerNotFound:
            return obj.object_repr
        context = {"request": self.context["request"]}
        data = serializer(obj.changed_object, context=context).data

        return data


#
# ContentTypes
#


class ContentTypeSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:contenttype-detail")
    display = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = ["id", "url", "app_label", "model", "display"]

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_display(self, obj):
        return obj.app_labeled_name


#
# Custom Links
#


class CustomLinkSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customlink-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = CustomLink
        fields = (
            "id",
            "url",
            "target_url",
            "name",
            "content_type",
            "text",
            "weight",
            "group_name",
            "button_class",
            "new_window",
        )


#
# Webhook
#


class WebhookSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:webhook-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("webhooks").get_query()).order_by("app_label", "model"),
        many=True,
    )

    class Meta:
        model = Webhook
        fields = [
            "id",
            "url",
            "content_types",
            "name",
            "type_create",
            "type_update",
            "type_delete",
            "payload_url",
            "http_method",
            "http_content_type",
            "additional_headers",
            "body_template",
            "secret",
            "ssl_verification",
            "ca_file_path",
        ]


#
# Custom statuses
#


class StatusSerializer(CustomFieldModelSerializer):
    """Serializer for `Status` objects."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:status-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("statuses").get_query()),
        many=True,
    )

    class Meta:
        model = Status
        fields = [
            "id",
            "url",
            "content_types",
            "name",
            "slug",
            "color",
            "custom_fields",
            "created",
            "last_updated",
        ]


class StatusModelSerializerMixin(serializers.Serializer):
    """Mixin to add non-required `status` choice field to model serializers."""

    status = StatusSerializerField(required=False, queryset=Status.objects.all())


#
# Relationship
#


class RelationshipSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:relationship-detail")

    source_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    destination_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    class Meta:
        model = Relationship
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "type",
            "source_type",
            "source_label",
            "source_hidden",
            "source_filter",
            "destination_type",
            "destination_label",
            "destination_hidden",
            "destination_filter",
        ]


class RelationshipAssociationSerializer(serializers.ModelSerializer):

    source_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    destination_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    relationship = NestedRelationshipSerializer()

    class Meta:
        model = RelationshipAssociation
        fields = [
            "id",
            "relationship",
            "source_type",
            "source_id",
            "destination_type",
            "destination_id",
        ]


#
# GraphQL Queries
#


class GraphQLQuerySerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:graphqlquery-detail")
    variables = serializers.DictField(required=False, allow_null=True, default={})

    class Meta:
        model = GraphQLQuery
        fields = (
            "id",
            "url",
            "name",
            "slug",
            "query",
            "variables",
        )


class GraphQLQueryInputSerializer(serializers.Serializer):
    variables = serializers.DictField(allow_null=True, default={})


class GraphQLQueryOutputSerializer(serializers.Serializer):
    data = serializers.DictField(default={})


# Computed Fields


class ComputedFieldSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:computedfield-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = ComputedField
        fields = (
            "id",
            "url",
            "slug",
            "label",
            "description",
            "content_type",
            "template",
            "fallback_value",
            "weight",
        )
