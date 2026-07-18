from db_file_storage.form_widgets import DBAdminClearableFileInput
from django import forms
from django.contrib import admin

from nautobot.core.admin import NautobotModelAdmin

from .models import FileProxy, JobResult, ObjectLock, ObjectLockBypassAudit


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


#
# Object locks
#


@admin.register(ObjectLock)
class ObjectLockAdmin(NautobotModelAdmin):
    list_display = ["content_type", "object_id", "prevent_delete", "prevent_update", "source_key", "expires"]
    list_filter = ["prevent_delete", "prevent_update", "source_context"]
    search_fields = ["source_key", "object_id"]
    readonly_fields = ["source_context", "source_detail", "source_key", "created_by"]

    def has_add_permission(self, request):
        """Object Locks are created via the manager/API (which derive attribution), never hand-created here."""
        return False

    def has_change_permission(self, request, obj=None):
        """Locks are view-only in admin; edits route through the API/UI, which preserve attribution."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Releasing here would bypass the force_release_objectlock ownership check; use the API/UI."""
        return False


@admin.register(ObjectLockBypassAudit)
class ObjectLockBypassAuditAdmin(NautobotModelAdmin):
    """Read-only view of bypass audit records (written only by the bypass context manager)."""

    list_display = ["time", "user", "content_type", "object_id", "suspended_other_source"]
    list_filter = ["suspended_other_source", "time"]
    search_fields = ["object_id"]
    fields = [
        "time",
        "user",
        "content_type",
        "object_id",
        "change_id",
        "suspended_source_keys",
        "suspended_fields",
        "suspended_other_source",
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        """Audit rows are written only by the bypass context manager, never created by hand."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit rows are immutable; allow viewing (read-only) but never editing."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit rows are a durable trail; deletion via admin is disabled."""
        return False
