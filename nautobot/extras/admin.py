from db_file_storage.form_widgets import DBAdminClearableFileInput
from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse

from nautobot.utilities.forms import LaxURLField
from .models import CustomField, CustomFieldChoice, CustomLink, ExportTemplate, FileProxy, JobResult, Webhook


def order_content_types(field):
    """
    Order the list of available ContentTypes by application
    """
    queryset = field.queryset.order_by("app_label", "model")
    field.choices = [(ct.pk, "{} > {}".format(ct.app_label, ct.name)) for ct in queryset]


#
# Webhooks
#


class WebhookForm(forms.ModelForm):
    payload_url = LaxURLField(label="URL")

    class Meta:
        model = Webhook
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "content_types" in self.fields:
            order_content_types(self.fields["content_types"])


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "models",
        "payload_url",
        "http_content_type",
        "enabled",
        "type_create",
        "type_update",
        "type_delete",
        "ssl_verification",
    ]
    list_filter = [
        "enabled",
        "type_create",
        "type_update",
        "type_delete",
        "content_types",
    ]
    form = WebhookForm
    fieldsets = (
        (None, {"fields": ("name", "content_types", "enabled")}),
        ("Events", {"fields": ("type_create", "type_update", "type_delete")}),
        (
            "HTTP Request",
            {
                "fields": (
                    "payload_url",
                    "http_method",
                    "http_content_type",
                    "additional_headers",
                    "body_template",
                    "secret",
                ),
                "classes": ("monospace",),
            },
        ),
        ("SSL", {"fields": ("ssl_verification", "ca_file_path")}),
    )

    def models(self, obj):
        return ", ".join([ct.name for ct in obj.content_types.all()])


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
# Custom links
#


class CustomLinkForm(forms.ModelForm):
    class Meta:
        model = CustomLink
        exclude = []
        widgets = {
            "text": forms.Textarea,
            "target_url": forms.Textarea,
        }
        help_texts = {
            "weight": "A numeric weight to influence the ordering of this link among its peers. Lower weights appear "
            "first in a list.",
            "text": "Jinja2 template code for the link text. Reference the object as <code>{{ obj }}</code>. Links "
            "which render as empty text will not be displayed.",
            "target_url": "Jinja2 template code for the link URL. Reference the object as <code>{{ obj }}</code>.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Format ContentType choices
        order_content_types(self.fields["content_type"])
        self.fields["content_type"].choices.insert(0, ("", "---------"))


@admin.register(CustomLink)
class CustomLinkAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Custom Link",
            {
                "fields": (
                    "content_type",
                    "name",
                    "group_name",
                    "weight",
                    "button_class",
                    "new_window",
                )
            },
        ),
        ("Templates", {"fields": ("text", "target_url"), "classes": ("monospace",)}),
    )
    list_display = [
        "name",
        "content_type",
        "group_name",
        "weight",
    ]
    list_filter = [
        "content_type",
    ]
    form = CustomLinkForm


#
# Export templates
#


class ExportTemplateForm(forms.ModelForm):
    class Meta:
        model = ExportTemplate
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Format ContentType choices
        order_content_types(self.fields["content_type"])
        self.fields["content_type"].choices.insert(0, ("", "---------"))


@admin.register(ExportTemplate)
class ExportTemplateAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Export Template",
            {
                "fields": (
                    "content_type",
                    "name",
                    "owner_content_type",
                    "owner_object_id",
                    "description",
                    "mime_type",
                    "file_extension",
                )
            },
        ),
        ("Content", {"fields": ("template_code",), "classes": ("monospace",)}),
    )
    list_display = [
        "name",
        "content_type",
        "owner",
        "description",
        "mime_type",
        "file_extension",
    ]
    list_filter = [
        "content_type",
        "owner_content_type",
    ]
    form = ExportTemplateForm


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
