from db_file_storage.form_widgets import DBAdminClearableFileInput
from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import admin

from nautobot.utilities.forms import LaxURLField
from .models import CustomField, CustomFieldChoice, CustomLink, ExportTemplate, FileProxy, JobResult, Webhook
from .models import FileProxy, JobResult


def order_content_types(field):
    """
    Order the list of available ContentTypes by application
    """
    queryset = field.queryset.order_by("app_label", "model")
    field.choices = [(ct.pk, "{} > {}".format(ct.app_label, ct.name)) for ct in queryset]


#
# Custom fields
#


class CustomFieldForm(forms.ModelForm):
    class Meta:
        model = CustomField
        exclude = []
        widgets = {
            "default": forms.TextInput(),
            "validation_regex": forms.Textarea(
                attrs={
                    "cols": 80,
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        order_content_types(self.fields["content_types"])


class CustomFieldChoiceAdmin(admin.TabularInline):
    """
    Defines the inline formset factory that handles choices for selection type custom fields.
    The `extra` defines the default number of inline rows that appear in the UI.
    """

    model = CustomFieldChoice
    extra = 5


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    """
    Define the structure and composition of the custom field form in the admin panel.
    """

    actions = None
    form = CustomFieldForm
    inlines = [CustomFieldChoiceAdmin]
    list_display = [
        "name",
        "models",
        "type",
        "required",
        "filter_logic",
        "default",
        "weight",
        "description",
    ]
    list_filter = [
        "type",
        "required",
        "content_types",
    ]
    fieldsets = (
        (
            "Custom Field",
            {
                "fields": (
                    "type",
                    "name",
                    "weight",
                    "label",
                    "description",
                    "required",
                    "default",
                    "filter_logic",
                )
            },
        ),
        (
            "Assignment",
            {
                "description": "A custom field must be assigned to one or more object types.",
                "fields": ("content_types",),
            },
        ),
        (
            "Validation Rules",
            {
                "fields": (
                    "validation_minimum",
                    "validation_maximum",
                    "validation_regex",
                ),
                "classes": ("monospace",),
            },
        ),
    )

    def models(self, obj):
        return ", ".join([ct.name for ct in obj.content_types.all()])

    @transaction.atomic
    def save_formset(self, request, form, formset, change):
        # TODO(John): revisit this when custom fields are moved out of admin... there is a better way...
        if formset.model != CustomFieldChoice:
            return super().save_formset(request, form, formset, change)
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
        for obj in formset.deleted_objects:
            try:
                obj.delete()
            except ProtectedError as e:
                self.message_user(request, e, level=messages.ERROR)
                raise e


#
# File attachments
#


class FileProxyForm(forms.ModelForm):
    class Meta:
        model = FileProxy
        exclude = []
        widgets = {
            "file": DBAdminClearableFileInput,
        }


@admin.register(FileProxy)
class FileProxyAdmin(admin.ModelAdmin):
    form = FileProxyForm
    list_display = ["name", "uploaded_at"]
    list_filter = ["uploaded_at"]


#
# Job results (jobs, scripts, reports, Git repository sync, etc.)
#


@admin.register(JobResult)
class JobResultAdmin(admin.ModelAdmin):
    list_display = [
        "obj_type",
        "name",
        "created",
        "completed",
        "user",
        "status",
    ]
    fields = [
        "obj_type",
        "name",
        "created",
        "completed",
        "user",
        "status",
        "data",
        "job_id",
    ]
    list_filter = [
        "status",
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False
