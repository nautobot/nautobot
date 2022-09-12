from db_file_storage.form_widgets import DBAdminClearableFileInput
from django import forms
from django.contrib import admin
from nautobot.core.admin import NautobotModelAdmin

from .models import FileProxy, JobResult


def order_content_types(field):
    """
    Order the list of available ContentTypes by application
    """
    queryset = field.queryset.order_by("app_label", "model")
    field.choices = [(ct.pk, f"{ct.app_label} > {ct.name}") for ct in queryset]


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
class FileProxyAdmin(NautobotModelAdmin):
    form = FileProxyForm
    list_display = ["name", "uploaded_at"]
    list_filter = ["uploaded_at"]


#
# Job results (jobs, scripts, reports, Git repository sync, etc.)
#


@admin.register(JobResult)
class JobResultAdmin(NautobotModelAdmin):
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
