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
        fields = ["name", "file"]
        widgets = {
            "file": DBAdminClearableFileInput,
        }


@admin.register(FileProxy)
class FileProxyAdmin(NautobotModelAdmin):
    form = FileProxyForm
    list_display = ["name", "file", "uploaded_at"]
    list_filter = ["uploaded_at"]


#
# Job results (jobs and Git repository sync)
#


@admin.register(JobResult)
class JobResultAdmin(NautobotModelAdmin):
    list_display = [
        "name",
        "date_created",
        "date_done",
        "user",
        "status",
    ]
    fields = [
        "id",
        "name",
        "date_created",
        "date_done",
        "user",
        "status",
        "result",
    ]
    list_filter = [
        "status",
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False
