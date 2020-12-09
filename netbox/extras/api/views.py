from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django_rq.queues import get_connection
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet
from rq import Worker

from extras import filters
from extras.choices import JobResultStatusChoices
from extras.models import (
    ConfigContext, ExportTemplate, ImageAttachment, ObjectChange, JobResult, Tag, TaggedItem,
)
from extras.models import CustomField
from extras.custom_jobs import get_custom_job, get_custom_jobs, run_custom_job
from netbox.api.authentication import IsAuthenticated
from netbox.api.metadata import ContentTypeMetadata
from netbox.api.views import ModelViewSet
from utilities.exceptions import RQWorkerNotRunningException
from utilities.utils import copy_safe_request, count_related
from . import serializers


class ExtrasRootView(APIRootView):
    """
    Extras API root view
    """
    def get_view_name(self):
        return 'Extras'


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
        request = self.get_serializer_context()['request']
        if self.brief or 'config_context' in request.query_params.get('exclude', []):
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


class CustomFieldModelViewSet(ModelViewSet):
    """
    Include the applicable set of CustomFields in the ModelViewSet context.
    """

    def get_serializer_context(self):

        # Gather all custom fields for the model
        content_type = ContentType.objects.get_for_model(self.queryset.model)
        custom_fields = content_type.custom_fields.all()

        context = super().get_serializer_context()
        context.update({
            'custom_fields': custom_fields,
        })
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

class TagViewSet(ModelViewSet):
    queryset = Tag.objects.annotate(
        tagged_items=count_related(TaggedItem, 'tag')
    )
    serializer_class = serializers.TagSerializer
    filterset_class = filters.TagFilterSet


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
        'regions', 'sites', 'roles', 'platforms', 'tenant_groups', 'tenants',
    )
    serializer_class = serializers.ConfigContextSerializer
    filterset_class = filters.ConfigContextFilterSet


#
# Custom jobs
#

class CustomJobViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "full_name"
    lookup_value_regex = '[^/]+'  # Allow dots in the "pk", i.e. "module_name.CustomJobName"

    def _get_custom_job_class(self, full_name):
        if '.' not in full_name:
            raise Http404
        module_name, job_name = full_name.split('.', 1)

        custom_job = get_custom_job(module_name, job_name)
        if custom_job is None:
            raise Http404

        return custom_job

    def list(self, request):
        if not request.user.has_perm('extras.view_customjob'):
            raise PermissionDenied("This user does not have permission to view custom jobs.")
        custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
        results = {
            r.name: r
            for r in JobResult.objects.filter(
                obj_type=custom_job_content_type,
                status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
            ).defer('data').order_by('created')
        }

        custom_jobs = get_custom_jobs()
        jobs_list = []
        for module_name, entry in custom_jobs.items():
            for custom_job_class in entry['jobs'].values():
                custom_job = custom_job_class()
                custom_job.result = results.get(custom_job.full_name, None)
                jobs_list.append(custom_job)

        serializer = serializers.CustomJobSerializer(jobs_list, many=True, context={'request': request})

        return Response(serializer.data)

    def retrieve(self, request, full_name):
        if not request.user.has_perm('extras.view_customjob'):
            raise PermissionDenied("This user does not have permission to view custom jobs.")
        custom_job_class = self._get_custom_job_class(full_name)
        custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
        custom_job = custom_job_class()
        custom_job.result = JobResult.objects.filter(
            obj_type=custom_job_content_type,
            name=custom_job.full_name,
            status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
        ).first()

        serializer = serializers.CustomJobDetailSerializer(custom_job, context={'request': request})

        return Response(serializer.data)

    @swagger_auto_schema(method='post', request_body=serializers.CustomJobInputSerializer)
    @action(detail=True, methods=['post'])
    def run(self, request, full_name):
        if not request.user.has_perm('extras.run_customjob'):
            raise PermissionDenied("This user does not have permission to run custom jobs.")

        # Check that at least one RQ worker is running
        if not Worker.count(get_connection('default')):
            raise RQWorkerNotRunningException()

        custom_job_class = self._get_custom_job_class(full_name)
        custom_job = custom_job_class()
        input_serializer = serializers.CustomJobInputSerializer(data=request.data)

        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = input_serializer.data['data']
        commit = input_serializer.data['commit']
        if commit is None:
            commit = getattr(custom_job_class.Meta, "commit_default", True)

        custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')

        job_result = JobResult.enqueue_job(
            run_custom_job,
            custom_job.full_name,
            custom_job_content_type,
            request.user,
            data=data,
            request=copy_safe_request(request),
            commit=commit,
        )
        custom_job.result = job_result

        serializer = serializers.CustomJobDetailSerializer(custom_job, context={'request': request})

        return Response(serializer.data)


#
# Change logging
#

class ObjectChangeViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of recent changes.
    """
    metadata_class = ContentTypeMetadata
    queryset = ObjectChange.objects.prefetch_related('user')
    serializer_class = serializers.ObjectChangeSerializer
    filterset_class = filters.ObjectChangeFilterSet


#
# Job Results
#

class JobResultViewSet(ReadOnlyModelViewSet):
    """
    Retrieve a list of job results
    """
    queryset = JobResult.objects.prefetch_related('user')
    serializer_class = serializers.JobResultSerializer
    filterset_class = filters.JobResultFilterSet


#
# ContentTypes
#

class ContentTypeViewSet(ReadOnlyModelViewSet):
    """
    Read-only list of ContentTypes. Limit results to ContentTypes pertinent to NetBox objects.
    """
    queryset = ContentType.objects.order_by('app_label', 'model')
    serializer_class = serializers.ContentTypeSerializer
    filterset_class = filters.ContentTypeFilterSet
