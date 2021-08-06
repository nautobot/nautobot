from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_rq.queues import get_connection
from drf_yasg.utils import swagger_auto_schema
from graphene_django.views import GraphQLView
from graphql import GraphQLError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet
from rq import Worker

from nautobot.core.api.metadata import ContentTypeMetadata, StatusFieldMetadata
from nautobot.core.api.views import ModelViewSet
from nautobot.core.graphql import execute_saved_query
from nautobot.extras import filters
from nautobot.extras.choices import JobResultStatusChoices
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
    Status,
    Tag,
    TaggedItem,
    Webhook,
)
from nautobot.extras.models import CustomField, CustomFieldChoice
from nautobot.extras.jobs import get_job, get_jobs, run_job
from nautobot.utilities.exceptions import RQWorkerNotRunningException
from nautobot.utilities.utils import copy_safe_request, count_related
from . import serializers


class ExtrasRootView(APIRootView):
    """
    Extras API root view
    """

    def get_view_name(self):
        return "Extras"


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
# Export templates
#


class ExportTemplateViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = ExportTemplate.objects.all()
    serializer_class = serializers.ExportTemplateSerializer
    filterset_class = filters.ExportTemplateFilterSet


#
# Tags
#


class TagViewSet(CustomFieldModelViewSet):
    queryset = Tag.objects.annotate(tagged_items=count_related(TaggedItem, "tag"))
    serializer_class = serializers.TagSerializer
    filterset_class = filters.TagFilterSet


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

        if not Worker.count(get_connection("default")):
            raise RQWorkerNotRunningException()

        repository = get_object_or_404(GitRepository, id=pk)
        enqueue_pull_git_repository_and_refresh_data(repository, request)
        return Response({"message": f"Repository {repository} sync job added to queue."})


#
# Image attachments
#


class ImageAttachmentViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = ImageAttachment.objects.all()
    serializer_class = serializers.ImageAttachmentSerializer
    filterset_class = filters.ImageAttachmentFilterSet


#
# Config contexts
#


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
# Jobs
#


class JobViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "class_path"
    lookup_value_regex = "[^/]+/[^/]+/[^/]+"  # e.g. "git.repo_name/module_name/JobName"

    def _get_job_class(self, class_path):
        job_class = get_job(class_path)
        if job_class is None:
            raise Http404

        return job_class

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

        data = input_serializer.data["data"]
        commit = input_serializer.data["commit"]
        if commit is None:
            commit = getattr(job_class.Meta, "commit_default", True)

        job_content_type = ContentType.objects.get(app_label="extras", model="job")

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
# ContentTypes
#


class ContentTypeViewSet(ReadOnlyModelViewSet):
    """
    Read-only list of ContentTypes. Limit results to ContentTypes pertinent to Nautobot objects.
    """

    queryset = ContentType.objects.order_by("app_label", "model")
    serializer_class = serializers.ContentTypeSerializer
    filterset_class = filters.ContentTypeFilterSet


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
# Webhooks
#


class WebhooksViewSet(ModelViewSet):
    """
    Manage Webhooks through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = Webhook.objects.all()
    serializer_class = serializers.WebhookSerializer
    filterset_class = filters.WebhookFilterSet


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
#  Computed Fields
#


class ComputedFieldViewSet(ModelViewSet):
    """
    Manage Computed Fields through DELETE, GET, POST, PUT, and PATCH requests.
    """

    queryset = ComputedField.objects.all()
    serializer_class = serializers.ComputedFieldSerializer
    filterset_class = filters.ComputedFieldFilterSet
