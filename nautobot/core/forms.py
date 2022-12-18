from django import forms
from django.utils.safestring import mark_safe

from nautobot.extras.forms import CustomFieldModelCSVForm, NautobotBulkEditForm, NautobotModelForm
from nautobot.extras.models import Role
from nautobot.extras.utils import RoleModelsQuery

from nautobot.utilities.forms import (
    BootstrapMixin,
    CSVMultipleContentTypeField,
    ColorSelect,
    MultipleContentTypeField,
    SlugField,
)

OBJ_TYPE_CHOICES = (
    ("", "All Objects"),
    (
        "Circuits",
        (
            ("provider", "Providers"),
            ("circuit", "Circuits"),
        ),
    ),
    (
        "DCIM",
        (
            ("site", "Sites"),
            ("rack", "Racks"),
            ("rackgroup", "Rack Groups"),
            ("devicetype", "Device types"),
            ("device", "Devices"),
            ("virtualchassis", "Virtual Chassis"),
            ("cable", "Cables"),
            ("powerfeed", "Power Feeds"),
        ),
    ),
    (
        "IPAM",
        (
            ("vrf", "VRFs"),
            ("aggregate", "Aggregates"),
            ("prefix", "Prefixes"),
            ("ipaddress", "IP addresses"),
            ("vlan", "VLANs"),
        ),
    ),
    ("Tenancy", (("tenant", "Tenants"),)),
    (
        "Virtualization",
        (
            ("cluster", "Clusters"),
            ("virtualmachine", "Virtual machines"),
        ),
    ),
)


class RoleForm(NautobotModelForm):
    """Generic create/update form for `Role` objects."""

    slug = SlugField()
    content_types = MultipleContentTypeField(
        required=False,
        label="Content Type(s)",
        queryset=RoleModelsQuery().as_queryset(),
    )

    class Meta:
        model = Role
        widgets = {"color": ColorSelect()}
        fields = ["name", "slug", "weight", "description", "content_types", "color"]


class RoleBulkEditForm(NautobotBulkEditForm):
    """Bulk edit/delete form for `Role` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=Role.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    content_types = MultipleContentTypeField(
        queryset=RoleModelsQuery().as_queryset(), required=False, label="Content Type(s)"
    )

    class Meta:
        nullable_fields = []


class RoleCSVForm(CustomFieldModelCSVForm):
    """Generic CSV bulk import form for `Role` objects."""

    content_types = CSVMultipleContentTypeField(
        queryset=RoleModelsQuery().as_queryset(),
        choices_as_strings=True,
        help_text=mark_safe(
            "The object types to which this role applies. Multiple values "
            "must be comma-separated and wrapped in double quotes. (e.g. "
            '<code>"dcim.device,dcim.rack"</code>)'
        ),
        label="Content type(s)",
    )

    class Meta:
        model = Role
        fields = Role.csv_headers
        help_texts = {
            "color": mark_safe("RGB color in hexadecimal (e.g. <code>00ff00</code>)"),
        }


class SearchForm(BootstrapMixin, forms.Form):
    q = forms.CharField(label="Search")
    obj_type = forms.ChoiceField(choices=OBJ_TYPE_CHOICES, required=False, label="Type")

    def __init__(self, *args, q_placeholder=None, **kwargs):
        super().__init__(*args, **kwargs)

        if q_placeholder:
            self.fields["q"].widget.attrs["placeholder"] = q_placeholder
