from datetime import timedelta
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError as FormsValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from graphene_django.views import GraphQLView
from graphql import GraphQLError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework import mixins, viewsets

from nautobot.core.api.authentication import TokenPermissions
from nautobot.core.api.filter_backends import NautobotFilterBackend
from nautobot.core.api.metadata import ContentTypeMetadata, StatusFieldMetadata
from nautobot.core.api.views import (
    BulkDestroyModelMixin,
    BulkUpdateModelMixin,
    ModelViewSet,
    ReadOnlyModelViewSet,
)
from nautobot.core.graphql import execute_saved_query
from nautobot.extras import filters
from nautobot.extras.choices import JobExecutionType, JobResultStatusChoices
from nautobot.extras.datasources import enqueue_pull_git_repository_and_refresh_data
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    DynamicGroup,
    DynamicGroupMembership,
    CustomLink,
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
    TaggedItem,
    Webhook,
)
from nautobot.extras.models import CustomField, CustomFieldChoice
from nautobot.extras.jobs import run_job
from nautobot.extras.utils import get_job_content_type, get_worker_count
from nautobot.utilities.exceptions import CeleryWorkerNotRunningException
from nautobot.utilities.api import get_serializer_for_model
from nautobot.utilities.utils import (
    copy_safe_request,
    count_related,
    SerializerForAPIVersions,
    versioned_serializer_selector,
)
from . import nested_serializers, serializers


class ExtrasRootView(APIRootView):
    """
    Extras API root view
    """

    def get_view_name(self):
        return "Extras"


class NotesViewSetMixin:
    @extend_schema(methods=["get"], filters=False, responses={200: serializers.NoteSerializer(many=True)})
    @extend_schema(
        methods=["post"],
        request=serializers.NoteInputSerializer,
        responses={201: serializers.NoteSerializer(many=False)},
    )
    @action(detail=True, url_path="notes", methods=["get", "post"])
    def notes(self, request, pk=None):
        """
        API methods for returning or creating notes on an object.
        """
        obj = get_object_or_404(self.queryset, pk=pk)
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


class ComputedFieldViewSet(ModelViewSet, NotesViewSetMixin):
    """
    Manage Computed Fields through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = ComputedField.objects.all()
    serializer_class = serializers.ComputedFieldSerializer
    filterset_class = filters.ComputedFieldFilterSet


#
# Config contexts
#


class ConfigContextFilterBackend(NautobotFilterBackend):
    """
    Used by views that work with config context models (device and virtual machine).

    Recognizes that "exclude" is not a filterset parameter but rather a view parameter (see ConfigContextQuerySetMixin)
    """

    def get_filterset_kwargs(self, request, queryset, view):
        kwargs = super().get_filterset_kwargs(request, queryset, view)
        try:
            kwargs["data"].pop("exclude")
        except KeyError:
            pass
        return kwargs


class ConfigContextQuerySetMixin:
    """
    Used by views that work with config context models (device and virtual machine).
    Provides a get_queryset() method which deals with adding the config context
    data annotation or not.
    """

    filter_backends = [ConfigContextFilterBackend]

    def get_queryset(self):
        """
        Build the proper queryset based on the request context

        If the `brief` query param equates to True or the `exclude` query param
        includes `config_context` as a value, return the base queryset.

        Else, return the queryset annotated with config context data
        """
        queryset = super().get_queryset()
        request = self.get_serializer_context()["request"]
        if self.brief or (request is not None and "config_context" in request.query_params.get("exclude", [])):
            return queryset
        return queryset.annotate_config_context_data()


class ConfigContextViewSet(ModelViewSet, NotesViewSetMixin):
    # v2 TODO(jathan): Replace prefetch_related with select_related (except the
    # plural ones are b2 m2m)
    queryset = ConfigContext.objects.prefetch_related(
        "regions",
        "sites",
        "roles",
        "device_types",
        "platforms",
        "tenant_groups",
        "tenants",
    )
    serializer_class = serializers.ConfigContextSerializer
    filterset_class = filters.ConfigContextFilterSet


#
# Config context schemas
#


class ConfigContextSchemaViewSet(ModelViewSet, NotesViewSetMixin):
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

    queryset = ContentType.objects.order_by("app_label", "model")
    serializer_class = serializers.ContentTypeSerializer
    filterset_class = filters.ContentTypeFilterSet


#
# Custom fields
#


@extend_schema_view(
    bulk_partial_update=extend_schema(
        filters=False,
        request=serializers.CustomFieldSerializerVersion12(many=True),
        responses={"200": serializers.CustomFieldSerializerVersion12(many=True)},
        versions=["1.2", "1.3"],
    ),
    bulk_update=extend_schema(
        filters=False,
        request=serializers.CustomFieldSerializerVersion12(many=True),
        responses={"200": serializers.CustomFieldSerializerVersion12(many=True)},
        versions=["1.2", "1.3"],
    ),
    create=extend_schema(
        request=serializers.CustomFieldSerializerVersion12,
        responses={"201": serializers.CustomFieldSerializerVersion12},
        versions=["1.2", "1.3"],
    ),
    list=extend_schema(
        responses={"200": serializers.CustomFieldSerializerVersion12(many=True)}, versions=["1.2", "1.3"]
    ),
    partial_update=extend_schema(
        request=serializers.CustomFieldSerializerVersion12,
        responses={"200": serializers.CustomFieldSerializerVersion12},
        versions=["1.2", "1.3"],
    ),
    retrieve=extend_schema(responses={"200": serializers.CustomFieldSerializerVersion12}, versions=["1.2", "1.3"]),
    update=extend_schema(
        request=serializers.CustomFieldSerializerVersion12,
        responses={"200": serializers.CustomFieldSerializerVersion12},
        versions=["1.2", "1.3"],
    ),
)
class CustomFieldViewSet(ModelViewSet, NotesViewSetMixin):
    metadata_class = ContentTypeMetadata
    queryset = CustomField.objects.all()
    serializer_class = serializers.CustomFieldSerializer
    filterset_class = filters.CustomFieldFilterSet

    def get_serializer_class(self):
        serializer_choices = (
            SerializerForAPIVersions(versions=["1.2", "1.3"], serializer=serializers.CustomFieldSerializerVersion12),
        )
        return versioned_serializer_selector(
            obj=self,
            serializer_choices=serializer_choices,
            default_serializer=super().get_serializer_class(),
        )


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


class NautobotModelViewSet(CustomFieldModelViewSet, NotesViewSetMixin):
    """Base class to use for API ViewSets based on OrganizationalModel or PrimaryModel.

    Can also be used for models derived from BaseModel, so long as they support Notes.
    """


#
# Custom Links
#


class CustomLinkViewSet(ModelViewSet, NotesViewSetMixin):
    """
    Manage Custom Links through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = CustomLink.objects.all()
    serializer_class = serializers.CustomLinkSerializer
    filterset_class = filters.CustomLinkFilterSet


#
# Dynamic Groups
#


class DynamicGroupViewSet(ModelViewSet, NotesViewSetMixin):
    """
    Manage Dynamic Groups through DELETE, GET, POST, PUT, and PATCH requests.
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DynamicGroup.objects.prefetch_related("content_type")
    serializer_class = serializers.DynamicGroupSerializer
    filterset_class = filters.DynamicGroupFilterSet

    # FIXME(jathan): Figure out how to do dynamic `responses` serializer based on the `content_type`
    # of the DynamicGroup? May not be possible or even desirable to have a "dynamic schema".
    # @extend_schema(methods=["get"], responses={200: member_response})
    @action(detail=True, methods=["get"])
    def members(self, request, pk, *args, **kwargs):
        """List member objects of the same type as the `content_type` for this dynamic group."""
        instance = get_object_or_404(self.queryset, pk=pk)

        # Retrieve the serializer for the content_type and paginate the results
        member_model_class = instance.content_type.model_class()
        member_serializer_class = get_serializer_for_model(member_model_class)
        members = self.paginate_queryset(instance.members)
        member_serializer = member_serializer_class(members, many=True, context={"request": request})
        return self.get_paginated_response(member_serializer.data)


class DynamicGroupMembershipViewSet(ModelViewSet):
    """
    Manage Dynamic Group Memberships through DELETE, GET, POST, PUT, and PATCH requests.
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DynamicGroupMembership.objects.prefetch_related("group", "parent_group")
    serializer_class = serializers.DynamicGroupMembershipSerializer
    filterset_class = filters.DynamicGroupMembershipFilterSet


#
# Export templates
#


class ExportTemplateViewSet(ModelViewSet, NotesViewSetMixin):
    metadata_class = ContentTypeMetadata
    queryset = ExportTemplate.objects.all()
    serializer_class = serializers.ExportTemplateSerializer
    filterset_class = filters.ExportTemplateFilterSet


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

    @extend_schema(methods=["post"], request=serializers.GitRepositorySerializer)
    @action(detail=True, methods=["post"])
    def sync(self, request, pk):
        """
        Enqueue pull git repository and refresh data.
        """
        if not request.user.has_perm("extras.change_gitrepository"):
            raise PermissionDenied("This user does not have permission to make changes to Git repositories.")

        if not get_worker_count():
            raise CeleryWorkerNotRunningException()

        repository = get_object_or_404(GitRepository, id=pk)
        enqueue_pull_git_repository_and_refresh_data(repository, request)
        return Response({"message": f"Repository {repository} sync job added to queue."})


#
# GraphQL Queries
#


class GraphQLQueryViewSet(ModelViewSet, NotesViewSetMixin):
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
            result = execute_saved_query(query.slug, variables=request.data.get("variables"), request=request).to_dict()
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
    metadata_class = ContentTypeMetadata
    queryset = ImageAttachment.objects.all()
    serializer_class = serializers.ImageAttachmentSerializer
    filterset_class = filters.ImageAttachmentFilterSet


#
# Jobs
#


def _create_schedule(serializer, data, commit, job, job_model, request, celery_kwargs=dict, task_queue=None):
    """
    This is an internal function to create a scheduled job from API data.
    It has to handle both once-offs (i.e. of type TYPE_FUTURE) and interval
    jobs.
    """
    job_kwargs = {
        "data": data,
        "request": copy_safe_request(request),
        "user": request.user.pk,
        "commit": commit,
        "name": job.class_path,
        "celery_kwargs": celery_kwargs,
        "task_queue": task_queue,
    }
    type_ = serializer["interval"]
    if type_ == JobExecutionType.TYPE_IMMEDIATELY:
        time = timezone.now()
        name = serializer.get("name") or f"{job.name} - {time}"
    elif type_ == JobExecutionType.TYPE_CUSTOM:
        time = serializer.get("start_time")  # doing .get("key", "default") returns None instead of "default"
        if time is None:
            # "start_time" is checked against models.ScheduledJob.earliest_possible_time()
            # which returns timezone.now() + timedelta(seconds=15)
            time = timezone.now() + timedelta(seconds=20)
        name = serializer["name"]
    else:
        time = serializer["start_time"]
        name = serializer["name"]
    crontab = serializer.get("crontab", "")

    # 2.0 TODO: To revisit this as part of a larger Jobs cleanup in 2.0.
    #
    # We pass in job_class and job_model here partly for forward/backward compatibility logic, and
    # part fallback safety. It's mildly useful to store both the class_path string and the JobModel
    # FK on the ScheduledJob, as in the case where the JobModel gets deleted (and the FK becomes
    # null) you still have a bit of context on the ScheduledJob as to what it was originally
    # scheduled for.
    scheduled_job = ScheduledJob(
        name=name,
        task="nautobot.extras.jobs.scheduled_job_handler",
        job_class=job.class_path,
        job_model=job_model,
        start_time=time,
        description=f"Nautobot job {name} scheduled by {request.user} on {time}",
        kwargs=job_kwargs,
        interval=type_,
        one_off=(type_ == JobExecutionType.TYPE_FUTURE),
        user=request.user,
        approval_required=job_model.approval_required,
        crontab=crontab,
        queue=task_queue,
    )
    scheduled_job.save()
    return scheduled_job


def _run_job(request, job_model, legacy_response=False):
    """An internal function providing logic shared between JobModelViewSet.run() and JobViewSet.run()."""
    if not request.user.has_perm("extras.run_job"):
        raise PermissionDenied("This user does not have permission to run jobs.")
    if not job_model.enabled:
        raise PermissionDenied("This job is not enabled to be run.")
    if not job_model.installed:
        raise MethodNotAllowed(request.method, detail="This job is not presently installed and cannot be run")
    if job_model.has_sensitive_variables:
        if request.data.get("schedule") and request.data["schedule"]["interval"] != JobExecutionType.TYPE_IMMEDIATELY:
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
        raise MethodNotAllowed(request.method, detail="This job's source code could not be located and cannot be run")
    job = job_class()

    valid_queues = job_model.task_queues if job_model.task_queues else [settings.CELERY_TASK_DEFAULT_QUEUE]
    # Get a default queue from either the job model's specified task queue or system default to fall back on if request doesn't provide one
    default_valid_queue = valid_queues[0]

    # We need to call request.data for both cases as this is what pulls and caches the request data
    data = request.data
    files = None
    schedule_data = None

    # We must extract from the request:
    # - Job Form data (for submission to the job itself)
    # - Schedule data
    # - Commit flag state
    # - Desired task queue
    # Depending on request content type (largely for backwards compatibility) the keys at which these are found are different
    if "multipart/form-data" in request.content_type:
        data = request._data.dict()  # .data will return data and files, we just want the data
        files = request.FILES

        # JobMultiPartInputSerializer is a "flattened" version of JobInputSerializer
        input_serializer = serializers.JobMultiPartInputSerializer(data=data, context={"request": request})
        input_serializer.is_valid(raise_exception=True)

        commit = input_serializer.validated_data.get("_commit", None)
        task_queue = input_serializer.validated_data.get("_task_queue", default_valid_queue)

        # JobMultiPartInputSerializer only has keys for executing job (commit, task_queue, etc),
        # everything else is a candidate for the job form's data.
        # job_class.validate_data will throw an error for any unexpected key/value pairs.
        non_job_keys = input_serializer.validated_data.keys()
        for non_job_key in non_job_keys:
            data.pop(non_job_key, None)

        # List of keys in serializer that are effectively exploded versions of the schedule dictionary from JobInputSerializer
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
        commit = input_serializer.validated_data.get("commit", None)
        task_queue = input_serializer.validated_data.get("task_queue", default_valid_queue)
        schedule_data = input_serializer.validated_data.get("schedule", None)

    if commit is None:
        commit = job_model.commit_default

    if task_queue not in valid_queues:
        raise ValidationError({"task_queue": [f'"{task_queue}" is not a valid choice.']})

    cleaned_data = None
    try:
        cleaned_data = job.validate_data(data, files=files)
        cleaned_data.pop(
            "_commit", None
        )  # We don't get commit from the form, instead it's part of the serializer's validated data

    except FormsValidationError as e:
        # message_dict can only be accessed if ValidationError got a dict
        # in the constructor (saved as error_dict). Otherwise we get a list
        # of errors under messages
        return Response({"errors": e.message_dict if hasattr(e, "error_dict") else e.messages}, status=400)

    if not get_worker_count(queue=task_queue):
        raise CeleryWorkerNotRunningException(queue=task_queue)

    job_content_type = get_job_content_type()

    # Default to a null JobResult.
    job_result = None

    # Assert that a job with `approval_required=True` has a schedule that enforces approval and
    # executes immediately.
    if schedule_data is None and job_model.approval_required:
        schedule_data = {"interval": JobExecutionType.TYPE_IMMEDIATELY}

    # Skip creating a ScheduledJob when job can be executed immediately
    elif (
        schedule_data
        and schedule_data["interval"] == JobExecutionType.TYPE_IMMEDIATELY
        and not job_model.approval_required
    ):
        schedule_data = None

    # Try to create a ScheduledJob, or...
    if schedule_data:
        schedule = _create_schedule(
            schedule_data,
            job_class.serialize_data(cleaned_data),
            commit,
            job,
            job_model,
            request,
            celery_kwargs={"queue": task_queue},
            task_queue=input_serializer.validated_data.get("task_queue", None),
        )
    else:
        schedule = None

    # ... If we can't create one, create a JobResult instead.
    if schedule is None:
        job_result = JobResult.enqueue_job(
            run_job,
            job.class_path,
            job_content_type,
            request.user,
            celery_kwargs={"queue": task_queue},
            data=job_class.serialize_data(cleaned_data),
            request=copy_safe_request(request),
            commit=commit,
            task_queue=input_serializer.validated_data.get("task_queue", None),
        )
        job.result = job_result

    if legacy_response:
        # Old-style JobViewSet response - serialize the Job class in the response for some reason?
        serializer = serializers.JobClassDetailSerializer(job, context={"request": request})
        return Response(serializer.data)
    else:
        # New-style JobModelViewSet response - serialize the schedule or job_result as appropriate
        data = {"schedule": None, "job_result": None}
        if schedule:
            data["schedule"] = nested_serializers.NestedScheduledJobSerializer(
                schedule, context={"request": request}
            ).data
        if job_result:
            data["job_result"] = nested_serializers.NestedJobResultSerializer(
                job_result, context={"request": request}
            ).data
        return Response(data, status=status.HTTP_201_CREATED)


class JobViewSet(
    # DRF mixins:
    # note no CreateModelMixin
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    # Nautobot mixins:
    BulkUpdateModelMixin,
    BulkDestroyModelMixin,
    # Base class
    ReadOnlyModelViewSet,
    NotesViewSetMixin,
):
    queryset = Job.objects.all()
    serializer_class = serializers.JobSerializer
    filterset_class = filters.JobFilterSet

    # Custom schema for the deprecated 1.2 API version of this endpoint.
    # For 1.3 and later, the standard autogenerated API schema is correct and does not need to be customized here.
    @extend_schema(
        filters=False,
        responses={"200": serializers.JobClassSerializer(many=True)},
        versions=["1.2"],
    )
    def list(self, request, *args, **kwargs):
        """List all known Jobs."""
        if request.major_version > 1 or request.minor_version >= 3:
            # API version 1.3 or later - standard model-based response
            return super().list(request, *args, **kwargs)

        # API version 1.2 or earlier - serialize JobClass records
        if not request.user.has_perm("extras.view_job"):
            raise PermissionDenied("This user does not have permission to view jobs.")
        job_content_type = get_job_content_type()
        results = {
            r.name: r
            for r in JobResult.objects.filter(
                obj_type=job_content_type,
                status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
            )
            .defer("data")
            .order_by("created")
        }

        job_models = Job.objects.restrict(request.user, "view")
        jobs_list = [
            job_model.job_class()  # TODO: why do we need to instantiate the job_class?
            for job_model in job_models
            if job_model.installed and job_model.job_class is not None
        ]
        for job_instance in jobs_list:
            job_instance.result = results.get(job_instance.class_path, None)

        serializer = serializers.JobClassSerializer(jobs_list, many=True, context={"request": request})

        return Response(serializer.data)

    @extend_schema(
        deprecated=True,
        operation_id="extras_jobs_read_deprecated",
        responses={"200": serializers.JobClassDetailSerializer()},
    )
    @action(
        detail=False,  # a /jobs/... URL, not a /jobs/<pk>/... URL
        methods=["get"],
        url_path="(?P<class_path>[^/]+/[^/]+/[^/]+)",  # /api/extras/jobs/<class_path>/
        url_name="detail",
    )
    def retrieve_deprecated(self, request, class_path):
        """
        Get details of a Job as identified by its class-path.

        This API endpoint is deprecated; it is recommended to use the extras_jobs_read endpoint instead.
        """
        if not request.user.has_perm("extras.view_job"):
            raise PermissionDenied("This user does not have permission to view jobs.")
        try:
            job_model = Job.objects.restrict(request.user, "view").get_for_class_path(class_path)
        except Job.DoesNotExist:
            raise Http404
        if not job_model.installed or job_model.job_class is None:
            raise Http404
        job_content_type = get_job_content_type()
        job = job_model.job_class()  # TODO: why do we need to instantiate the job_class?
        job.result = JobResult.objects.filter(
            obj_type=job_content_type,
            name=job.class_path,
            status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
        ).first()

        serializer = serializers.JobClassDetailSerializer(job, context={"request": request})

        return Response(serializer.data)

    @extend_schema(responses={"200": serializers.JobVariableSerializer(many=True)})
    @action(detail=True, filterset_class=None)
    def variables(self, request, pk):
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
    def run(self, request, *args, pk, **kwargs):
        """Run the specified Job."""
        job_model = self.get_object()
        return _run_job(request, job_model)

    @extend_schema(
        deprecated=True,
        methods=["post"],
        request=serializers.JobInputSerializer,
        responses={"200": serializers.JobClassDetailSerializer()},
        operation_id="extras_jobs_run_deprecated",
    )
    @action(
        detail=False,  # a /jobs/... URL, not a /jobs/<pk>/... URL
        methods=["post"],
        permission_classes=[JobRunTokenPermissions],
        url_path="(?P<class_path>[^/]+/[^/]+/[^/]+)/run",  # /api/extras/jobs/<class_path>/run/
        url_name="run",
        parser_classes=[JSONParser, MultiPartParser],
    )
    def run_deprecated(self, request, class_path):
        """
        Run a Job as identified by its class-path.

        This API endpoint is deprecated; it is recommended to use the extras_jobs_run endpoint instead.
        """
        if not request.user.has_perm("extras.run_job"):
            raise PermissionDenied("This user does not have permission to run jobs.")
        try:
            job_model = Job.objects.restrict(request.user, "run").get_for_class_path(class_path)
        except Job.DoesNotExist:
            raise Http404
        return _run_job(request, job_model, legacy_response=True)


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
# Job Results
#


class JobLogEntryViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of job log entries.
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = JobLogEntry.objects.prefetch_related("job_result")
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

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = JobResult.objects.prefetch_related("job_model", "obj_type", "user")
    serializer_class = serializers.JobResultSerializer
    filterset_class = filters.JobResultFilterSet

    @action(detail=True)
    def logs(self, request, pk=None):
        job_result = self.get_object()
        logs = job_result.logs.all()
        serializer = nested_serializers.NestedJobLogEntrySerializer(logs, context={"request": request}, many=True)
        return Response(serializer.data)


#
# Scheduled Jobs
#


class ScheduledJobViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of scheduled jobs
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = ScheduledJob.objects.prefetch_related("user")
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
    @action(detail=True, url_path="dry-run", methods=["post"], permission_classes=[ScheduledJobViewPermissions])
    def dry_run(self, request, pk):
        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)
        job_model = scheduled_job.job_model
        if job_model is None or not job_model.runnable:
            raise MethodNotAllowed("This job cannot be dry-run at this time.")
        if not Job.objects.check_perms(request.user, instance=job_model, action="run"):
            raise PermissionDenied("You do not have permission to run this job.")

        # Immediately enqueue the job with commit=False
        job_content_type = get_job_content_type()
        job_result = JobResult.enqueue_job(
            run_job,
            job_model.class_path,
            job_content_type,
            request.user,
            celery_kwargs=scheduled_job.kwargs.get("celery_kwargs", {}),
            data=scheduled_job.kwargs.get("data", {}),
            request=copy_safe_request(request),
            commit=False,  # force a dry-run
            task_queue=scheduled_job.kwargs.get("task_queue", None),
        )
        serializer = serializers.JobResultSerializer(job_result, context={"request": request})

        return Response(serializer.data)


#
# Notes
#


class NoteViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Note.objects.prefetch_related("user")
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

    metadata_class = ContentTypeMetadata
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = ObjectChange.objects.prefetch_related("user")
    serializer_class = serializers.ObjectChangeSerializer
    filterset_class = filters.ObjectChangeFilterSet


#
#  Relationships
#


class RelationshipViewSet(ModelViewSet, NotesViewSetMixin):
    metadata_class = ContentTypeMetadata
    queryset = Relationship.objects.all()
    serializer_class = serializers.RelationshipSerializer
    filterset_class = filters.RelationshipFilterSet


class RelationshipAssociationViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = RelationshipAssociation.objects.all()
    serializer_class = serializers.RelationshipAssociationSerializer
    filterset_class = filters.RelationshipAssociationFilterSet


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


class StatusViewSetMixin(ModelViewSet):
    """
    Mixin to set `metadata_class` to implement `status` field in model viewset metadata.
    """

    metadata_class = StatusFieldMetadata


#
# Tags
#


@extend_schema_view(
    bulk_update=extend_schema(
        filters=False,
        request=serializers.TagSerializer(many=True),
        responses={"200": serializers.TagSerializer(many=True)},
        versions=["1.2"],
    ),
    bulk_partial_update=extend_schema(
        filters=False,
        request=serializers.TagSerializer(many=True),
        responses={"200": serializers.TagSerializer(many=True)},
        versions=["1.2"],
    ),
    create=extend_schema(
        request=serializers.TagSerializer, responses={"201": serializers.TagSerializer}, versions=["1.2"]
    ),
    partial_update=extend_schema(
        request=serializers.TagSerializer, responses={"200": serializers.TagSerializer}, versions=["1.2"]
    ),
    update=extend_schema(
        request=serializers.TagSerializer, responses={"200": serializers.TagSerializer}, versions=["1.2"]
    ),
    list=extend_schema(responses={"200": serializers.TagSerializer(many=True)}, versions=["1.2"]),
    retrieve=extend_schema(responses={"200": serializers.TagSerializer}, versions=["1.2"]),
)
class TagViewSet(NautobotModelViewSet):
    queryset = Tag.objects.annotate(tagged_items=count_related(TaggedItem, "tag"))
    serializer_class = serializers.TagSerializerVersion13
    filterset_class = filters.TagFilterSet

    def get_serializer_class(self):
        serializer_choices = (SerializerForAPIVersions(versions=["1.2"], serializer=serializers.TagSerializer),)
        return versioned_serializer_selector(
            obj=self,
            serializer_choices=serializer_choices,
            default_serializer=super().get_serializer_class(),
        )


#
# Webhooks
#


class WebhooksViewSet(ModelViewSet, NotesViewSetMixin):
    """
    Manage Webhooks through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = Webhook.objects.all()
    serializer_class = serializers.WebhookSerializer
    filterset_class = filters.WebhookFilterSet
