from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError as FormsValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import no_body, swagger_auto_schema
from graphene_django.views import GraphQLView
from graphql import GraphQLError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework import viewsets

from nautobot.core.api.metadata import ContentTypeMetadata, StatusFieldMetadata
from nautobot.core.api.views import ModelViewSet, ReadOnlyModelViewSet
from nautobot.core.graphql import execute_saved_query
from nautobot.extras import filters
from nautobot.extras.choices import JobExecutionType, JobResultStatusChoices
from nautobot.extras.datasources import enqueue_pull_git_repository_and_refresh_data
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretType,
    Status,
    Tag,
    TaggedItem,
    Webhook,
)
from nautobot.extras.models import CustomField, CustomFieldChoice
from nautobot.extras.jobs import get_job, get_jobs, run_job
from nautobot.extras.utils import get_worker_count
from nautobot.utilities.exceptions import CeleryWorkerNotRunningException
from nautobot.utilities.utils import copy_safe_request, count_related
from . import serializers


class ExtrasRootView(APIRootView):
    """
    Extras API root view
    """

    def get_view_name(self):
        return "Extras"


#
#  Computed Fields
#


class ComputedFieldViewSet(ModelViewSet):
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

        If the `brief` query param equates to True or the `exclude` query param
        includes `config_context` as a value, return the base queryset.

        Else, return the queryset annotated with config context data
        """
        queryset = super().get_queryset()
        request = self.get_serializer_context()["request"]
        if self.brief or "config_context" in request.query_params.get("exclude", []):
            return queryset
        return queryset.annotate_config_context_data()


class ConfigContextViewSet(ModelViewSet):
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


class ConfigContextSchemaViewSet(ModelViewSet):
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


class CustomFieldViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
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


#
# Custom Links
#


class CustomLinkViewSet(ModelViewSet):
    """
    Manage Custom Links through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = CustomLink.objects.all()
    serializer_class = serializers.CustomLinkSerializer
    filterset_class = filters.CustomLinkFilterSet


#
# Export templates
#


class ExportTemplateViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = ExportTemplate.objects.all()
    serializer_class = serializers.ExportTemplateSerializer
    filterset_class = filters.ExportTemplateFilterSet


#
# Git repositories
#


class GitRepositoryViewSet(CustomFieldModelViewSet):
    """
    Manage the use of Git repositories as external data sources.
    """

    queryset = GitRepository.objects.all()
    serializer_class = serializers.GitRepositorySerializer
    filterset_class = filters.GitRepositoryFilterSet

    @swagger_auto_schema(method="post", request_body=serializers.GitRepositorySerializer)
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


class GraphQLQueryViewSet(ModelViewSet):
    queryset = GraphQLQuery.objects.all()
    serializer_class = serializers.GraphQLQuerySerializer
    filterset_class = filters.GraphQLQueryFilterSet

    @swagger_auto_schema(
        method="post",
        request_body=serializers.GraphQLQueryInputSerializer,
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


class JobViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "class_path"
    lookup_value_regex = "[^/]+/[^/]+/[^/]+"  # e.g. "git.repo_name/module_name/JobName"

    def _get_job_class(self, class_path):
        job_class = get_job(class_path)
        if job_class is None:
            raise Http404

        return job_class

    def _create_schedule(self, serializer, data, commit, job, job_class, request):
        """
        This is an internal function to create a scheduled job from API data.
        It has to handle boths once-offs (i.e. of type TYPE_FUTURE) and interval
        jobs.
        """
        job_kwargs = {
            "data": data,
            "request": copy_safe_request(request),
            "user": request.user.pk,
            "commit": commit,
            "name": job.class_path,
        }
        type_ = serializer["interval"]
        if type_ == JobExecutionType.TYPE_IMMEDIATELY:
            time = datetime.now()
            name = serializer.get("name") or f"{job.name} - {time}"
        else:
            time = serializer["start_time"]
            name = serializer["name"]
        scheduled_job = ScheduledJob(
            name=name,
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=job.class_path,
            start_time=time,
            description=f"Nautobot job {name} scheduled by {request.user} on {time}",
            kwargs=job_kwargs,
            interval=type_,
            one_off=(type_ == JobExecutionType.TYPE_FUTURE),
            user=request.user,
            approval_required=job_class.approval_required,
        )
        scheduled_job.save()
        return scheduled_job

    def list(self, request):
        if not request.user.has_perm("extras.view_job"):
            raise PermissionDenied("This user does not have permission to view jobs.")
        job_content_type = ContentType.objects.get(app_label="extras", model="job")
        results = {
            r.name: r
            for r in JobResult.objects.filter(
                obj_type=job_content_type,
                status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
            )
            .defer("data")
            .order_by("created")
        }

        jobs = get_jobs()
        jobs_list = []
        for grouping, modules in jobs.items():
            for module_name, entry in modules.items():
                for job_class in entry["jobs"].values():
                    job = job_class()
                    job.result = results.get(job.class_path, None)
                    jobs_list.append(job)

        serializer = serializers.JobSerializer(jobs_list, many=True, context={"request": request})

        return Response(serializer.data)

    def retrieve(self, request, class_path):
        if not request.user.has_perm("extras.view_job"):
            raise PermissionDenied("This user does not have permission to view jobs.")
        job_class = self._get_job_class(class_path)
        job_content_type = ContentType.objects.get(app_label="extras", model="job")
        job = job_class()
        job.result = JobResult.objects.filter(
            obj_type=job_content_type,
            name=job.class_path,
            status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
        ).first()

        serializer = serializers.JobDetailSerializer(job, context={"request": request})

        return Response(serializer.data)

    @swagger_auto_schema(method="post", request_body=serializers.JobInputSerializer)
    @action(detail=True, methods=["post"])
    def run(self, request, class_path):
        if not request.user.has_perm("extras.run_job"):
            raise PermissionDenied("This user does not have permission to run jobs.")

        job_class = self._get_job_class(class_path)
        job = job_class()

        input_serializer = serializers.JobInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        data = input_serializer.data["data"] or {}
        commit = input_serializer.data["commit"]
        if commit is None:
            commit = getattr(job_class.Meta, "commit_default", True)

        try:
            job.validate_data(data)
        except FormsValidationError as e:
            # message_dict can only be accessed if ValidationError got a dict
            # in the constructor (saved as error_dict). Otherwise we get a list
            # of errors under messages
            return Response({"errors": e.message_dict if hasattr(e, "error_dict") else e.messages}, status=400)

        if not get_worker_count():
            raise CeleryWorkerNotRunningException()

        job_content_type = ContentType.objects.get(app_label="extras", model="job")

        schedule = input_serializer.data.get("schedule")
        if schedule:
            schedule = self._create_schedule(schedule, data, commit, job, job_class, request)
        else:
            job_result = JobResult.enqueue_job(
                run_job,
                job.class_path,
                job_content_type,
                request.user,
                data=data,
                request=copy_safe_request(request),
                commit=commit,
            )
            job.result = job_result

        serializer = serializers.JobDetailSerializer(job, context={"request": request})

        return Response(serializer.data)


#
# Job Results
#


class JobResultViewSet(ModelViewSet):
    """
    Retrieve a list of job results
    """

    queryset = JobResult.objects.prefetch_related("user")
    serializer_class = serializers.JobResultSerializer
    filterset_class = filters.JobResultFilterSet


#
# Scheduled Jobs
#


class ScheduledJobViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of scheduled jobs
    """

    queryset = ScheduledJob.objects.prefetch_related("user")
    serializer_class = serializers.ScheduledJobSerializer
    filterset_class = filters.ScheduledJobFilterSet

    @swagger_auto_schema(
        method="post",
        responses={"200": serializers.ScheduledJobSerializer},
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                "force",
                openapi.IN_QUERY,
                description="force execution even if start time has passed",
                type=openapi.TYPE_BOOLEAN,
            )
        ],
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk):
        if not request.user.has_perm("extras.run_job"):
            raise PermissionDenied()

        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)

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

    @swagger_auto_schema(
        method="post",
        request_body=no_body,
    )
    @action(detail=True, methods=["post"])
    def deny(self, request, pk):
        if not request.user.has_perm("extras.run_job"):
            raise PermissionDenied()

        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)

        scheduled_job.delete()

        return Response(None)

    @swagger_auto_schema(
        method="post",
        responses={"200": serializers.JobResultSerializer},
        request_body=no_body,
    )
    @action(detail=True, url_path="dry-run", methods=["post"])
    def dry_run(self, request, pk):
        if not request.user.has_perm("extras.run_job"):
            raise PermissionDenied()

        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)
        job_class = get_job(scheduled_job.job_class)
        if job_class is None:
            raise Http404
        job = job_class()
        grouping, module, class_name = job_class.class_path.split("/", 2)

        # Immediately enqueue the job with commit=False
        job_content_type = ContentType.objects.get(app_label="extras", model="job")
        job_result = JobResult.enqueue_job(
            run_job,
            job.class_path,
            job_content_type,
            scheduled_job.user,
            data=scheduled_job.kwargs["data"],
            request=copy_safe_request(request),
            commit=False,  # force a dry-run
        )
        serializer = serializers.JobResultSerializer(job_result, context={"request": request})

        return Response(serializer.data)


#
# Change logging
#


class ObjectChangeViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of recent changes.
    """

    metadata_class = ContentTypeMetadata
    queryset = ObjectChange.objects.prefetch_related("user")
    serializer_class = serializers.ObjectChangeSerializer
    filterset_class = filters.ObjectChangeFilterSet


#
#  Relationships
#


class RelationshipViewSet(ModelViewSet):
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


class SecretsViewSet(ModelViewSet):
    """
    Manage Secrets through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = Secret.objects.all()
    serializer_class = serializers.SecretSerializer
    filterset_class = filters.SecretFilterSet


class SecretsGroupViewSet(ModelViewSet):
    """
    Manage Secrets Groups through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = SecretsGroup.objects.all()
    serializer_class = serializers.SecretsGroupSerializer
    filterset_class = filters.SecretsGroupFilterSet


class SecretTypeViewSet(ModelViewSet):
    """
    Manage Secret Types through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = SecretType.objects.all()
    serializer_class = serializers.SecretTypeSerializer
    filterset_class = filters.SecretTypeFilterSet


#
# Statuses
#


class StatusViewSet(CustomFieldModelViewSet):
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


class TagViewSet(CustomFieldModelViewSet):
    queryset = Tag.objects.annotate(tagged_items=count_related(TaggedItem, "tag"))
    serializer_class = serializers.TagSerializer
    filterset_class = filters.TagFilterSet


#
# Webhooks
#


class WebhooksViewSet(ModelViewSet):
    """
    Manage Webhooks through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = Webhook.objects.all()
    serializer_class = serializers.WebhookSerializer
    filterset_class = filters.WebhookFilterSet
