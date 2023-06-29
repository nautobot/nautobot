import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import (
    BaseModelSerializer,
    ChoiceField,
    ContentTypeField,
    CustomFieldModelSerializerMixin,
    NautobotModelSerializer,
    NotesSerializerMixin,
    RelationshipModelSerializerMixin,
    ValidatedModelSerializer,
)
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.serializers import PolymorphicProxySerializer
from nautobot.core.api.utils import (
    get_nested_serializer_depth,
    nested_serializers_for_models,
    return_nested_serializer_data_based_on_depth,
)
from nautobot.core.models.utils import get_all_concrete_models
from nautobot.dcim.api.serializers import (
    DeviceSerializer,
    LocationSerializer,
    RackSerializer,
)
from nautobot.extras import choices, models
from nautobot.extras.choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    JobExecutionType,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
)
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
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
    JobButton,
    JobHook,
    JobLogEntry,
    JobResult,
    Note,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Role,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery, RoleModelsQuery, TaggableClassesQuery

from .fields import MultipleChoiceJSONField

#
# Mixins and Base Classes
#

logger = logging.getLogger(__name__)


#
# Computed Fields
#


class ComputedFieldSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = ComputedField
        fields = "__all__"


#
# Config contexts
#


class ConfigContextSerializer(ValidatedModelSerializer, TaggedModelSerializerMixin, NotesSerializerMixin):
    owner_content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("config_context_owners").get_query()),
        required=False,
        allow_null=True,
        default=None,
    )
    owner = serializers.SerializerMethodField(read_only=True)

    # Conditional enablement of dynamic groups filtering
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            # In the case of a nested serializer, we won't have a `dynamic_groups` field at all.
            self.fields.pop("dynamic_groups", None)

    class Meta:
        model = ConfigContext
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="ConfigContextOwner",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(FeatureQuery("config_context_owners").list_subclasses()),
            allow_null=True,
        )
    )
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        depth = get_nested_serializer_depth(self)
        return return_nested_serializer_data_based_on_depth(self, depth, obj, obj.owner, "owner")


#
# Config context Schemas
#


class ConfigContextSchemaSerializer(NautobotModelSerializer):
    owner_content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("config_context_owners").get_query()),
        required=False,
        allow_null=True,
        default=None,
    )
    owner = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ConfigContextSchema
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="ConfigContextSchemaOwner",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(FeatureQuery("config_context_owners").list_subclasses()),
            allow_null=True,
        )
    )
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        depth = get_nested_serializer_depth(self)
        return return_nested_serializer_data_based_on_depth(self, depth, obj, obj.owner, "owner")


#
# ContentTypes
#


class ContentTypeSerializer(BaseModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:contenttype-detail")
    display = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = "__all__"

    @extend_schema_field(serializers.CharField)
    def get_display(self, obj):
        return obj.app_labeled_name


#
# Custom fields
#


class CustomFieldSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()),
        many=True,
    )
    type = ChoiceField(choices=CustomFieldTypeChoices)
    filter_logic = ChoiceField(choices=CustomFieldFilterLogicChoices, required=False)
    label = serializers.CharField(max_length=50, required=True)

    class Meta:
        model = CustomField
        fields = "__all__"


class CustomFieldChoiceSerializer(ValidatedModelSerializer):
    class Meta:
        model = CustomFieldChoice
        fields = "__all__"


#
# Custom Links
#


class CustomLinkSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = CustomLink
        fields = "__all__"


#
# Dynamic Groups
#


class DynamicGroupMembershipSerializer(ValidatedModelSerializer):
    class Meta:
        model = DynamicGroupMembership
        fields = "__all__"


class DynamicGroupSerializer(NautobotModelSerializer):
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = DynamicGroup
        fields = "__all__"
        extra_kwargs = {
            "children": {"source": "dynamic_group_memberships", "read_only": True},
            "filter": {"read_only": False},
        }


#
# Export templates
#


# TODO: export-templates don't support custom-fields, is this omission intentional?
class ExportTemplateSerializer(RelationshipModelSerializerMixin, ValidatedModelSerializer, NotesSerializerMixin):
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
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="ExportTemplateOwner",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(FeatureQuery("export_template_owners").list_subclasses()),
            allow_null=True,
        )
    )
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        depth = get_nested_serializer_depth(self)
        return return_nested_serializer_data_based_on_depth(self, depth, obj, obj.owner, "owner")


#
# Git repositories
#


class GitRepositorySerializer(NautobotModelSerializer):
    """Git repositories defined as a data source."""

    provided_contents = MultipleChoiceJSONField(
        choices=lambda: get_datasource_content_choices("extras.gitrepository"),
        allow_blank=True,
        required=False,
    )

    class Meta:
        model = GitRepository
        fields = "__all__"


#
# GraphQL Queries
#


class GraphQLQuerySerializer(ValidatedModelSerializer, NotesSerializerMixin):
    variables = serializers.DictField(required=False, allow_null=True, default={})

    class Meta:
        model = GraphQLQuery
        fields = "__all__"


class GraphQLQueryInputSerializer(serializers.Serializer):
    variables = serializers.DictField(allow_null=True, default={})


class GraphQLQueryOutputSerializer(serializers.Serializer):
    data = serializers.DictField(default={})


#
# Image attachments
#


class ImageAttachmentSerializer(ValidatedModelSerializer):
    content_type = ContentTypeField(queryset=ContentType.objects.all())

    class Meta:
        model = ImageAttachment
        fields = "__all__"

    def validate(self, data):
        # Validate that the parent object exists
        try:
            data["content_type"].get_object_for_this_type(id=data["object_id"])
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f"Invalid parent object: {data['content_type']} ID {data['object_id']}")

        # Enforce model validation
        super().validate(data)

        return data

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="ImageAttachmentParent",
            resource_type_field_name="object_type",
            serializers=[
                DeviceSerializer,
                LocationSerializer,
                RackSerializer,
            ],
        )
    )
    def get_parent(self, obj):
        depth = get_nested_serializer_depth(self)
        return return_nested_serializer_data_based_on_depth(self, depth, obj, obj.parent, "parent")


#
# Jobs
#


class JobSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = Job
        fields = "__all__"

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


#
# Scheduled Jobs
#


class ScheduledJobSerializer(BaseModelSerializer):
    # start_time = serializers.DateTimeField(format=None, required=False)

    class Meta:
        model = ScheduledJob
        fields = "__all__"


#
# Job Results
#


class JobResultSerializer(CustomFieldModelSerializerMixin, BaseModelSerializer):
    status = ChoiceField(choices=JobResultStatusChoices, read_only=True)

    class Meta:
        model = JobResult
        fields = "__all__"


class JobRunResponseSerializer(serializers.Serializer):
    """Serializer representing responses from the JobModelViewSet.run() POST endpoint."""

    schedule = ScheduledJobSerializer(read_only=True, required=False)
    job_result = JobResultSerializer(read_only=True, required=False)


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
    content_types = ContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(),
        many=True,
    )

    class Meta:
        model = JobHook
        fields = "__all__"

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


class JobCreationSerializer(BaseModelSerializer):
    """
    Nested serializer specifically for use with `JobInputSerializer.schedule`.

    We don't use `WritableNestedSerializer` here because this is not used to look up
    an existing `ScheduledJob`, but instead used to specify parameters for creating one.
    """

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:scheduledjob-detail")
    name = serializers.CharField(max_length=255, required=False)
    start_time = serializers.DateTimeField(format=None, required=False)

    class Meta:
        model = ScheduledJob
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


class JobInputSerializer(serializers.Serializer):
    data = serializers.JSONField(required=False, default=dict)
    schedule = JobCreationSerializer(required=False)
    task_queue = serializers.CharField(required=False, allow_blank=True)


class JobMultiPartInputSerializer(serializers.Serializer):
    """JobMultiPartInputSerializer is a "flattened" version of JobInputSerializer for use with multipart/form-data submissions which only accept key-value pairs"""

    _schedule_name = serializers.CharField(max_length=255, required=False)
    _schedule_start_time = serializers.DateTimeField(format=None, required=False)
    _schedule_interval = ChoiceField(choices=JobExecutionType, required=False)
    _schedule_crontab = serializers.CharField(required=False, allow_blank=True)
    _task_queue = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        data = super().validate(data)

        if "_schedule_interval" in data and data["_schedule_interval"] != JobExecutionType.TYPE_IMMEDIATELY:
            if "_schedule_name" not in data:
                raise serializers.ValidationError({"_schedule_name": "Please provide a name for the job schedule."})

            if ("_schedule_start_time" not in data and data["_schedule_interval"] != JobExecutionType.TYPE_CUSTOM) or (
                "_schedule_start_time" in data and data["_schedule_start_time"] < ScheduledJob.earliest_possible_time()
            ):
                raise serializers.ValidationError(
                    {
                        "_schedule_start_time": "Please enter a valid date and time greater than or equal to the current date and time."
                    }
                )

            if data["_schedule_interval"] == JobExecutionType.TYPE_CUSTOM:
                if data.get("_schedule_crontab") is None:
                    raise serializers.ValidationError({"_schedule_crontab": "Please enter a valid crontab."})
                try:
                    ScheduledJob.get_crontab(data["_schedule_crontab"])
                except Exception as e:
                    raise serializers.ValidationError({"_schedule_crontab": e})

        return data


class JobLogEntrySerializer(BaseModelSerializer):
    class Meta:
        model = JobLogEntry
        fields = "__all__"


#
# Job Button
#


class JobButtonSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    content_types = ContentTypeField(queryset=ContentType.objects.all(), many=True)

    class Meta:
        model = JobButton
        fields = "__all__"


#
# Notes
#


class NoteSerializer(BaseModelSerializer):
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = "__all__"
        list_display_fields = ["note", "assigned_object_type", "assigned_object_id", "user"]

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="NoteAssignedObject",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(get_all_concrete_models(NotesMixin)),
            allow_null=True,
        )
    )
    def get_assigned_object(self, obj):
        if obj.assigned_object is None:
            return None
        try:
            depth = get_nested_serializer_depth(self)
            return return_nested_serializer_data_based_on_depth(
                self, depth, obj, obj.assigned_object, "assigned_object"
            )
        except SerializerNotFound:
            return None


class NoteInputSerializer(serializers.Serializer):
    note = serializers.CharField()


#
# Change logging
#


class ObjectChangeSerializer(BaseModelSerializer):
    action = ChoiceField(choices=ObjectChangeActionChoices, read_only=True)
    changed_object_type = ContentTypeField(read_only=True)
    changed_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ObjectChange
        fields = "__all__"
        list_display_fields = ["changed_object_id", "related_object_id", "related_object_type", "user"]

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="ObjectChangeChangedObject",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(ChangeLoggedModelsQuery().list_subclasses()),
            allow_null=True,
        )
    )
    def get_changed_object(self, obj):
        """
        Serialize a nested representation of the changed object.
        """
        if obj.changed_object is None:
            return None
        try:
            depth = get_nested_serializer_depth(self)
            return return_nested_serializer_data_based_on_depth(self, depth, obj, obj.changed_object, "changed_object")
        except SerializerNotFound:
            return obj.object_repr


#
# Relationship
#


class RelationshipSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    source_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    destination_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    class Meta:
        model = Relationship
        fields = "__all__"


class RelationshipAssociationSerializer(ValidatedModelSerializer):
    source_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    destination_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()),
    )

    class Meta:
        model = RelationshipAssociation
        fields = "__all__"


#
# Roles
#


class RoleSerializer(NautobotModelSerializer):
    """Serializer for `Role` objects."""

    content_types = ContentTypeField(
        queryset=RoleModelsQuery().as_queryset(),
        many=True,
    )

    class Meta:
        model = Role
        fields = "__all__"
        extra_kwargs = {
            "color": {"help_text": "RGB color in hexadecimal (e.g. 00ff00)"},
        }


#
# Secrets
#


class SecretSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for `Secret` objects."""

    class Meta:
        model = Secret
        fields = "__all__"


class SecretsGroupAssociationSerializer(ValidatedModelSerializer):
    """Serializer for `SecretsGroupAssociation` objects."""

    class Meta:
        model = SecretsGroupAssociation
        fields = "__all__"


class SecretsGroupSerializer(NautobotModelSerializer):
    """Serializer for `SecretsGroup` objects."""

    class Meta:
        model = SecretsGroup
        fields = "__all__"
        # TODO: it would be **awesome** if we could create/update SecretsGroupAssociations
        # alongside creating/updating the base SecretsGroup, but since this is a ManyToManyField with
        # a `through` table, that appears very non-trivial to implement. For now we have this as a
        # read-only field; to create/update SecretsGroupAssociations you must make separate calls to the
        # api/extras/secrets-group-associations/ REST endpoint as appropriate.
        extra_kwargs = {
            "secrets": {"source": "secrets_group_associations", "read_only": True},
        }


#
# Custom statuses
#


class StatusSerializer(NautobotModelSerializer):
    """Serializer for `Status` objects."""

    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("statuses").get_query()),
        many=True,
    )

    class Meta:
        model = Status
        fields = "__all__"
        extra_kwargs = {
            "color": {"help_text": "RGB color in hexadecimal (e.g. 00ff00)"},
        }


#
# Tags
#


class TagSerializer(NautobotModelSerializer):
    tagged_items = serializers.IntegerField(read_only=True)
    content_types = ContentTypeField(
        queryset=TaggableClassesQuery().as_queryset(),
        many=True,
        required=True,
    )

    class Meta:
        model = Tag
        fields = "__all__"
        extra_kwargs = {
            "color": {"help_text": "RGB color in hexadecimal (e.g. 00ff00)"},
        }

    def validate(self, data):
        data = super().validate(data)

        # check if tag is assigned to any of the removed content_types
        if self.instance is not None and self.instance.present_in_database and "content_types" in data:
            content_types_id = [content_type.id for content_type in data["content_types"]]
            errors = self.instance.validate_content_types_removal(content_types_id)

            if errors:
                raise serializers.ValidationError(errors)

        return data


#
# Webhook
#


class WebhookSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("webhooks").get_query()).order_by("app_label", "model"),
        many=True,
    )

    class Meta:
        model = Webhook
        fields = "__all__"

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
