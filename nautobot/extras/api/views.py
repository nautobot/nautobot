from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import ProtectedError
from django.forms import ValidationError as FormsValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from graphene_django.views import GraphQLView
from graphql import GraphQLError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from nautobot.core.api.authentication import TokenPermissions
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.api.views import (
    BulkDestroyModelMixin,
    BulkUpdateModelMixin,
    ModelViewSet,
    ModelViewSetMixin,
    NautobotAPIVersionMixin,
    ReadOnlyModelViewSet,
)
from nautobot.core.events import publish_event
from nautobot.core.exceptions import CeleryWorkerNotRunningException
from nautobot.core.graphql import execute_saved_query
from nautobot.core.models.querysets import count_related
from nautobot.core.models.utils import serialize_object_v2
from nautobot.extras import filters
from nautobot.extras.choices import JobExecutionType, JobQueueTypeChoices
from nautobot.extras.filters import RoleFilterSet
from nautobot.extras.jobs import get_job
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
    TaggedItem,
    Team,
    UserSavedViewAssociation,
    Webhook,
)
from nautobot.extras.secrets.exceptions import SecretError
from nautobot.extras.utils import get_job_queue, get_worker_count

from . import serializers


class NotesViewSetMixin:
    def restrict_queryset(self, request, *args, **kwargs):
        """
        Apply "view" permissions on the POST /notes/ endpoint, otherwise as ModelViewSetMixin.
        """
        if request.user.is_authenticated and self.action == "notes":
            self.queryset = self.queryset.restrict(request.user, "view")
        else:
            super().restrict_queryset(request, *args, **kwargs)

    class CreateNotePermissions(TokenPermissions):
        """As nautobot.core.api.authentication.TokenPermissions, but enforcing add_note permission."""

        perms_map = {
            "GET": ["%(app_label)s.view_%(model_name)s", "extras.view_note"],
            "POST": ["%(app_label)s.view_%(model_name)s", "extras.add_note"],
        }

    @extend_schema(methods=["get"], filters=False, responses={200: serializers.NoteSerializer(many=True)})
    @extend_schema(
        methods=["post"],
        request=serializers.NoteInputSerializer,
        responses={201: serializers.NoteSerializer(many=False)},
    )
    @action(detail=True, url_path="notes", methods=["get", "post"], permission_classes=[CreateNotePermissions])
    def notes(self, request, *args, **kwargs):
        """
        API methods for returning or creating notes on an object.
        """
        obj = get_object_or_404(
            self.queryset, **{self.lookup_field: self.kwargs[self.lookup_url_kwarg or self.lookup_field]}
        )
        if request.method == "POST":
            content_type = ContentType.objects.get_for_model(obj)
            data = request.data
            data["assigned_object_id"] = obj.pk
            data["assigned_object_type"] = f"{content_type.app_label}.{content_type.model}"
            serializer = serializers.NoteSerializer(data=data, context={"request": request})

            # Create the new Note.
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        else:
            notes = self.paginate_queryset(obj.notes)
            serializer = serializers.NoteSerializer(notes, many=True, context={"request": request})

        return self.get_paginated_response(serializer.data)


#
#  Computed Fields
#


class ComputedFieldViewSet(NotesViewSetMixin, ModelViewSet):
    """
    Manage Computed Fields through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = ComputedField.objects.all()
    serializer_class = serializers.ComputedFieldSerializer
    filterset_class = filters.ComputedFieldFilterSet


#
# Config contexts
#


class ConfigContextQuerySetMixin:
    """
    Used by views that work with config context models (device and virtual machine).
    Provides a get_queryset() method which deals with adding the config context
    data annotation or not.
    """

    def get_queryset(self):
        """
        Build the proper queryset based on the request context

        If the `include` query param includes `config_context`, return the queryset annotated with config context.

        Else, return the base queryset.
        """
        queryset = super().get_queryset()
        request = self.get_serializer_context()["request"]
        if request is not None and "config_context" in request.query_params.get("include", []):
            return queryset.annotate_config_context_data()
        return queryset


class ConfigContextViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = ConfigContext.objects.all()
    serializer_class = serializers.ConfigContextSerializer
    filterset_class = filters.ConfigContextFilterSet


#
# Config context schemas
#


class ConfigContextSchemaViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = ConfigContextSchema.objects.all()
    serializer_class = serializers.ConfigContextSchemaSerializer
    filterset_class = filters.ConfigContextSchemaFilterSet


#
# ContentTypes
#


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of ContentTypes. Limit results to ContentTypes pertinent to Nautobot objects.
    """

    permission_classes = [IsAuthenticated]
    queryset = ContentType.objects.order_by("app_label", "model")
    serializer_class = serializers.ContentTypeSerializer
    filterset_class = filters.ContentTypeFilterSet


#
# Custom fields
#


class CustomFieldViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = CustomField.objects.all()
    serializer_class = serializers.CustomFieldSerializer
    filterset_class = filters.CustomFieldFilterSet


class CustomFieldChoiceViewSet(ModelViewSet):
    queryset = CustomFieldChoice.objects.all()
    serializer_class = serializers.CustomFieldChoiceSerializer
    filterset_class = filters.CustomFieldChoiceFilterSet


class CustomFieldModelViewSet(ModelViewSet):
    """
    Include the applicable set of CustomFields in the ModelViewSet context.
    """

    def get_serializer_context(self):
        # Gather all custom fields for the model
        content_type = ContentType.objects.get_for_model(self.queryset.model)
        custom_fields = content_type.custom_fields.all()

        context = super().get_serializer_context()
        context.update(
            {
                "custom_fields": custom_fields,
            }
        )
        return context


class NautobotModelViewSet(NotesViewSetMixin, CustomFieldModelViewSet):
    """Base class to use for API ViewSets based on OrganizationalModel or PrimaryModel.

    Can also be used for models derived from BaseModel, so long as they support Notes.
    """


#
# Contacts
#


class ContactViewSet(NautobotModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = serializers.ContactSerializer
    filterset_class = filters.ContactFilterSet


class ContactAssociationViewSet(NautobotModelViewSet):
    queryset = ContactAssociation.objects.all()
    serializer_class = serializers.ContactAssociationSerializer
    filterset_class = filters.ContactAssociationFilterSet


#
# Custom Links
#


class CustomLinkViewSet(NotesViewSetMixin, ModelViewSet):
    """
    Manage Custom Links through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = CustomLink.objects.all()
    serializer_class = serializers.CustomLinkSerializer
    filterset_class = filters.CustomLinkFilterSet


#
# Dynamic Groups
#


class DynamicGroupViewSet(NotesViewSetMixin, ModelViewSet):
    """
    Manage Dynamic Groups through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = DynamicGroup.objects.all()
    serializer_class = serializers.DynamicGroupSerializer
    filterset_class = filters.DynamicGroupFilterSet

    # FIXME(jathan): Figure out how to do dynamic `responses` serializer based on the `content_type`
    # of the DynamicGroup? May not be possible or even desirable to have a "dynamic schema".
    # @extend_schema(methods=["get"], responses={200: member_response})
    @action(detail=True, methods=["get"])
    def members(self, request, pk, *args, **kwargs):
        """List the member objects of this dynamic group."""
        instance = get_object_or_404(self.queryset, pk=pk)

        # Retrieve the serializer for the content_type and paginate the results
        member_model_class = instance.content_type.model_class()
        member_serializer_class = get_serializer_for_model(member_model_class)
        members = self.paginate_queryset(instance.members.restrict(request.user, "view"))
        member_serializer = member_serializer_class(members, many=True, context={"request": request})
        return self.get_paginated_response(member_serializer.data)


class DynamicGroupMembershipViewSet(ModelViewSet):
    """
    Manage Dynamic Group Memberships through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = DynamicGroupMembership.objects.all()
    serializer_class = serializers.DynamicGroupMembershipSerializer
    filterset_class = filters.DynamicGroupMembershipFilterSet


#
# Saved Views
#


class SavedViewViewSet(ModelViewSet):
    queryset = SavedView.objects.all()
    serializer_class = serializers.SavedViewSerializer
    filterset_class = filters.SavedViewFilterSet


class UserSavedViewAssociationViewSet(ModelViewSet):
    queryset = UserSavedViewAssociation.objects.all()
    serializer_class = serializers.UserSavedViewAssociationSerializer
    filterset_class = filters.UserSavedViewAssociationFilterSet


class StaticGroupAssociationViewSet(NautobotModelViewSet):
    """
    Manage Static Group Associations through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = StaticGroupAssociation.objects.all()
    serializer_class = serializers.StaticGroupAssociationSerializer
    filterset_class = filters.StaticGroupAssociationFilterSet

    def get_queryset(self):
        if (
            hasattr(self, "request")
            and self.request is not None
            and "dynamic_group" in self.request.GET
            and self.action in ["list", "retrieve"]
        ):
            self.queryset = StaticGroupAssociation.all_objects.all()
        return super().get_queryset()


#
# Export templates
#


class ExportTemplateViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = ExportTemplate.objects.all()
    serializer_class = serializers.ExportTemplateSerializer
    filterset_class = filters.ExportTemplateFilterSet


#
# External integrations
#


class ExternalIntegrationViewSet(NautobotModelViewSet):
    queryset = ExternalIntegration.objects.all()
    serializer_class = serializers.ExternalIntegrationSerializer
    filterset_class = filters.ExternalIntegrationFilterSet


#
# File proxies
#


class FileProxyViewSet(ReadOnlyModelViewSet):
    queryset = FileProxy.objects.all()
    serializer_class = serializers.FileProxySerializer
    filterset_class = filters.FileProxyFilterSet

    @extend_schema(
        methods=["get"],
        responses=OpenApiTypes.BINARY,
    )
    @action(
        detail=True,
        methods=["get"],
    )
    def download(self, request, *args, **kwargs):
        """Download the specified FileProxy."""
        file_proxy = self.get_object()
        return FileResponse(file_proxy.file.open("rb"), as_attachment=True)


#
# Git repositories
#


class GitRepositoryViewSet(NautobotModelViewSet):
    """
    Manage the use of Git repositories as external data sources.
    """

    queryset = GitRepository.objects.all()
    serializer_class = serializers.GitRepositorySerializer
    filterset_class = filters.GitRepositoryFilterSet

    @extend_schema(methods=["post"], responses={"200": serializers.GitRepositorySyncResponseSerializer}, request=None)
    # Since we are explicitly checking for `extras:change_gitrepository` in the API sync() method
    # We explicitly set the permission_classes to IsAuthenticated in the @action decorator
    # bypassing the default DRF permission check for `extras:add_gitrepository` and the permission check fall through to the function itself.
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def sync(self, request, pk):
        """
        Enqueue pull git repository and refresh data.
        """
        if not request.user.has_perm("extras.change_gitrepository"):
            raise PermissionDenied("This user does not have permission to make changes to Git repositories.")

        if not get_worker_count():
            raise CeleryWorkerNotRunningException()

        repository = get_object_or_404(GitRepository, id=pk)
        job_result = repository.sync(user=request.user)

        data = {
            # Kept message for backward compatibility for now
            "message": f"Repository {repository} sync job added to queue.",
            "job_result": job_result,
        }

        serializer = serializers.GitRepositorySyncResponseSerializer(data, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


#
# GraphQL Queries
#


class GraphQLQueryViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = GraphQLQuery.objects.all()
    serializer_class = serializers.GraphQLQuerySerializer
    filterset_class = filters.GraphQLQueryFilterSet

    @extend_schema(
        methods=["post"],
        request=serializers.GraphQLQueryInputSerializer,
        responses={"200": serializers.GraphQLQueryOutputSerializer},
    )
    @action(detail=True, methods=["post"])
    def run(self, request, pk):
        try:
            query = get_object_or_404(self.queryset, pk=pk)
            result = execute_saved_query(query.name, variables=request.data.get("variables"), request=request).to_dict()
            return Response(result)
        except GraphQLError as error:
            return Response(
                {"errors": [GraphQLView.format_error(error)]},
                status=status.HTTP_400_BAD_REQUEST,
            )


#
# Image attachments
#


class ImageAttachmentViewSet(ModelViewSet):
    queryset = ImageAttachment.objects.all()
    serializer_class = serializers.ImageAttachmentSerializer
    filterset_class = filters.ImageAttachmentFilterSet
    parser_classes = [JSONParser, NautobotCSVParser, MultiPartParser]


#
# Jobs
#


class JobViewSetBase(
    NautobotAPIVersionMixin,
    # note no CreateModelMixin
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    NotesViewSetMixin,
    ModelViewSetMixin,
    viewsets.GenericViewSet,
):
    queryset = Job.objects.all()
    serializer_class = serializers.JobSerializer
    filterset_class = filters.JobFilterSet

    def get_object(self):
        """Get the Job instance and reload the job class to ensure we have the latest version of the job code."""
        obj = super().get_object()
        get_job(obj.class_path, reload=True)

        return obj

    @extend_schema(responses={"200": serializers.JobVariableSerializer(many=True)})
    @action(detail=True, filterset_class=None)
    def variables(self, request, *args, **kwargs):
        """Get details of the input variables that may/must be specified to run a particular Job."""
        job_model = self.get_object()
        job_class = job_model.job_class
        if job_class is None:
            raise Http404
        variables_dict = job_class._get_vars()
        data = []
        for name, instance in variables_dict.items():
            entry = {"name": name, "type": instance.__class__.__name__}
            for key in [
                "label",
                "help_text",
                "required",
                "min_length",
                "max_length",
                "min_value",
                "max_value",
                "choices",
            ]:
                if key in instance.field_attrs:
                    entry[key] = instance.field_attrs[key]
            if "initial" in instance.field_attrs:
                entry["default"] = instance.field_attrs["initial"]
            if "queryset" in instance.field_attrs:
                content_type = ContentType.objects.get_for_model(instance.field_attrs["queryset"].model)
                entry["model"] = f"{content_type.app_label}.{content_type.model}"
            data.append(entry)
        return Response(data)

    def restrict_queryset(self, request, *args, **kwargs):
        """
        Apply special "run_job" permission as queryset filter on the /run/ endpoint, otherwise as ModelViewSetMixin.
        """
        if request.user.is_authenticated and self.action == "run":
            self.queryset = self.queryset.restrict(request.user, "run")
        else:
            super().restrict_queryset(request, *args, **kwargs)

    class JobRunTokenPermissions(TokenPermissions):
        """As nautobot.core.api.authentication.TokenPermissions, but enforcing run_job instead of add_job."""

        perms_map = {
            "POST": ["%(app_label)s.run_%(model_name)s"],
        }

    @extend_schema(
        methods=["post"],
        request={
            "application/json": serializers.JobInputSerializer,
            "multipart/form-data": serializers.JobMultiPartInputSerializer,
        },
        responses={"201": serializers.JobRunResponseSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[JobRunTokenPermissions],
        parser_classes=[JSONParser, MultiPartParser],
    )
    def run(self, request, *args, **kwargs):
        """Run the specified Job."""
        job_model = self.get_object()
        if not request.user.has_perm("extras.run_job"):
            raise PermissionDenied("This user does not have permission to run jobs.")
        if not job_model.enabled:
            raise PermissionDenied("This job is not enabled to be run.")
        if not job_model.installed:
            raise MethodNotAllowed(request.method, detail="This job is not presently installed and cannot be run")
        if job_model.has_sensitive_variables:
            if (
                "schedule" in request.data
                and "interval" in request.data["schedule"]
                and request.data["schedule"]["interval"] != JobExecutionType.TYPE_IMMEDIATELY
            ):
                raise ValidationError(
                    {"schedule": {"interval": ["Unable to schedule job: Job may have sensitive input variables"]}}
                )
            if job_model.approval_required:
                raise ValidationError(
                    "Unable to run or schedule job: "
                    "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval."
                    "One of these two flags must be removed before this job can be scheduled or run."
                )

        job_class = job_model.job_class
        if job_class is None:
            raise MethodNotAllowed(
                request.method, detail="This job's source code could not be located and cannot be run"
            )

        valid_queues = job_model.task_queues if job_model.task_queues else [settings.CELERY_TASK_DEFAULT_QUEUE]
        # default queue should be specified on the default_job_queue.
        default_valid_queue = job_model.default_job_queue.name

        # We need to call request.data for both cases as this is what pulls and caches the request data
        data = request.data
        files = None
        schedule_data = None

        # We must extract from the request:
        # - Job Form data (for submission to the job itself)
        # - Schedule data
        # - Desired task queue
        # Depending on request content type (largely for backwards compatibility) the keys at which these are found
        # are different
        if "multipart/form-data" in request.content_type:
            data = request._data.dict()  # .data will return data and files, we just want the data
            files = request.FILES

            # JobMultiPartInputSerializer is a "flattened" version of JobInputSerializer
            input_serializer = serializers.JobMultiPartInputSerializer(data=data, context={"request": request})
            input_serializer.is_valid(raise_exception=True)

            # TODO remove _task_queue related code in 3.0
            # _task_queue and _job_queue are both valid arguments in v2.4
            task_queue = input_serializer.validated_data.get(
                "_task_queue", None
            ) or input_serializer.validated_data.get("_job_queue", None)
            if not task_queue:
                task_queue = default_valid_queue

            # Log a warning if _task_queue and _job_queue fields are both specified out
            if input_serializer.validated_data.get("_task_queue", None) and input_serializer.validated_data.get(
                "_job_queue", None
            ):
                raise ValidationError(
                    {
                        "_task_queue": "_task_queue and _job_queue are both specified. Please specify only one or another."
                    }
                )

            # JobMultiPartInputSerializer only has keys for executing job (task_queue, etc),
            # everything else is a candidate for the job form's data.
            # job_class.validate_data will throw an error for any unexpected key/value pairs.
            non_job_keys = input_serializer.validated_data.keys()
            for non_job_key in non_job_keys:
                data.pop(non_job_key, None)

            # List of keys in serializer that are effectively exploded versions of the schedule dictionary
            # from JobInputSerializer
            schedule_keys = ("_schedule_name", "_schedule_start_time", "_schedule_interval", "_schedule_crontab")

            # Assign the key from the validated_data output to dictionary without prefixed "_schedule_"
            # For all the keys that are schedule keys
            # Assign only if the key is in the output since we don't want None's if not provided
            if any(schedule_key in non_job_keys for schedule_key in schedule_keys):
                schedule_data = {
                    k.replace("_schedule_", ""): input_serializer.validated_data[k]
                    for k in schedule_keys
                    if k in input_serializer.validated_data
                }

        else:
            input_serializer = serializers.JobInputSerializer(data=data, context={"request": request})
            input_serializer.is_valid(raise_exception=True)

            data = input_serializer.validated_data.get("data", {})
            # TODO remove _task_queue related code in 3.0
            # _task_queue and _job_queue are both valid arguments in v2.4
            task_queue = input_serializer.validated_data.get("task_queue", None) or input_serializer.validated_data.get(
                "job_queue", None
            )
            if not task_queue:
                task_queue = default_valid_queue

            # Log a warning if _task_queue and _job_queue fields are both specified out
            if input_serializer.validated_data.get("task_queue", None) and input_serializer.validated_data.get(
                "job_queue", None
            ):
                raise ValidationError(
                    {"task_queue": "task_queue and job_queue are both specified. Please specify only one or another."}
                )
            schedule_data = input_serializer.validated_data.get("schedule", None)

        if task_queue not in valid_queues:
            raise ValidationError({"task_queue": [f'"{task_queue}" is not a valid choice.']})

        cleaned_data = None
        try:
            cleaned_data = job_class.validate_data(data, files=files)
            cleaned_data = job_class.prepare_job_kwargs(cleaned_data)

        except FormsValidationError as e:
            # message_dict can only be accessed if ValidationError got a dict
            # in the constructor (saved as error_dict). Otherwise we get a list
            # of errors under messages
            return Response({"errors": e.message_dict if hasattr(e, "error_dict") else e.messages}, status=400)

        job_queue = get_job_queue(task_queue) or job_model.default_job_queue
        if job_queue.queue_type == JobQueueTypeChoices.TYPE_CELERY and not get_worker_count(queue=task_queue):
            raise CeleryWorkerNotRunningException(queue=task_queue)

        # Default to a null JobResult.
        job_result = None

        # Approval is not required for dryrun
        if job_class.supports_dryrun:
            dryrun = data.get("dryrun", False)
            approval_required = not dryrun and job_model.approval_required
        else:
            approval_required = job_model.approval_required

        # Set schedule for jobs that require approval but request did not supply schedule data
        if schedule_data is None and approval_required:
            schedule_data = {"interval": JobExecutionType.TYPE_IMMEDIATELY}

        # Skip creating a ScheduledJob when job can be executed immediately
        elif schedule_data and schedule_data["interval"] == JobExecutionType.TYPE_IMMEDIATELY and not approval_required:
            schedule_data = None

        # Try to create a ScheduledJob, or...
        if schedule_data:
            schedule = ScheduledJob.create_schedule(
                job_model,
                request.user,
                name=schedule_data.get("name"),
                start_time=schedule_data.get("start_time"),
                interval=schedule_data.get("interval"),
                crontab=schedule_data.get("crontab", ""),
                approval_required=approval_required,
                job_queue=job_queue,
                **job_class.serialize_data(cleaned_data),
            )
        else:
            schedule = None

        # ... If we can't create one, create a JobResult instead.
        if schedule is None:
            job_result = JobResult.enqueue_job(
                job_model,
                request.user,
                job_queue=job_queue,
                **job_class.serialize_data(cleaned_data),
            )

        # New-style JobModelViewSet response - serialize the schedule or job_result as appropriate
        data = {"scheduled_job": None, "job_result": None}
        if schedule:
            data["scheduled_job"] = serializers.ScheduledJobSerializer(schedule, context={"request": request}).data
        if job_result:
            data["job_result"] = serializers.JobResultSerializer(job_result, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)


class JobViewSet(
    JobViewSetBase,
    mixins.ListModelMixin,
    BulkUpdateModelMixin,
    BulkDestroyModelMixin,
):
    lookup_value_regex = r"[-0-9a-fA-F]+"

    def perform_destroy(self, instance):
        if instance.module_name.startswith("nautobot."):
            raise ProtectedError(
                f"Unable to delete Job {instance}. System Job cannot be deleted",
                [],
            )
        super().perform_destroy(instance)


@extend_schema_view(
    destroy=extend_schema(operation_id="extras_jobs_destroy_by_name"),
    partial_update=extend_schema(operation_id="extras_jobs_partial_update_by_name"),
    notes=extend_schema(methods=["get"], operation_id="extras_jobs_notes_list_by_name"),
    retrieve=extend_schema(operation_id="extras_jobs_retrieve_by_name"),
    run=extend_schema(
        methods=["post"],
        operation_id="extras_jobs_run_create_by_name",
        request={
            "application/json": serializers.JobInputSerializer,
            "multipart/form-data": serializers.JobMultiPartInputSerializer,
        },
        responses={"201": serializers.JobRunResponseSerializer},
    ),
    update=extend_schema(operation_id="extras_jobs_update_by_name"),
    variables=extend_schema(operation_id="extras_jobs_variables_list_by_name"),
)
@extend_schema_view(
    notes=extend_schema(methods=["post"], operation_id="extras_jobs_notes_create_by_name"),
)
class JobByNameViewSet(
    JobViewSetBase,
):
    lookup_field = "name"
    lookup_url_kwarg = "name"
    lookup_value_regex = r"[^/]+"


#
# Job Hooks
#


class JobHooksViewSet(NautobotModelViewSet):
    """
    Manage job hooks through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = JobHook.objects.all()
    serializer_class = serializers.JobHookSerializer
    filterset_class = filters.JobHookFilterSet


#
# Job Queues
#


class JobQueueViewSet(NautobotModelViewSet):
    """
    Manage job queues through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = JobQueue.objects.all()
    serializer_class = serializers.JobQueueSerializer
    filterset_class = filters.JobQueueFilterSet


class JobQueueAssignmentViewSet(ModelViewSet):
    """
    Manage job queue assignments through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = JobQueueAssignment.objects.all()
    serializer_class = serializers.JobQueueAssignmentSerializer
    filterset_class = filters.JobQueueAssignmentFilterSet


#
# Job Results
#


class JobLogEntryViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of job log entries.
    """

    queryset = JobLogEntry.objects.all()
    serializer_class = serializers.JobLogEntrySerializer
    filterset_class = filters.JobLogEntryFilterSet


class JobResultViewSet(
    # DRF mixins:
    # note no CreateModelMixin or UpdateModelMixin
    mixins.DestroyModelMixin,
    # Nautobot mixins:
    BulkDestroyModelMixin,
    # Base class
    ReadOnlyModelViewSet,
):
    """
    Retrieve a list of job results
    """

    queryset = JobResult.objects.all()
    serializer_class = serializers.JobResultSerializer
    filterset_class = filters.JobResultFilterSet

    @action(detail=True)
    def logs(self, request, pk=None):
        job_result = self.get_object()
        logs = job_result.job_log_entries.all()
        serializer = serializers.JobLogEntrySerializer(logs, context={"request": request}, many=True)
        return Response(serializer.data)


#
# Job Button
#


class JobButtonViewSet(NotesViewSetMixin, ModelViewSet):
    """
    Manage Job Buttons through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = JobButton.objects.all()
    serializer_class = serializers.JobButtonSerializer
    filterset_class = filters.JobButtonFilterSet


#
# Scheduled Jobs
#


class ScheduledJobViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of scheduled jobs
    """

    queryset = ScheduledJob.objects.all()
    serializer_class = serializers.ScheduledJobSerializer
    filterset_class = filters.ScheduledJobFilterSet

    def restrict_queryset(self, request, *args, **kwargs):
        """
        Apply special permissions as queryset filter on the /approve/, /deny/, and /dry-run/ endpoints.

        Otherwise, same as ModelViewSetMixin.
        """
        action_to_method = {"approve": "change", "deny": "delete", "dry-run": "view"}
        if request.user.is_authenticated and self.action in action_to_method:
            self.queryset = self.queryset.restrict(request.user, action_to_method[self.action])
        else:
            super().restrict_queryset(request, *args, **kwargs)

    class ScheduledJobChangePermissions(TokenPermissions):
        """
        As nautobot.core.api.authentication.TokenPermissions, but enforcing change_scheduledjob not add_scheduledjob.
        """

        perms_map = {
            "POST": ["%(app_label)s.change_%(model_name)s"],
        }

    @extend_schema(
        methods=["post"],
        responses={"200": serializers.ScheduledJobSerializer},
        request=None,
        parameters=[
            OpenApiParameter(
                "force",
                location=OpenApiParameter.QUERY,
                description="force execution even if start time has passed",
                type=OpenApiTypes.BOOL,
            )
        ],
    )
    @action(detail=True, methods=["post"], permission_classes=[ScheduledJobChangePermissions])
    def approve(self, request, pk):
        scheduled_job = get_object_or_404(self.queryset, pk=pk)

        if not Job.objects.check_perms(request.user, instance=scheduled_job.job_model, action="approve"):
            raise PermissionDenied("You do not have permission to approve this request.")

        # Mark the scheduled_job as approved, allowing the schedular to schedule the job execution task
        if request.user == scheduled_job.user:
            # The requestor *cannot* approve their own job
            return Response("You cannot approve your own job request!", status=403)

        if (
            scheduled_job.one_off
            and scheduled_job.start_time < timezone.now()
            and not request.query_params.get("force")
        ):
            return Response(
                "The job's start time is in the past. If you want to force a run anyway, add the `force` query parameter.",
                status=400,
            )

        scheduled_job.approved_by_user = request.user
        scheduled_job.approved_at = timezone.now()
        scheduled_job.save()
        publish_event_payload = {"data": serialize_object_v2(scheduled_job)}
        publish_event(topic="nautobot.jobs.approval.approved", payload=publish_event_payload)
        serializer = serializers.ScheduledJobSerializer(scheduled_job, context={"request": request})

        return Response(serializer.data)

    class ScheduledJobDeletePermissions(TokenPermissions):
        """
        As nautobot.core.api.authentication.TokenPermissions, but enforcing delete_scheduledjob not add_scheduledjob.
        """

        perms_map = {
            "POST": ["%(app_label)s.delete_%(model_name)s"],
        }

    @extend_schema(
        methods=["post"],
        request=None,
    )
    @action(detail=True, methods=["post"], permission_classes=[ScheduledJobDeletePermissions])
    def deny(self, request, pk):
        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)

        if not Job.objects.check_perms(request.user, instance=scheduled_job.job_model, action="approve"):
            raise PermissionDenied("You do not have permission to deny this request.")

        publish_event_payload = {"data": serialize_object_v2(scheduled_job)}
        publish_event(topic="nautobot.jobs.approval.denied", payload=publish_event_payload)
        scheduled_job.delete()

        return Response(None)

    class ScheduledJobViewPermissions(TokenPermissions):
        """
        As nautobot.core.api.authentication.TokenPermissions, but enforcing view_scheduledjob not add_scheduledjob.
        """

        perms_map = {
            "POST": ["%(app_label)s.view_%(model_name)s"],
        }

    @extend_schema(
        methods=["post"],
        responses={"200": serializers.JobResultSerializer},
        request=None,
    )
    @action(
        detail=True,
        name="Dry Run",
        url_path="dry-run",
        methods=["post"],
        permission_classes=[ScheduledJobViewPermissions],
    )
    def dry_run(self, request, pk):
        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)
        job_model = scheduled_job.job_model
        if job_model is None or not job_model.runnable:
            raise MethodNotAllowed("This job cannot be dry-run at this time.")
        if not job_model.supports_dryrun:
            raise MethodNotAllowed("This job does not support dry-run.")
        if not Job.objects.check_perms(request.user, instance=job_model, action="run"):
            raise PermissionDenied("You do not have permission to run this job.")

        # Immediately enqueue the job
        job_class = get_job(job_model.class_path, reload=True)
        job_kwargs = job_class.prepare_job_kwargs(scheduled_job.kwargs or {})
        job_kwargs["dryrun"] = True
        job_result = JobResult.enqueue_job(
            job_model,
            request.user,
            celery_kwargs=scheduled_job.celery_kwargs or {},
            **job_class.serialize_data(job_kwargs),
        )
        serializer = serializers.JobResultSerializer(job_result, context={"request": request})

        return Response(serializer.data)


#
# Metadata
#


class MetadataTypeViewSet(NautobotModelViewSet):
    queryset = MetadataType.objects.all()
    serializer_class = serializers.MetadataTypeSerializer
    filterset_class = filters.MetadataTypeFilterSet


class MetadataChoiceViewSet(ModelViewSet):
    queryset = MetadataChoice.objects.all()
    serializer_class = serializers.MetadataChoiceSerializer
    filterset_class = filters.MetadataChoiceFilterSet


class ObjectMetadataViewSet(ModelViewSet):
    queryset = ObjectMetadata.objects.all()
    serializer_class = serializers.ObjectMetadataSerializer
    filterset_class = filters.ObjectMetadataFilterSet


#
# Notes
#


class NoteViewSet(ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = serializers.NoteSerializer
    filterset_class = filters.NoteFilterSet

    # Assign user from request
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


#
# Change logging
#


class ObjectChangeViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of recent changes.
    """

    queryset = ObjectChange.objects.all()
    serializer_class = serializers.ObjectChangeSerializer
    filterset_class = filters.ObjectChangeFilterSet


#
#  Relationships
#


class RelationshipViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = Relationship.objects.all()
    serializer_class = serializers.RelationshipSerializer
    filterset_class = filters.RelationshipFilterSet


class RelationshipAssociationViewSet(ModelViewSet):
    queryset = RelationshipAssociation.objects.all()
    serializer_class = serializers.RelationshipAssociationSerializer
    filterset_class = filters.RelationshipAssociationFilterSet


#
# Roles
#


class RoleViewSet(NautobotModelViewSet):
    queryset = Role.objects.all()
    serializer_class = serializers.RoleSerializer
    filterset_class = RoleFilterSet


#
# Secrets
#


class SecretsViewSet(NautobotModelViewSet):
    """
    Manage Secrets through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = Secret.objects.all()
    serializer_class = serializers.SecretSerializer
    filterset_class = filters.SecretFilterSet

    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "result": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            }
        },
    )
    @action(methods=["GET"], detail=True)
    def check(self, request, pk):
        """Check that a secret's value is accessible."""
        result = False
        message = "Unknown error"
        try:
            self.get_object().get_value()
            result = True
            message = "Passed"
        except SecretError as e:
            message = str(e)
        response = {"result": result, "message": message}
        return Response(response)


class SecretsGroupViewSet(NautobotModelViewSet):
    """
    Manage Secrets Groups through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = SecretsGroup.objects.all()
    serializer_class = serializers.SecretsGroupSerializer
    filterset_class = filters.SecretsGroupFilterSet


class SecretsGroupAssociationViewSet(ModelViewSet):
    """
    Manage Secrets Group Associations through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = SecretsGroupAssociation.objects.all()
    serializer_class = serializers.SecretsGroupAssociationSerializer
    filterset_class = filters.SecretsGroupAssociationFilterSet


#
# Statuses
#


class StatusViewSet(NautobotModelViewSet):
    """
    View and manage custom status choices for objects with a `status` field.
    """

    queryset = Status.objects.all()
    serializer_class = serializers.StatusSerializer
    filterset_class = filters.StatusFilterSet


#
# Tags
#


class TagViewSet(NautobotModelViewSet):
    queryset = Tag.objects.annotate(tagged_items=count_related(TaggedItem, "tag"))
    serializer_class = serializers.TagSerializer
    filterset_class = filters.TagFilterSet


#
# Teams
#


class TeamViewSet(NautobotModelViewSet):
    queryset = Team.objects.all()
    serializer_class = serializers.TeamSerializer
    filterset_class = filters.TeamFilterSet


#
# Webhooks
#


class WebhooksViewSet(NotesViewSetMixin, ModelViewSet):
    """
    Manage Webhooks through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = Webhook.objects.all()
    serializer_class = serializers.WebhookSerializer
    filterset_class = filters.WebhookFilterSet
