from django import template
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django_rq.queues import get_connection
from django_tables2 import RequestConfig
from rq import Worker

from netbox.views import generic
from utilities.forms import ConfirmationForm
from utilities.paginator import EnhancedPaginator, get_paginate_count
from utilities.utils import copy_safe_request, count_related, shallow_compare_dict
from utilities.views import ContentTypePermissionRequiredMixin
from . import filters, forms, tables
from .choices import JobResultStatusChoices
from .models import ConfigContext, ImageAttachment, ObjectChange, JobResult, Tag, TaggedItem
from .custom_jobs import get_custom_job, get_custom_jobs, run_custom_job


#
# Tags
#

class TagListView(generic.ObjectListView):
    queryset = Tag.objects.annotate(
        items=count_related(TaggedItem, 'tag')
    )
    filterset = filters.TagFilterSet
    filterset_form = forms.TagFilterForm
    table = tables.TagTable


class TagEditView(generic.ObjectEditView):
    queryset = Tag.objects.all()
    model_form = forms.TagForm
    template_name = 'extras/tag_edit.html'


class TagDeleteView(generic.ObjectDeleteView):
    queryset = Tag.objects.all()


class TagBulkImportView(generic.BulkImportView):
    queryset = Tag.objects.all()
    model_form = forms.TagCSVForm
    table = tables.TagTable


class TagBulkEditView(generic.BulkEditView):
    queryset = Tag.objects.annotate(
        items=count_related(TaggedItem, 'tag')
    )
    table = tables.TagTable
    form = forms.TagBulkEditForm


class TagBulkDeleteView(generic.BulkDeleteView):
    queryset = Tag.objects.annotate(
        items=count_related(TaggedItem, 'tag')
    )
    table = tables.TagTable


#
# Config contexts
#

class ConfigContextListView(generic.ObjectListView):
    queryset = ConfigContext.objects.all()
    filterset = filters.ConfigContextFilterSet
    filterset_form = forms.ConfigContextFilterForm
    table = tables.ConfigContextTable
    action_buttons = ('add',)


class ConfigContextView(generic.ObjectView):
    queryset = ConfigContext.objects.all()

    def get_extra_context(self, request, instance):
        # Determine user's preferred output format
        if request.GET.get('format') in ['json', 'yaml']:
            format = request.GET.get('format')
            if request.user.is_authenticated:
                request.user.config.set('extras.configcontext.format', format, commit=True)
        elif request.user.is_authenticated:
            format = request.user.config.get('extras.configcontext.format', 'json')
        else:
            format = 'json'

        return {
            'format': format,
        }


class ConfigContextEditView(generic.ObjectEditView):
    queryset = ConfigContext.objects.all()
    model_form = forms.ConfigContextForm
    template_name = 'extras/configcontext_edit.html'


class ConfigContextBulkEditView(generic.BulkEditView):
    queryset = ConfigContext.objects.all()
    filterset = filters.ConfigContextFilterSet
    table = tables.ConfigContextTable
    form = forms.ConfigContextBulkEditForm


class ConfigContextDeleteView(generic.ObjectDeleteView):
    queryset = ConfigContext.objects.all()


class ConfigContextBulkDeleteView(generic.BulkDeleteView):
    queryset = ConfigContext.objects.all()
    table = tables.ConfigContextTable


class ObjectConfigContextView(generic.ObjectView):
    base_template = None
    template_name = 'extras/object_configcontext.html'

    def get_extra_context(self, request, instance):
        source_contexts = ConfigContext.objects.restrict(request.user, 'view').get_for_object(instance)

        # Determine user's preferred output format
        if request.GET.get('format') in ['json', 'yaml']:
            format = request.GET.get('format')
            if request.user.is_authenticated:
                request.user.config.set('extras.configcontext.format', format, commit=True)
        elif request.user.is_authenticated:
            format = request.user.config.get('extras.configcontext.format', 'json')
        else:
            format = 'json'

        return {
            'rendered_context': instance.get_config_context(),
            'source_contexts': source_contexts,
            'format': format,
            'base_template': self.base_template,
            'active_tab': 'config-context',
        }


#
# Change logging
#

class ObjectChangeListView(generic.ObjectListView):
    queryset = ObjectChange.objects.all()
    filterset = filters.ObjectChangeFilterSet
    filterset_form = forms.ObjectChangeFilterForm
    table = tables.ObjectChangeTable
    template_name = 'extras/objectchange_list.html'
    action_buttons = ('export',)


class ObjectChangeView(generic.ObjectView):
    queryset = ObjectChange.objects.all()

    def get_extra_context(self, request, instance):
        related_changes = ObjectChange.objects.restrict(request.user, 'view').filter(
            request_id=instance.request_id
        ).exclude(
            pk=instance.pk
        )
        related_changes_table = tables.ObjectChangeTable(
            data=related_changes[:50],
            orderable=False
        )

        objectchanges = ObjectChange.objects.restrict(request.user, 'view').filter(
            changed_object_type=instance.changed_object_type,
            changed_object_id=instance.changed_object_id,
        )

        next_change = objectchanges.filter(time__gt=instance.time).order_by('time').first()
        prev_change = objectchanges.filter(time__lt=instance.time).order_by('-time').first()

        if prev_change:
            diff_added = shallow_compare_dict(
                prev_change.object_data,
                instance.object_data,
                exclude=['last_updated'],
            )
            diff_removed = {x: prev_change.object_data.get(x) for x in diff_added}
        else:
            # No previous change; this is the initial change that added the object
            diff_added = diff_removed = instance.object_data

        return {
            'diff_added': diff_added,
            'diff_removed': diff_removed,
            'next_change': next_change,
            'prev_change': prev_change,
            'related_changes_table': related_changes_table,
            'related_changes_count': related_changes.count()
        }


class ObjectChangeLogView(View):
    """
    Present a history of changes made to a particular object.

    base_template: The name of the template to extend. If not provided, "<app>/<model>.html" will be used.
    """
    base_template = None

    def get(self, request, model, **kwargs):

        # Handle QuerySet restriction of parent object if needed
        if hasattr(model.objects, 'restrict'):
            obj = get_object_or_404(model.objects.restrict(request.user, 'view'), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        # Gather all changes for this object (and its related objects)
        content_type = ContentType.objects.get_for_model(model)
        objectchanges = ObjectChange.objects.restrict(request.user, 'view').prefetch_related(
            'user', 'changed_object_type'
        ).filter(
            Q(changed_object_type=content_type, changed_object_id=obj.pk) |
            Q(related_object_type=content_type, related_object_id=obj.pk)
        )
        objectchanges_table = tables.ObjectChangeTable(
            data=objectchanges,
            orderable=False
        )

        # Apply the request context
        paginate = {
            'paginator_class': EnhancedPaginator,
            'per_page': get_paginate_count(request)
        }
        RequestConfig(request, paginate).configure(objectchanges_table)

        # Default to using "<app>/<model>.html" as the template, if it exists. Otherwise,
        # fall back to using base.html.
        if self.base_template is None:
            self.base_template = f"{model._meta.app_label}/{model._meta.model_name}.html"
            # TODO: This can be removed once an object view has been established for every model.
            try:
                template.loader.get_template(self.base_template)
            except template.TemplateDoesNotExist:
                self.base_template = 'base.html'

        return render(request, 'extras/object_changelog.html', {
            'object': obj,
            'table': objectchanges_table,
            'base_template': self.base_template,
            'active_tab': 'changelog',
        })


#
# Image attachments
#

class ImageAttachmentEditView(generic.ObjectEditView):
    queryset = ImageAttachment.objects.all()
    model_form = forms.ImageAttachmentForm

    def alter_obj(self, imageattachment, request, args, kwargs):
        if not imageattachment.pk:
            # Assign the parent object based on URL kwargs
            model = kwargs.get('model')
            imageattachment.parent = get_object_or_404(model, pk=kwargs['object_id'])
        return imageattachment

    def get_return_url(self, request, imageattachment):
        return imageattachment.parent.get_absolute_url()


class ImageAttachmentDeleteView(generic.ObjectDeleteView):
    queryset = ImageAttachment.objects.all()

    def get_return_url(self, request, imageattachment):
        return imageattachment.parent.get_absolute_url()


#
# Custom jobs
#

class CustomJobListView(ContentTypePermissionRequiredMixin, View):
    """
    Retrieve all of the available custom jobs from disk and the recorded JobResult (if any) for each.
    """
    def get_required_permission(self):
        return 'extras.view_customjob'

    def get(self, request):
        custom_jobs = get_custom_jobs()
        custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
        # Get the newest results for each job name
        results = {
            r.name: r
            for r in JobResult.objects.filter(
                obj_type=custom_job_content_type,
                status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES
            ).order_by('completed').defer('data')
        }

        ret = []
        for module, entry in custom_jobs.items():
            module_custom_jobs = []
            for custom_job_class in entry['jobs'].values():
                custom_job = custom_job_class()
                custom_job.result = results.get(custom_job.full_name, None)
                module_custom_jobs.append(custom_job)
            ret.append((entry["name"], module_custom_jobs))

        return render(request, 'extras/customjob_list.html', {
            'custom_jobs': ret,
        })


class CustomJobView(ContentTypePermissionRequiredMixin, View):
    """
    View the parameters of a Custom Job and enqueue it if desired.
    """

    def get_required_permission(self):
        return 'extras.view_customjob'

    def get(self, request, module, name):
        custom_job_class = get_custom_job(module, name)
        if custom_job_class is None:
            raise Http404
        custom_job = custom_job_class()

        form = custom_job.as_form(initial=request.GET)

        return render(request, 'extras/customjob.html', {
            'module': module,
            'custom_job': custom_job,
            'form': form,
            # 'run_form': ConfirmationForm(),
        })

    def post(self, request, module, name):
        if not request.user.has_perm('extras.run_customjob'):
            return HttpResponseForbidden()

        custom_job_class = get_custom_job(module, name)
        if custom_job_class is None:
            raise Http404
        custom_job = custom_job_class()
        form = custom_job.as_form(request.POST, request.FILES)

        # Allow execution only if RQ worker process is running
        if not Worker.count(get_connection('default')):
            messages.error(request, "Unable to run custom job: RQ worker process not running.")

        elif form.is_valid():
            # Run the job. A new JobResult is created.
            commit = form.cleaned_data.pop('_commit')

            custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
            job_result = JobResult.enqueue_job(
                run_custom_job,
                custom_job.full_name,
                custom_job_content_type,
                request.user,
                data=form.cleaned_data,
                request=copy_safe_request(request),
                commit=commit,
            )

            return redirect('extras:customjob_result', job_result_pk=job_result.pk)

        return render(request, 'extras/customjob.html', {
            'module': module,
            'custom_job': custom_job,
            'form': form,
        })


class CustomJobResultListView(generic.ObjectListView):
    """
    List JobResults pertaining to the execution of Custom Jobs.
    """
    additional_permissions = ["extras.view_customjob"]

    queryset = None
    filterset = filters.JobResultFilterSet
    filterset_form = forms.JobResultFilterForm
    table = tables.JobResultTable
    action_buttons = ()
    template_name = 'extras/customjob_result_list.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
        self.queryset = JobResult.objects.filter(obj_type=custom_job_content_type).order_by('-created')


class JobResultDeleteView(generic.ObjectDeleteView):
    queryset = JobResult.objects.all()


class JobResultBulkDeleteView(generic.BulkDeleteView):
    queryset = JobResult.objects.all()
    table = tables.JobResultTable


class CustomJobResultView(ContentTypePermissionRequiredMixin, View):
    """
    Display a JobResult pertaining to the execution of a Custom Job.
    """
    def get_required_permission(self):
        return 'extras.view_customjob'

    def get(self, request, job_result_pk):
        custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
        job_result = get_object_or_404(JobResult.objects.all(), pk=job_result_pk, obj_type=custom_job_content_type)

        module, job_name = job_result.name.split('.', 1)
        custom_job_class = get_custom_job(module, job_name)
        if custom_job_class is not None:
            custom_job = custom_job_class()
        else:
            custom_job = None

        return render(request, 'extras/customjob_result.html', {
            'module': module,
            'class_name': job_name,
            'custom_job': custom_job,
            'result': job_result,
        })
