from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import classproperty
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.reverse import reverse

from nautobot.core.api import (
    ChoiceField,
    ContentTypeField,
    SerializedPKRelatedField,
    ValidatedModelSerializer,
)
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.serializers import BaseModelSerializer
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceSerializer,
    NestedDeviceRoleSerializer,
    NestedDeviceTypeSerializer,
    NestedLocationSerializer,
    NestedPlatformSerializer,
    NestedRackSerializer,
    NestedRegionSerializer,
    NestedSiteSerializer,
)
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Location, Platform, Rack, Region, Site
from nautobot.extras.api.fields import StatusSerializerField
from nautobot.extras.choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
)
from nautobot.extras.datasources import get_datasource_content_choices
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobHook,
    JobLogEntry,
    JobResult,
    Note,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery, TaggableClassesQuery
from nautobot.tenancy.api.nested_serializers import (
    NestedTenantSerializer,
    NestedTenantGroupSerializer,
)
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.api.nested_serializers import NestedUserSerializer
from nautobot.utilities.api import get_serializer_for_model
from nautobot.utilities.utils import get_route_for_model, slugify_dashes_to_underscores
from nautobot.virtualization.api.nested_serializers import (
    NestedClusterGroupSerializer,
    NestedClusterSerializer,
)
from nautobot.virtualization.models import Cluster, ClusterGroup

from .customfields import CustomFieldModelSerializer
from .fields import MultipleChoiceJSONField
from .relationships import RelationshipModelSerializerMixin

# Not all of these variable(s) are not actually used anywhere in this file, but required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import (  # noqa: F401
    NestedComputedFieldSerializer,
    NestedConfigContextSchemaSerializer,
    NestedConfigContextSerializer,
    NestedCustomFieldSerializer,
    NestedCustomLinkSerializer,
    NestedDynamicGroupSerializer,
    NestedDynamicGroupMembershipSerializer,
    NestedExportTemplateSerializer,
    NestedGitRepositorySerializer,
    NestedGraphQLQuerySerializer,
    NestedImageAttachmentSerializer,
    NestedJobSerializer,
    NestedJobResultSerializer,
    NestedNoteSerializer,
    NestedRelationshipAssociationSerializer,
    NestedRelationshipSerializer,
    NestedScheduledJobSerializer,
    NestedSecretSerializer,
    NestedSecretsGroupSerializer,
    NestedSecretsGroupAssociationSerializer,
    NestedStatusSerializer,
    NestedTagSerializer,
    NestedWebhookSerializer,
    NestedJobHookSerializer,
)

#
# Mixins and Base Classes
#


class NotesSerializerMixin(BaseModelSerializer):
    """Extend Serializer with a `notes` field."""

    notes_url = serializers.SerializerMethodField()

    def get_field_names(self, declared_fields, info):
        """Ensure that fields includes "notes_url" field if applicable."""
        fields = list(super().get_field_names(declared_fields, info))
        if hasattr(self.Meta.model, "notes"):
            self.extend_field_names(fields, "notes_url")
        return fields

    @extend_schema_field(serializers.URLField())
    def get_notes_url(self, instance):
        notes_url = get_route_for_model(instance, "notes", api=True)
        return reverse(notes_url, args=[instance.id], request=self.context["request"])


class NautobotModelSerializer(
    RelationshipModelSerializerMixin, CustomFieldModelSerializer, NotesSerializerMixin, ValidatedModelSerializer
):
    """Base class to use for serializers based on OrganizationalModel or PrimaryModel.

    Can also be used for models derived from BaseModel, so long as they support custom fields and relationships.
    """


class StatusModelSerializerMixin(BaseModelSerializer):
    """Mixin to add `status` choice field to model serializers."""

    status = StatusSerializerField(queryset=Status.objects.all())

    def get_field_names(self, declared_fields, info):
        """Ensure that "status" field is always present."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "status")
        return fields

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def status_choices(cls):  # pylint: disable=no-self-argument
        """
        Get the list of valid status values for this serializer.

        In the case where multiple serializers have the same set of status choices, it's necessary to set
        settings.SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"] for at least one of the matching serializers,
        or else drf-spectacular will report:
        'enum naming encountered a non-optimally resolvable collision for fields named "status"'
        """
        return list(cls().fields["status"].get_choices().keys())


class TagSerializerField(NestedTagSerializer):
    """NestedSerializer field for `Tag` object fields."""

    def get_queryset(self):
        """Only emit status options for this model/field combination."""
        queryset = super().get_queryset()
        # Get objects model e.g Site, Device... etc.
        model = self.parent.parent.Meta.model
        return queryset.get_for_model(model)


# TODO should be TaggedModelSerializerMixin
class TaggedObjectSerializer(BaseModelSerializer):
    tags = TagSerializerField(many=True, required=False)

    def get_field_names(self, declared_fields, info):
        """Ensure that 'tags' field is always present."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "tags")
        return fields

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
            instance.tags.set([t.name for t in tags])
        else:
            instance.tags.clear()

        return instance


#
# Computed Fields
#


class ComputedFieldSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:computedfield-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = ComputedField
        fields = (
            "url",
            "slug",
            "label",
            "description",
            "content_type",
            "template",
            "fallback_value",
            "weight",
        )


#
# Config contexts
#


class ConfigContextSerializer(ValidatedModelSerializer, NotesSerializerMixin):
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
    locations = SerializedPKRelatedField(
        queryset=Location.objects.all(),
        serializer=NestedLocationSerializer,
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
        serializer=NestedDeviceTypeSerializer,
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
            "locations",
            "roles",
            "device_types",
            "platforms",
            "cluster_groups",
            "clusters",
            "tenant_groups",
            "tenants",
            "tags",
            "data",
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        serializer = get_serializer_for_model(obj.owner, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.owner, context=context).data


#
# Config context Schemas
#


class ConfigContextSchemaSerializer(NautobotModelSerializer):
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
            "url",
            "name",
            "slug",
            "owner_content_type",
            "owner_object_id",
            "owner",
            "description",
            "data_schema",
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        serializer = get_serializer_for_model(obj.owner, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.owner, context=context).data


#
# ContentTypes
#


class ContentTypeSerializer(BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:contenttype-detail")
    display = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = ["url", "app_label", "model"]

    @extend_schema_field(serializers.CharField)
    def get_display(self, obj):
        return obj.app_labeled_name


#
# Custom fields
#


class CustomFieldSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfield-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()),
        many=True,
    )
    type = ChoiceField(choices=CustomFieldTypeChoices)
    filter_logic = ChoiceField(choices=CustomFieldFilterLogicChoices, required=False)
    # Laying groundwork for 2.0:
    # - in 1.4 `label` is not required at the model level due to backward compatibility, but in 2.0 it will be.
    # - in 1.4 `name` is required at the model level, but in 2.0 it will be removed entirely.
    # Since the API is versioned we can go ahead and adopt the future here.
    label = serializers.CharField(max_length=50, required=True)

    class Meta:
        model = CustomField
        fields = [
            "url",
            "content_types",
            "type",
            "label",
            "slug",
            "description",
            "required",
            "filter_logic",
            "default",
            "weight",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
        ]

    def validate(self, data):
        # 2.0 TODO: #824 remove `name` entirely from the model; for now it's required.
        if self.instance is None:
            if "slug" in data and "name" not in data:
                data["name"] = data["slug"]

        return super().validate(data)


class CustomFieldSerializerVersion12(CustomFieldSerializer):
    # In older versions of the REST API, neither `label` nor `slug` were required fields. See also validate() below.
    label = serializers.CharField(max_length=50, required=False)
    slug = serializers.CharField(max_length=50, required=False)

    class Meta(CustomFieldSerializer.Meta):
        fields = CustomFieldSerializer.Meta.fields.copy()
        fields.insert(4, "name")

    def validate(self, data):
        # Logic copied from CustomField.clean_fields(), since this needs to happen *before* the instance is created
        if self.instance is None:
            # 2.0 TODO: this is to fix up existing usage when caller specifies a name but not a label;
            # in 2.0 we should make `label` a mandatory field when getting rid of `name`.
            if "name" in data and "label" not in data:
                data["label"] = data["name"]

            if "label" in data and "slug" not in data:
                data["slug"] = slugify_dashes_to_underscores(data["label"])

        return super().validate(data)


class CustomFieldChoiceSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customfieldchoice-detail")
    field = NestedCustomFieldSerializer()

    class Meta:
        model = CustomFieldChoice
        fields = ["url", "field", "value", "weight"]


#
# Custom Links
#


class CustomLinkSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:customlink-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = CustomLink
        fields = (
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
# Dynamic Groups
#


class DynamicGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroup-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
    )
    # Read-only because m2m is hard. Easier to just create # `DynamicGroupMemberships` explicitly
    # using their own endpoint at /api/extras/dynamic-group-memberships/.
    children = NestedDynamicGroupMembershipSerializer(source="dynamic_group_memberships", read_only=True, many=True)

    class Meta:
        model = DynamicGroup
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "content_type",
            "filter",
            "children",
        ]
        extra_kwargs = {"filter": {"read_only": False}}


class DynamicGroupMembershipSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroupmembership-detail")
    group = NestedDynamicGroupSerializer()
    parent_group = NestedDynamicGroupSerializer()

    class Meta:
        model = DynamicGroupMembership
        fields = ["url", "group", "parent_group", "operator", "weight"]


#
# Export templates
#

# TODO: export-templates don't support custom-fields, is this omission intentional?
class ExportTemplateSerializer(RelationshipModelSerializerMixin, ValidatedModelSerializer, NotesSerializerMixin):
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

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        serializer = get_serializer_for_model(obj.owner, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.owner, context=context).data


#
# Git repositories
#


class GitRepositorySerializer(NautobotModelSerializer):
    """Git repositories defined as a data source."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:gitrepository-detail")
    token = serializers.CharField(source="_token", write_only=True, required=False)

    secrets_group = NestedSecretsGroupSerializer(required=False, allow_null=True)

    provided_contents = MultipleChoiceJSONField(
        choices=lambda: get_datasource_content_choices("extras.gitrepository"),
        allow_blank=True,
        required=False,
    )

    class Meta:
        model = GitRepository
        fields = [
            "url",
            "name",
            "slug",
            "remote_url",
            "branch",
            "token",
            "username",
            "secrets_group",
            "current_head",
            "provided_contents",
        ]

    def validate(self, data):
        """
        Add the originating Request as a parameter to be passed when creating/updating a GitRepository.
        """
        data["request"] = self.context["request"]
        return super().validate(data)


#
# GraphQL Queries
#


class GraphQLQuerySerializer(ValidatedModelSerializer, NotesSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:graphqlquery-detail")
    variables = serializers.DictField(required=False, allow_null=True, default={})

    class Meta:
        model = GraphQLQuery
        fields = (
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
            raise serializers.ValidationError(f"Invalid parent object: {data['content_type']} ID {data['object_id']}")

        # Enforce model validation
        super().validate(data)

        return data

    @extend_schema_field(serializers.DictField)
    def get_parent(self, obj):

        # Static mapping of models to their nested serializers
        if isinstance(obj.parent, Device):
            serializer = NestedDeviceSerializer
        elif isinstance(obj.parent, Location):
            serializer = NestedLocationSerializer
        elif isinstance(obj.parent, Rack):
            serializer = NestedRackSerializer
        elif isinstance(obj.parent, Site):
            serializer = NestedSiteSerializer
        else:
            raise Exception("Unexpected type of parent object for ImageAttachment")

        return serializer(obj.parent, context={"request": self.context["request"]}).data


#
# Jobs
#


class JobSerializer(NautobotModelSerializer, TaggedObjectSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:job-detail")

    class Meta:
        model = Job
        fields = [
            "url",
            "source",
            "module_name",
            "job_class_name",
            "grouping",
            "grouping_override",
            "name",
            "name_override",
            "slug",
            "description",
            "description_override",
            "installed",
            "enabled",
            "is_job_hook_receiver",
            "has_sensitive_variables",
            "has_sensitive_variables_override",
            "approval_required",
            "approval_required_override",
            "commit_default",
            "commit_default_override",
            "hidden",
            "hidden_override",
            "read_only",
            "read_only_override",
            "soft_time_limit",
            "soft_time_limit_override",
            "time_limit",
            "time_limit_override",
            "task_queues",
            "task_queues_override",
            "tags",
        ]

    def validate(self, data):
        # note no validation for on creation of jobs because we do not support user creation of Job records via API
        if self.instance:
            has_sensitive_variables = data.get("has_sensitive_variables", self.instance.has_sensitive_variables)
            approval_required = data.get("approval_required", self.instance.approval_required)

            if approval_required and has_sensitive_variables:
                error_message = "A job with sensitive variables cannot also be marked as requiring approval"
                errors = {}

                if "approval_required" in data:
                    errors["approval_required"] = [error_message]
                if "has_sensitive_variables" in data:
                    errors["has_sensitive_variables"] = [error_message]

                raise serializers.ValidationError(errors)

        return super().validate(data)


class JobVariableSerializer(serializers.Serializer):
    """Serializer used for responses from the JobModelViewSet.variables() detail endpoint."""

    name = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True, required=False)
    help_text = serializers.CharField(read_only=True, required=False)
    default = serializers.JSONField(read_only=True, required=False)
    required = serializers.BooleanField(read_only=True, required=False)

    min_length = serializers.IntegerField(read_only=True, required=False)
    max_length = serializers.IntegerField(read_only=True, required=False)
    min_value = serializers.IntegerField(read_only=True, required=False)
    max_value = serializers.IntegerField(read_only=True, required=False)
    choices = serializers.JSONField(read_only=True, required=False)
    model = serializers.CharField(read_only=True, required=False)


class JobRunResponseSerializer(serializers.Serializer):
    """Serializer representing responses from the JobModelViewSet.run() POST endpoint."""

    schedule = NestedScheduledJobSerializer(read_only=True, required=False)
    job_result = NestedJobResultSerializer(read_only=True, required=False)


#
# Job Results
#


class JobResultSerializer(CustomFieldModelSerializer, BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobresult-detail")
    user = NestedUserSerializer(read_only=True)
    status = ChoiceField(choices=JobResultStatusChoices, read_only=True)
    job_model = NestedJobSerializer(read_only=True)
    obj_type = ContentTypeField(read_only=True)
    schedule = NestedScheduledJobSerializer(read_only=True)

    class Meta:
        model = JobResult
        fields = [
            "url",
            "created",
            "completed",
            "name",
            "job_model",
            "obj_type",
            "status",
            "user",
            "data",
            "job_id",
            "job_kwargs",
            "schedule",
        ]


#
# Scheduled Jobs
#


class ScheduledJobSerializer(BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:scheduledjob-detail")
    user = NestedUserSerializer(read_only=True)
    job_model = NestedJobSerializer(read_only=True)
    approved_by_user = NestedUserSerializer(read_only=True)

    class Meta:
        model = ScheduledJob
        fields = [
            "url",
            "name",
            "user",
            "job_model",
            "task",
            "interval",
            "queue",
            "job_class",
            "last_run_at",
            "total_run_count",
            "date_changed",
            "description",
            "user",
            "approved_by_user",
            "approval_required",
            "approved_at",
            "crontab",
        ]


#
# Job classes (fka Custom Scripts, Reports)
# 2.0 TODO: remove these if no longer needed
#


class JobClassSerializer(serializers.Serializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="extras-api:job-detail",
        lookup_field="class_path",
        lookup_url_kwarg="class_path",
    )
    id = serializers.CharField(read_only=True, source="class_path")
    pk = serializers.SerializerMethodField(read_only=True)
    name = serializers.CharField(max_length=255, read_only=True)
    description = serializers.CharField(max_length=255, required=False, read_only=True)
    test_methods = serializers.ListField(child=serializers.CharField(max_length=255))
    vars = serializers.SerializerMethodField(read_only=True)
    result = NestedJobResultSerializer(required=False)

    @extend_schema_field(serializers.DictField)
    def get_vars(self, instance):
        return {k: v.__class__.__name__ for k, v in instance._get_vars().items()}

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_pk(self, instance):
        try:
            jobs = Job.objects
            if "request" in self.context and self.context["request"].user is not None:
                jobs = jobs.restrict(self.context["request"].user, "view")
            job_model = jobs.get_for_class_path(instance.class_path)
            return job_model.pk
        except Job.DoesNotExist:
            return None


class JobClassDetailSerializer(JobClassSerializer):
    result = JobResultSerializer(required=False)


class JobHookSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:jobhook-detail")
    content_types = ContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(),
        many=True,
    )

    class Meta:
        model = JobHook
        fields = [
            "id",
            "url",
            "name",
            "content_types",
            "job",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
        ]

    def validate(self, data):
        validated_data = super().validate(data)

        conflicts = JobHook.check_for_conflicts(
            instance=self.instance,
            content_types=data.get("content_types"),
            job=data.get("job"),
            type_create=data.get("type_create"),
            type_update=data.get("type_update"),
            type_delete=data.get("type_delete"),
        )

        if conflicts:
            raise serializers.ValidationError(conflicts)

        return validated_data


class JobInputSerializer(serializers.Serializer):
    data = serializers.JSONField(required=False, default=dict)
    commit = serializers.BooleanField(required=False, default=None)
    schedule = NestedScheduledJobSerializer(required=False)
    task_queue = serializers.CharField(required=False, allow_blank=True)


class JobLogEntrySerializer(BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:joblogentry-detail")
    display = serializers.SerializerMethodField()

    class Meta:
        model = JobLogEntry
        fields = [
            "url",
            "absolute_url",
            "created",
            "grouping",
            "job_result",
            "log_level",
            "log_object",
            "message",
        ]

    @extend_schema_field(serializers.CharField)
    def get_display(self, obj):
        return obj.created.isoformat()


#
# Notes
#


class NoteSerializer(BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:note-detail")
    user = NestedUserSerializer(read_only=True)
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "url",
            "user",
            "user_name",
            "assigned_object_type",
            "assigned_object_id",
            "assigned_object",
            "note",
            "slug",
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_assigned_object(self, obj):
        if obj.assigned_object is None:
            return None
        try:
            serializer = get_serializer_for_model(obj.assigned_object, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj.assigned_object, context=context).data
        except SerializerNotFound:
            return None


class NoteInputSerializer(serializers.Serializer):
    note = serializers.CharField()


#
# Change logging
#


class ObjectChangeSerializer(BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:objectchange-detail")
    user = NestedUserSerializer(read_only=True)
    action = ChoiceField(choices=ObjectChangeActionChoices, read_only=True)
    changed_object_type = ContentTypeField(read_only=True)
    changed_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ObjectChange
        fields = [
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

    @extend_schema_field(serializers.DictField(allow_null=True))
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
# Relationship
#


class RelationshipSerializer(ValidatedModelSerializer, NotesSerializerMixin):
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
            "url",
            "name",
            "slug",
            "description",
            "type",
            "required_on",
            "source_type",
            "source_label",
            "source_hidden",
            "source_filter",
            "destination_type",
            "destination_label",
            "destination_hidden",
            "destination_filter",
        ]


class RelationshipAssociationSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:relationshipassociation-detail")

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
            "url",
            "relationship",
            "source_type",
            "source_id",
            "destination_type",
            "destination_id",
        ]


#
# Secrets
#


class SecretSerializer(NautobotModelSerializer, TaggedObjectSerializer):
    """Serializer for `Secret` objects."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secret-detail")

    class Meta:
        model = Secret
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "provider",
            "parameters",
        ]


class SecretsGroupSerializer(NautobotModelSerializer):
    """Serializer for `SecretsGroup` objects."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secretsgroup-detail")

    # TODO: it would be **awesome** if we could create/update SecretsGroupAssociations
    # alongside creating/updating the base SecretsGroup, but since this is a ManyToManyField with
    # a `through` table, that appears very non-trivial to implement. For now we have this as a
    # read-only field; to create/update SecretsGroupAssociations you must make separate calls to the
    # api/extras/secrets-group-associations/ REST endpoint as appropriate.
    secrets = NestedSecretsGroupAssociationSerializer(source="secretsgroupassociation_set", many=True, read_only=True)

    class Meta:
        model = SecretsGroup
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "secrets",
        ]


class SecretsGroupAssociationSerializer(ValidatedModelSerializer):
    """Serializer for `SecretsGroupAssociation` objects."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:secretsgroupassociation-detail")
    group = NestedSecretsGroupSerializer()
    secret = NestedSecretSerializer()

    class Meta:
        model = SecretsGroupAssociation
        fields = [
            "url",
            "group",
            "access_type",
            "secret_type",
            "secret",
        ]


#
# Custom statuses
#


class StatusSerializer(NautobotModelSerializer):
    """Serializer for `Status` objects."""

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:status-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("statuses").get_query()),
        many=True,
    )

    class Meta:
        model = Status
        fields = [
            "url",
            "content_types",
            "name",
            "slug",
            "color",
        ]


#
# Tags
#


class TagSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:tag-detail")
    tagged_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = [
            "url",
            "name",
            "slug",
            "color",
            "description",
            "tagged_items",
        ]

    def validate(self, data):
        data = super().validate(data)

        # All relevant content_types should be assigned to newly created tag for API Version <1.3
        if (self.instance is None or not self.instance.present_in_database) and "content_types" not in data:
            data["content_types"] = TaggableClassesQuery().as_queryset()

        # check if tag is assigned to any of the removed content_types
        if self.instance is not None and self.instance.present_in_database and "content_types" in data:
            content_types_id = [content_type.id for content_type in data["content_types"]]
            errors = self.instance.validate_content_types_removal(content_types_id)

            if errors:
                raise serializers.ValidationError(errors)

        return data


class TagSerializerVersion13(TagSerializer):
    content_types = ContentTypeField(
        queryset=TaggableClassesQuery().as_queryset(),
        many=True,
        required=True,
    )

    class Meta:
        model = Tag
        fields = [
            "url",
            "name",
            "slug",
            "color",
            "description",
            "tagged_items",
            "content_types",
        ]


#
# Webhook
#


class WebhookSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:webhook-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("webhooks").get_query()).order_by("app_label", "model"),
        many=True,
    )

    class Meta:
        model = Webhook
        fields = [
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

    def validate(self, data):
        validated_data = super().validate(data)

        conflicts = Webhook.check_for_conflicts(
            instance=self.instance,
            content_types=data.get("content_types"),
            payload_url=data.get("payload_url"),
            type_create=data.get("type_create"),
            type_update=data.get("type_update"),
            type_delete=data.get("type_delete"),
        )

        if conflicts:
            raise serializers.ValidationError(conflicts)

        return validated_data
