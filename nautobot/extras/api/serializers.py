import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from timezone_field.rest_framework import TimeZoneSerializerField

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
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.utils import get_all_concrete_models
from nautobot.dcim.api.serializers import (
    DeviceSerializer,
    LocationSerializer,
    RackSerializer,
)
from nautobot.extras import choices, models
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)
from nautobot.extras.choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    JobExecutionType,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
)
from nautobot.extras.datasources import get_datasource_content_choices
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    ExternalIntegration,
    FileProxy,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobQueue,
    JobQueueAssignment,
    JobResult,
    MetadataChoice,
    MetadataType,
    Note,
    ObjectChange,
    ObjectMetadata,
    Relationship,
    RelationshipAssociation,
    Role,
    SavedView,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    StaticGroupAssociation,
    Status,
    Tag,
    Team,
    UserSavedViewAssociation,
    Webhook,
)
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.utils import (
    ChangeLoggedModelsQuery,
    FeatureQuery,
    RoleModelsQuery,
    TaggableClassesQuery,
)

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
    @property
    def fields(self):
        fields = super().fields
        if not settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            fields.pop("dynamic_groups", None)
        return fields

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
# Contacts
#


class ContactSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
        # https://www.django-rest-framework.org/api-guide/validators/#optional-fields
        validators = []
        extra_kwargs = {
            "email": {"default": ""},
            "phone": {"default": ""},
            "teams": {"required": False},
        }

    def get_field_names(self, declared_fields, info):
        """Add reverse M2M for teams to the fields for this serializer."""
        field_names = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(field_names, "teams")
        return field_names

    def validate(self, attrs):
        local_attrs = attrs.copy()
        local_attrs.pop("teams", None)
        validator = UniqueTogetherValidator(queryset=Contact.objects.all(), fields=("name", "phone", "email"))
        validator(local_attrs, self)
        super().validate(local_attrs)
        return attrs


class ContactAssociationSerializer(NautobotModelSerializer):
    associated_object_type = ContentTypeField(queryset=ContentType.objects.all(), many=False)

    class Meta:
        model = ContactAssociation
        fields = "__all__"
        validators = []
        extra_kwargs = {
            "contact": {"required": False},
            "team": {"required": False},
        }

    def validate(self, attrs):
        # Validate uniqueness of (associated object, associated object type, contact/team, role)
        unique_together_fields = None

        if attrs.get("contact") and attrs.get("role"):
            unique_together_fields = (
                "associated_object_type",
                "associated_object_id",
                "contact",
                "role",
            )
        elif attrs.get("team") and attrs.get("role"):
            unique_together_fields = (
                "associated_object_type",
                "associated_object_id",
                "team",
                "role",
            )

        if unique_together_fields is not None:
            validator = UniqueTogetherValidator(
                queryset=ContactAssociation.objects.all(),
                fields=unique_together_fields,
            )
            validator(attrs, self)

        super().validate(attrs)

        return attrs


#
# ContentTypes
#


class ContentTypeSerializer(BaseModelSerializer):
    id = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:contenttype-detail")
    display = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = "__all__"

    @extend_schema_field(serializers.CharField)
    def get_display(self, instance):
        return instance.app_labeled_name


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


class DynamicGroupSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
    )

    class Meta:
        model = DynamicGroup
        fields = "__all__"
        extra_kwargs = {
            "children": {"source": "dynamic_group_memberships", "read_only": True},
            "filter": {"read_only": False, "required": False},
        }


class SavedViewSerializer(ValidatedModelSerializer):
    class Meta:
        model = SavedView
        fields = "__all__"


class UserSavedViewAssociationSerializer(ValidatedModelSerializer):
    class Meta:
        model = UserSavedViewAssociation
        fields = "__all__"
        validators = []


class StaticGroupAssociationSerializer(NautobotModelSerializer):
    associated_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
    )
    associated_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StaticGroupAssociation
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="DynamicGroupAssociatedObject",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(FeatureQuery("dynamic_groups").list_subclasses()),
        )
    )
    def get_associated_object(self, obj):
        if obj.associated_object is None:
            return None
        try:
            depth = get_nested_serializer_depth(self)
            return return_nested_serializer_data_based_on_depth(
                self, depth, obj, obj.associated_object, "associated_object"
            )
        except SerializerNotFound:
            return None


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
# External integrations
#


class ExternalIntegrationSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = ExternalIntegration
        fields = "__all__"


#
# File proxies
#


class FileProxySerializer(BaseModelSerializer):
    class Meta:
        model = FileProxy
        exclude = ["file"]


#
# Git repositories
#


class GitRepositorySerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
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
    variables = serializers.DictField(read_only=True)
    owner_content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("graphql_query_owners").get_query()),
        required=False,
        allow_null=True,
        default=None,
    )
    owner = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GraphQLQuery
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="GraphQLQueryOwner",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(FeatureQuery("graphql_query_owners").list_subclasses()),
            allow_null=True,
        )
    )
    def get_owner(self, obj):
        if obj.owner is None:
            return None
        depth = get_nested_serializer_depth(self)
        return return_nested_serializer_data_based_on_depth(self, depth, obj, obj.owner, "owner")


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

    def validate(self, attrs):
        # Validate that the parent object exists
        try:
            attrs["content_type"].get_object_for_this_type(id=attrs["object_id"])
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f"Invalid parent object: {attrs['content_type']} ID {attrs['object_id']}")

        # Enforce model validation
        super().validate(attrs)

        return attrs

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
    # task_queues and task_queues_override are added to maintain backward compatibility with versions pre v2.4.
    task_queues = serializers.JSONField(read_only=True, required=False)
    task_queues_override = serializers.BooleanField(read_only=True, required=False)

    class Meta:
        model = Job
        fields = "__all__"

    def validate(self, attrs):
        # note no validation for on creation of jobs because we do not support user creation of Job records via API
        if self.instance:
            has_sensitive_variables = attrs.get("has_sensitive_variables", self.instance.has_sensitive_variables)
            approval_required = attrs.get("approval_required", self.instance.approval_required)

            if approval_required and has_sensitive_variables:
                error_message = "A job with sensitive variables cannot also be marked as requiring approval"
                errors = {}

                if "approval_required" in attrs:
                    errors["approval_required"] = [error_message]
                if "has_sensitive_variables" in attrs:
                    errors["has_sensitive_variables"] = [error_message]

                raise serializers.ValidationError(errors)

        return super().validate(attrs)


class JobQueueSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = JobQueue
        fields = "__all__"


class JobQueueAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = JobQueueAssignment
        fields = "__all__"


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
    # queue is added to maintain backward compatibility with versions pre v2.4.
    queue = serializers.CharField(read_only=True, required=False)
    time_zone = TimeZoneSerializerField(required=False)

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
        extra_kwargs = {
            "files": {"read_only": True},
        }

    def get_field_names(self, declared_fields, info):
        """Add reverse relation to related FileProxy objects."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "files")
        return fields


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
    name = serializers.CharField(max_length=CHARFIELD_MAX_LENGTH, read_only=True)
    description = serializers.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False, read_only=True)
    test_methods = serializers.ListField(child=serializers.CharField(max_length=CHARFIELD_MAX_LENGTH))
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

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        conflicts = JobHook.check_for_conflicts(
            instance=self.instance,
            content_types=attrs.get("content_types"),
            job=attrs.get("job"),
            type_create=attrs.get("type_create"),
            type_update=attrs.get("type_update"),
            type_delete=attrs.get("type_delete"),
        )

        if conflicts:
            raise serializers.ValidationError(conflicts)

        return validated_attrs


class JobCreationSerializer(BaseModelSerializer):
    """
    Nested serializer specifically for use with `JobInputSerializer.schedule`.

    We don't use `WritableNestedSerializer` here because this is not used to look up
    an existing `ScheduledJob`, but instead used to specify parameters for creating one.
    """

    url = serializers.HyperlinkedIdentityField(view_name="extras-api:scheduledjob-detail")
    name = serializers.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    start_time = serializers.DateTimeField(format=None, required=False)

    class Meta:
        model = ScheduledJob
        fields = ["url", "name", "start_time", "interval", "crontab"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if attrs["interval"] in choices.JobExecutionType.SCHEDULE_CHOICES:
            if "name" not in attrs:
                raise serializers.ValidationError({"name": "Please provide a name for the job schedule."})

            if ("start_time" not in attrs and attrs["interval"] != choices.JobExecutionType.TYPE_CUSTOM) or (
                "start_time" in attrs and attrs["start_time"] < models.ScheduledJob.earliest_possible_time()
            ):
                raise serializers.ValidationError(
                    {
                        "start_time": "Please enter a valid date and time greater than or equal to the current date and time."
                    }
                )

            if attrs["interval"] == choices.JobExecutionType.TYPE_CUSTOM:
                if attrs.get("crontab") is None:
                    raise serializers.ValidationError({"crontab": "Please enter a valid crontab."})
                try:
                    models.ScheduledJob.get_crontab(attrs["crontab"])
                except Exception as e:
                    raise serializers.ValidationError({"crontab": e})

        return attrs


class JobInputSerializer(serializers.Serializer):
    data = serializers.JSONField(required=False, default=dict)
    schedule = JobCreationSerializer(required=False)
    task_queue = serializers.CharField(required=False, allow_blank=True)
    job_queue = serializers.CharField(required=False, allow_blank=True)


class JobMultiPartInputSerializer(serializers.Serializer):
    """JobMultiPartInputSerializer is a "flattened" version of JobInputSerializer for use with multipart/form-data submissions which only accept key-value pairs"""

    _schedule_name = serializers.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    _schedule_start_time = serializers.DateTimeField(format=None, required=False)
    _schedule_interval = ChoiceField(choices=JobExecutionType, required=False)
    _schedule_crontab = serializers.CharField(required=False, allow_blank=True)
    _task_queue = serializers.CharField(required=False, allow_blank=True)
    _job_queue = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if "_schedule_interval" in attrs and attrs["_schedule_interval"] != JobExecutionType.TYPE_IMMEDIATELY:
            if "_schedule_name" not in attrs:
                raise serializers.ValidationError({"_schedule_name": "Please provide a name for the job schedule."})

            if (
                "_schedule_start_time" not in attrs and attrs["_schedule_interval"] != JobExecutionType.TYPE_CUSTOM
            ) or (
                "_schedule_start_time" in attrs
                and attrs["_schedule_start_time"] < ScheduledJob.earliest_possible_time()
            ):
                raise serializers.ValidationError(
                    {
                        "_schedule_start_time": "Please enter a valid date and time greater than or equal to the current date and time."
                    }
                )

            if attrs["_schedule_interval"] == JobExecutionType.TYPE_CUSTOM:
                if attrs.get("_schedule_crontab") is None:
                    raise serializers.ValidationError({"_schedule_crontab": "Please enter a valid crontab."})
                try:
                    ScheduledJob.get_crontab(attrs["_schedule_crontab"])
                except Exception as e:
                    raise serializers.ValidationError({"_schedule_crontab": e})

        return attrs


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
# Metadata
#


class MetadataTypeSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("metadata").get_query()),
        many=True,
    )

    class Meta:
        model = MetadataType
        fields = "__all__"


class MetadataChoiceSerializer(ValidatedModelSerializer):
    class Meta:
        model = MetadataChoice
        fields = "__all__"


class ObjectMetadataValueJSONField(serializers.JSONField):
    """Special class to discern between itself and serializers.JSONField in NautobotCSVParser"""


class ObjectMetadataSerializer(ValidatedModelSerializer):
    assigned_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("metadata").get_query()),
    )
    assigned_object = serializers.SerializerMethodField()
    value = ObjectMetadataValueJSONField(allow_null=True, required=False)

    class Meta:
        model = ObjectMetadata
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="ObjectMetadataAssignedObject",
            resource_type_field_name="object_type",
            serializers=lambda: nested_serializers_for_models(FeatureQuery("metadata").list_subclasses()),
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


#
# Notes
#


class NoteSerializer(BaseModelSerializer):
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = "__all__"

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
    related_object_type = ContentTypeField(read_only=True)
    changed_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ObjectChange
        fields = "__all__"

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

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # check if tag is assigned to any of the removed content_types
        if self.instance is not None and self.instance.present_in_database and "content_types" in attrs:
            content_types_id = [content_type.id for content_type in attrs["content_types"]]
            errors = self.instance.validate_content_types_removal(content_types_id)

            if errors:
                raise serializers.ValidationError(errors)

        return attrs


#
# Teams
#


class TeamSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = Team
        fields = "__all__"
        extra_kwargs = {
            "contacts": {"required": False},
            "email": {"default": ""},
            "phone": {"default": ""},
        }
        # https://www.django-rest-framework.org/api-guide/validators/#optional-fields
        validators = []

    def validate(self, attrs):
        validator = UniqueTogetherValidator(queryset=Team.objects.all(), fields=("name", "phone", "email"))
        validator(attrs, self)
        return super().validate(attrs)


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

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        conflicts = Webhook.check_for_conflicts(
            instance=self.instance,
            content_types=attrs.get("content_types"),
            payload_url=attrs.get("payload_url"),
            type_create=attrs.get("type_create"),
            type_update=attrs.get("type_update"),
            type_delete=attrs.get("type_delete"),
        )

        if conflicts:
            raise serializers.ValidationError(conflicts)

        return validated_attrs


#
# More Git repositories
#


class GitRepositorySyncResponseSerializer(serializers.Serializer):
    """Serializer representing responses from the GitRepository.sync() POST endpoint."""

    message = serializers.CharField(read_only=True)
    job_result = JobResultSerializer(read_only=True)
