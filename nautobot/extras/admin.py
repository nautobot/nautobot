from django.contrib import admin

from nautobot.core.admin import NautobotModelAdmin

from .models import JobResult


def order_content_types(field):
    """
    Order the list of available ContentTypes by application
    """
    queryset = field.queryset.order_by("app_label", "model")
    field.choices = [(ct.pk, f"{ct.app_label} > {ct.name}") for ct in queryset]


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
