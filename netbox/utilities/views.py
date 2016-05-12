from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateSyntaxError
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.views.generic import View

from django_tables2 import RequestConfig

from .error_handlers import handle_protectederror
from .forms import ConfirmationForm
from .paginator import EnhancedPaginator
from extras.models import ExportTemplate


class ObjectListView(View):
    queryset = None
    filter = None
    filter_form = None
    table = None
    edit_table = None
    edit_table_permissions = []
    template_name = None
    redirect_on_single_result = True

    def get(self, request, *args, **kwargs):

        object_ct = ContentType.objects.get_for_model(self.queryset.model)

        if self.filter:
            self.queryset = self.filter(request.GET, self.queryset).qs

        # Check for export template rendering
        if request.GET.get('export'):
            et = get_object_or_404(ExportTemplate, content_type=object_ct, name=request.GET.get('export'))
            try:
                response = et.to_response(context_dict={'queryset': self.queryset},
                                          filename='netbox_{}'.format(self.queryset.model._meta.verbose_name_plural))
                return response
            except TemplateSyntaxError:
                messages.error(request, "There was an error rendering the selected export template ({}).".format(et.name))

        # Attempt to redirect automatically if the query returns a single result
        if self.redirect_on_single_result and self.queryset.count() == 1:
            try:
                return HttpResponseRedirect(self.queryset[0].get_absolute_url())
            except AttributeError:
                pass

        # Provide a hook to tweak the queryset based on the request immediately prior to rendering the object list
        self.queryset = self.alter_queryset(request)

        # Construct the table based on the user's permissions
        if any([request.user.has_perm(perm) for perm in self.edit_table_permissions]):
            table = self.edit_table(self.queryset)
        else:
            table = self.table(self.queryset)
        RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator})\
            .configure(table)

        export_templates = ExportTemplate.objects.filter(content_type=object_ct)

        return render(request, self.template_name, {
            'table': table,
            'filter_form': self.filter_form(request.GET, label_suffix='') if self.filter_form else None,
            'export_templates': export_templates,
        })

    def alter_queryset(self, request):
        return self.queryset


class ObjectAddView(View):
    model = None
    form_class = None
    template_name = None
    cancel_url = None
    fields_initial = []

    def get(self, request):

        initial = {k: request.GET.get(k) for k in self.fields_initial}
        form = self.form_class(initial=initial)

        return render(request, self.template_name, {
            'form': form,
            'obj_type': self.model._meta.verbose_name,
            'cancel_url': reverse(self.cancel_url),
        })

    def post(self, request):

        form = self.form_class(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Added new {} <a href="{}">{}</a>'.format(self.model._meta.verbose_name,
                                                                                obj.get_absolute_url(), obj))
            if '_addanother' in request.POST:
                return redirect(request.path)
            else:
                return redirect(obj.get_absolute_url())

        return render(request, self.template_name, {
            'form': form,
            'obj_type': self.model._meta.verbose_name,
            'cancel_url': reverse(self.cancel_url),
        })


class ObjectEditView(View):
    model = None
    form_class = None
    template_name = None
    return_url = None

    def get_object(self, kwargs):
        # Look up object by slug if one has been provided. Otherwise, use PK.
        if 'slug' in kwargs:
            return get_object_or_404(self.model, slug=kwargs['slug'])
        else:
            return get_object_or_404(self.model, pk=kwargs['pk'])

    def get(self, request, *args, **kwargs):

        obj = self.get_object(kwargs)
        form = self.form_class(instance=obj)

        return render(request, self.template_name, {
            'obj': obj,
            'form': form,
            'obj_type': self.model._meta.verbose_name,
            'cancel_url': reverse(self.return_url) if self.return_url else obj.get_absolute_url(),
        })

    def post(self, request, *args, **kwargs):

        obj = self.get_object(kwargs)
        form = self.form_class(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Modified {} <a href="{}">{}</a>'.format(self.model._meta.verbose_name,
                                                                               obj.get_absolute_url(), obj))
            if '_addanother' in request.POST:
                return redirect(request.path)
            else:
                return redirect(obj.get_absolute_url())

        return render(request, self.template_name, {
            'obj': obj,
            'form': form,
            'obj_type': self.model._meta.verbose_name,
            'cancel_url': reverse(self.return_url) if self.return_url else obj.get_absolute_url(),
        })


class ObjectDeleteView(View):
    model = None
    template_name = None
    redirect_url = None

    def get_object(self, kwargs):
        # Look up object by slug if one has been provided. Otherwise, use PK.
        if 'slug' in kwargs:
            return get_object_or_404(self.model, slug=kwargs['slug'])
        else:
            return get_object_or_404(self.model, pk=kwargs['pk'])

    def get(self, request, *args, **kwargs):

        obj = self.get_object(kwargs)
        form = ConfirmationForm()

        return render(request, self.template_name, {
            'obj': obj,
            'form': form,
            'cancel_url': obj.get_absolute_url(),
        })

    def post(self, request, *args, **kwargs):

        obj = self.get_object(kwargs)
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                obj.delete()
                messages.success(request, 'Deleted {} {}'.format(self.model._meta.verbose_name, obj))
                return redirect(self.redirect_url)
            except ProtectedError, e:
                handle_protectederror(obj, request, e)
                return redirect(obj.get_absolute_url())

        return render(request, self.template_name, {
            'obj': obj,
            'form': form,
            'cancel_url': obj.get_absolute_url(),
        })


class BulkImportView(View):
    form = None
    table = None
    template_name = None
    obj_list_url = None

    def get(self, request, *args, **kwargs):

        return render(request, self.template_name, {
            'form': self.form(),
            'obj_list_url': self.obj_list_url,
        })

    def post(self, request, *args, **kwargs):

        form = self.form(request.POST)
        if form.is_valid():
            new_objs = []
            try:
                with transaction.atomic():
                    for obj in form.cleaned_data['csv']:
                        self.save_obj(obj)
                        new_objs.append(obj)

                obj_table = self.table(new_objs)
                messages.success(request, "Imported {} objects".format(len(new_objs)))

                return render(request, "import_success.html", {
                    'table': obj_table,
                })

            except IntegrityError as e:
                form.add_error('csv', "Record {}: {}".format(len(new_objs) + 1, e.__cause__))

        return render(request, self.template_name, {
            'form': form,
            'obj_list_url': self.obj_list_url,
        })

    def save_obj(self, obj):
        obj.save()


class BulkEditView(View):
    cls = None
    form = None
    template_name = None
    default_redirect_url = None

    def get(self, request, *args, **kwargs):
        return redirect(self.default_redirect_url)

    def post(self, request, *args, **kwargs):

        posted_redirect_url = request.POST.get('redirect_url')
        if posted_redirect_url and is_safe_url(url=posted_redirect_url, host=request.get_host()):
            redirect_url = posted_redirect_url
        else:
            redirect_url = reverse(self.default_redirect_url)

        if '_apply' in request.POST:
            form = self.form(request.POST)
            if form.is_valid():
                pk_list = [obj.pk for obj in form.cleaned_data['pk']]
                self.update_objects(pk_list, form)
                if not form.errors:
                    return redirect(redirect_url)

        else:
            form = self.form(initial={'pk': request.POST.getlist('pk')})

        selected_objects = self.cls.objects.filter(pk__in=request.POST.getlist('pk'))
        if not selected_objects:
            messages.warning(request, "No {} were selected.".format(self.cls._meta.verbose_name_plural))
            return redirect(redirect_url)

        return render(request, self.template_name, {
            'form': form,
            'selected_objects': selected_objects,
            'cancel_url': redirect_url,
        })

    def update_objects(self, obj_list, form):
        """
        This method provides the update logic (must be overridden by subclasses).
        """
        raise NotImplementedError()


class BulkDeleteView(View):
    cls = None
    form = None
    template_name = 'utilities/confirm_bulk_delete.html'
    default_redirect_url = None

    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super(BulkDeleteView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect(self.default_redirect_url)

    def post(self, request, *args, **kwargs):

        posted_redirect_url = request.POST.get('redirect_url')
        if posted_redirect_url and is_safe_url(url=posted_redirect_url, host=request.get_host()):
            redirect_url = posted_redirect_url
        else:
            redirect_url = reverse(self.default_redirect_url)

        if '_confirm' in request.POST:
            form = self.form(request.POST)
            if form.is_valid():

                # Delete objects
                objects_to_delete = self.cls.objects.filter(pk__in=[v.id for v in form.cleaned_data['pk']])
                try:
                    deleted_count = objects_to_delete.count()
                    objects_to_delete.delete()
                except ProtectedError, e:
                    handle_protectederror(list(objects_to_delete), request, e)
                    return redirect(redirect_url)

                messages.success(request, "Deleted {} {}".format(deleted_count, self.cls._meta.verbose_name_plural))
                return redirect(redirect_url)

        else:
            form = self.form(initial={'pk': request.POST.getlist('pk')})

        selected_objects = self.cls.objects.filter(pk__in=form.initial.get('pk'))
        if not selected_objects:
            messages.warning(request, "No {} were selected for deletion.".format(self.cls._meta.verbose_name_plural))
            return redirect(redirect_url)

        return render(request, self.template_name, {
            'form': form,
            'obj_type_plural': self.cls._meta.verbose_name_plural,
            'selected_objects': selected_objects,
            'cancel_url': redirect_url,
        })
