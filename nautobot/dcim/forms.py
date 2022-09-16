import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.forms.array import SimpleArrayField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q
from django.utils.safestring import mark_safe
from netaddr import EUI
from netaddr.core import AddrFormatError
from timezone_field import TimeZoneFormField

from nautobot.circuits.models import Circuit, CircuitTermination, Provider
from nautobot.dcim.form_mixins import (
    LocatableModelBulkEditFormMixin,
    LocatableModelCSVFormMixin,
    LocatableModelFilterFormMixin,
    LocatableModelFormMixin,
)
from nautobot.extras.forms import (
    CustomFieldModelBulkEditFormMixin,
    CustomFieldModelCSVForm,
    NautobotBulkEditForm,
    NautobotModelForm,
    NautobotFilterForm,
    LocalContextFilterForm,
    LocalContextModelForm,
    LocalContextModelBulkEditForm,
    StatusModelBulkEditFormMixin,
    StatusModelCSVFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)
from nautobot.extras.models import SecretsGroup, Status
from nautobot.ipam.constants import BGP_ASN_MAX, BGP_ASN_MIN
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.forms import (
    APISelect,
    APISelectMultiple,
    add_blank_choice,
    BootstrapMixin,
    BulkEditNullBooleanSelect,
    ColorSelect,
    CommentField,
    CSVChoiceField,
    CSVContentTypeField,
    CSVModelChoiceField,
    CSVMultipleContentTypeField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    ExpandableNameField,
    form_from_model,
    MultipleContentTypeField,
    NumericArrayField,
    SelectWithPK,
    SmallTextarea,
    SlugField,
    StaticSelect2,
    StaticSelect2Multiple,
    TagFilterField,
)
from nautobot.utilities.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.virtualization.models import Cluster, ClusterGroup
from .choices import (
    CableLengthUnitChoices,
    CableTypeChoices,
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    InterfaceModeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)
from .constants import (
    CABLE_TERMINATION_MODELS,
    INTERFACE_MTU_MAX,
    INTERFACE_MTU_MIN,
    NONCONNECTABLE_IFACE_TYPES,
    REARPORT_POSITIONS_MAX,
    REARPORT_POSITIONS_MIN,
)

from .models import (
    Cable,
    DeviceBay,
    DeviceBayTemplate,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceRole,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
    InventoryItem,
    Platform,
    PowerFeed,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
    VirtualChassis,
)

DEVICE_BY_PK_RE = r"{\d+\}"

INTERFACE_MODE_HELP_TEXT = """
Access: One untagged VLAN<br />
Tagged: One untagged VLAN and/or one or more tagged VLANs<br />
Tagged (All): Implies all VLANs are available (w/optional untagged VLAN)
"""


def get_device_by_name_or_pk(name):
    """
    Attempt to retrieve a device by either its name or primary key ('{pk}').
    """
    if re.match(DEVICE_BY_PK_RE, name):
        pk = name.strip("{}")
        device = Device.objects.get(pk=pk)
    else:
        device = Device.objects.get(name=name)
    return device


class ConnectCableExcludeIDMixin:
    def __init__(self, *args, exclude_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if exclude_id is not None:
            self.fields["termination_b_id"].widget.add_query_param("id__n", str(exclude_id))


class DeviceComponentFilterForm(NautobotFilterForm):
    field_order = ["q", "region", "site"]
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
        query_params={"site": "$site"},
    )


class InterfaceCommonForm(forms.Form):
    def clean(self):
        super().clean()

        parent_field = "device" if "device" in self.cleaned_data else "virtual_machine"
        tagged_vlans = self.cleaned_data["tagged_vlans"]

        # Untagged interfaces cannot be assigned tagged VLANs
        if self.cleaned_data["mode"] == InterfaceModeChoices.MODE_ACCESS and tagged_vlans:
            raise forms.ValidationError({"mode": "An access interface cannot have tagged VLANs assigned."})

        # Remove all tagged VLAN assignments from "tagged all" interfaces
        elif self.cleaned_data["mode"] == InterfaceModeChoices.MODE_TAGGED_ALL:
            self.cleaned_data["tagged_vlans"] = []

        # Validate tagged VLANs; must be a global VLAN or in the same site
        elif self.cleaned_data["mode"] == InterfaceModeChoices.MODE_TAGGED:
            valid_sites = [None, self.cleaned_data[parent_field].site]
            invalid_vlans = [str(v) for v in tagged_vlans if v.site not in valid_sites]

            if invalid_vlans:
                raise forms.ValidationError(
                    {
                        "tagged_vlans": f"The tagged VLANs ({', '.join(invalid_vlans)}) must belong to the same site as "
                        f"the interface's parent device/VM, or they must be global"
                    }
                )


class ComponentForm(BootstrapMixin, forms.Form):
    """
    Subclass this form when facilitating the creation of one or more device component or component templates based on
    a name pattern.
    """

    name_pattern = ExpandableNameField(label="Name")
    label_pattern = ExpandableNameField(
        label="Label",
        required=False,
        help_text="Alphanumeric ranges are supported. (Must match the number of names being created.)",
    )

    def clean(self):
        super().clean()

        # Validate that the number of components being created from both the name_pattern and label_pattern are equal
        if self.cleaned_data["label_pattern"]:
            name_pattern_count = len(self.cleaned_data["name_pattern"])
            label_pattern_count = len(self.cleaned_data["label_pattern"])
            if name_pattern_count != label_pattern_count:
                raise forms.ValidationError(
                    {
                        "label_pattern": f"The provided name pattern will create {name_pattern_count} components, however "
                        f"{label_pattern_count} labels will be generated. These counts must match."
                    },
                    code="label_pattern_mismatch",
                )


#
# Fields
#


class MACAddressField(forms.Field):
    widget = forms.CharField
    default_error_messages = {
        "invalid": "MAC address must be in EUI-48 format",
    }

    def to_python(self, value):
        value = super().to_python(value)

        # Validate MAC address format
        try:
            value = EUI(value.strip())
        except AddrFormatError:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

        return value


#
# Regions
#


class RegionForm(NautobotModelForm):
    parent = DynamicModelChoiceField(queryset=Region.objects.all(), required=False)
    slug = SlugField()

    class Meta:
        model = Region
        fields = (
            "parent",
            "name",
            "slug",
            "description",
        )


class RegionCSVForm(CustomFieldModelCSVForm):
    parent = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Name of parent region",
    )

    class Meta:
        model = Region
        fields = Region.csv_headers


class RegionFilterForm(NautobotFilterForm):
    model = Site
    q = forms.CharField(required=False, label="Search")


#
# Sites
#


class SiteForm(NautobotModelForm, TenancyForm):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False)
    slug = SlugField()
    comments = CommentField()

    class Meta:
        model = Site
        fields = [
            "name",
            "slug",
            "status",
            "region",
            "tenant_group",
            "tenant",
            "facility",
            "asn",
            "time_zone",
            "description",
            "physical_address",
            "shipping_address",
            "latitude",
            "longitude",
            "contact_name",
            "contact_phone",
            "contact_email",
            "comments",
            "tags",
        ]
        widgets = {
            "physical_address": SmallTextarea(
                attrs={
                    "rows": 3,
                }
            ),
            "shipping_address": SmallTextarea(
                attrs={
                    "rows": 3,
                }
            ),
            "time_zone": StaticSelect2(),
        }
        help_texts = {
            "name": "Full name of the site",
            "facility": "Data center provider and facility (e.g. Equinix NY7)",
            "asn": "BGP autonomous system number",
            "time_zone": "Local time zone",
            "description": "Short description (will appear in sites list)",
            "physical_address": "Physical location of the building (e.g. for GPS)",
            "shipping_address": "If different from the physical address",
            "latitude": "Latitude in decimal format (xx.yyyyyy)",
            "longitude": "Longitude in decimal format (xx.yyyyyy)",
        }


class SiteCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    region = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned region",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned tenant",
    )

    class Meta:
        model = Site
        fields = Site.csv_headers
        help_texts = {
            "time_zone": mark_safe(
                'Time zone (<a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">available options</a>)'
            )
        }


class SiteBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Site.objects.all(), widget=forms.MultipleHiddenInput)
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    asn = forms.IntegerField(min_value=BGP_ASN_MIN, max_value=BGP_ASN_MAX, required=False, label="ASN")
    description = forms.CharField(max_length=100, required=False)
    time_zone = TimeZoneFormField(
        choices=add_blank_choice(TimeZoneFormField().choices),
        required=False,
        widget=StaticSelect2(),
    )

    class Meta:
        nullable_fields = [
            "region",
            "tenant",
            "asn",
            "description",
            "time_zone",
        ]


class SiteFilterForm(NautobotFilterForm, TenancyFilterForm, StatusModelFilterFormMixin):
    model = Site
    field_order = ["q", "status", "region", "tenant_group", "tenant"]
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    tag = TagFilterField(model)


#
# LocationTypes
#


class LocationTypeForm(NautobotModelForm):
    parent = DynamicModelChoiceField(queryset=LocationType.objects.all(), required=False)
    slug = SlugField()
    content_types = MultipleContentTypeField(
        feature="locations",
        help_text="The object type(s) that can be associated to a Location of this type",
        required=False,
    )

    class Meta:
        model = LocationType
        fields = ("parent", "name", "slug", "description", "content_types")


class LocationTypeCSVForm(CustomFieldModelCSVForm):
    parent = CSVModelChoiceField(
        queryset=LocationType.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Name of parent location type",
    )
    content_types = CSVMultipleContentTypeField(
        feature="locations",
        required=False,
        choices_as_strings=True,
        help_text=mark_safe(
            "The object types to which this status applies. Multiple values "
            "must be comma-separated and wrapped in double quotes. (e.g. "
            '<code>"dcim.device,dcim.rack"</code>)'
        ),
    )

    class Meta:
        model = LocationType
        fields = LocationType.csv_headers


class LocationTypeFilterForm(NautobotFilterForm):
    model = LocationType
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(feature="locations", choices_as_strings=True, required=False)


#
# Locations
#


class LocationForm(NautobotModelForm, TenancyForm):
    slug = SlugField(slug_source=("parent", "name"))
    location_type = DynamicModelChoiceField(queryset=LocationType.objects.all())
    parent = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        query_params={"child_location_type": "$location_type"},
        required=False,
    )
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)

    class Meta:
        model = Location
        fields = [
            "location_type",
            "parent",
            "site",
            "name",
            "slug",
            "status",
            "tenant_group",
            "tenant",
            "description",
            "tags",
        ]


class LocationBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Location.objects.all(), widget=forms.MultipleHiddenInput)
    # location_type is not editable on existing instances
    parent = DynamicModelChoiceField(queryset=Location.objects.all(), required=False)
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=100, required=False)

    class Meta:
        nullable_fields = [
            "parent",
            "site",
            "tenant",
            "description",
        ]


class LocationCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    location_type = CSVModelChoiceField(
        queryset=LocationType.objects.all(),
        to_field_name="name",
        help_text="Location type",
    )
    parent = CSVModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Parent location",
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Parent site",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned tenant",
    )

    class Meta:
        model = Location
        fields = Location.csv_headers


class LocationFilterForm(NautobotFilterForm, StatusModelFilterFormMixin, TenancyFilterForm):
    model = Location
    field_order = ["q", "location_type", "parent", "status", "tenant_group", "tenant", "tag"]

    q = forms.CharField(required=False, label="Search")
    location_type = DynamicModelMultipleChoiceField(
        queryset=LocationType.objects.all(), to_field_name="slug", required=False
    )
    parent = DynamicModelMultipleChoiceField(queryset=Location.objects.all(), to_field_name="slug", required=False)
    tag = TagFilterField(model)


#
# Rack groups
#


class RackGroupForm(LocatableModelFormMixin, NautobotModelForm):
    parent = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )
    slug = SlugField()

    class Meta:
        model = RackGroup
        fields = (
            "region",
            "site",
            "location",
            "parent",
            "name",
            "slug",
            "description",
        )


class RackGroupCSVForm(LocatableModelCSVFormMixin, CustomFieldModelCSVForm):
    parent = CSVModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Parent rack group",
        error_messages={
            "invalid_choice": "Rack group not found.",
        },
    )

    class Meta:
        model = RackGroup
        fields = RackGroup.csv_headers


class RackGroupFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin):
    model = RackGroup
    parent = DynamicModelMultipleChoiceField(
        queryset=RackGroup.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={
            "region": "$region",
            "site": "$site",
        },
    )


#
# Rack roles
#


class RackRoleForm(NautobotModelForm):
    slug = SlugField()

    class Meta:
        model = RackRole
        fields = [
            "name",
            "slug",
            "color",
            "description",
        ]


class RackRoleCSVForm(CustomFieldModelCSVForm):
    class Meta:
        model = RackRole
        fields = RackRole.csv_headers
        help_texts = {
            "color": mark_safe("RGB color in hexadecimal (e.g. <code>00ff00</code>)"),
        }


#
# Racks
#


class RackForm(LocatableModelFormMixin, NautobotModelForm, TenancyForm):
    group = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )
    role = DynamicModelChoiceField(queryset=RackRole.objects.all(), required=False)
    comments = CommentField()

    class Meta:
        model = Rack
        fields = [
            "region",
            "site",
            "location",
            "group",
            "name",
            "facility_id",
            "tenant_group",
            "tenant",
            "status",
            "role",
            "serial",
            "asset_tag",
            "type",
            "width",
            "u_height",
            "desc_units",
            "outer_width",
            "outer_depth",
            "outer_unit",
            "comments",
            "tags",
        ]
        help_texts = {
            "site": "The site at which the rack exists",
            "location": "The specific location of the rack",
            "name": "Organizational rack name",
            "facility_id": "The unique rack ID assigned by the facility",
            "u_height": "Height in rack units",
        }
        widgets = {
            "type": StaticSelect2(),
            "width": StaticSelect2(),
            "outer_unit": StaticSelect2(),
        }


class RackCSVForm(LocatableModelCSVFormMixin, StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    group = CSVModelChoiceField(queryset=RackGroup.objects.all(), required=False, to_field_name="name")
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Name of assigned tenant",
    )
    role = CSVModelChoiceField(
        queryset=RackRole.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Name of assigned role",
    )
    type = CSVChoiceField(choices=RackTypeChoices, required=False, help_text="Rack type")
    width = forms.ChoiceField(choices=RackWidthChoices, help_text="Rail-to-rail width (in inches)")
    outer_unit = CSVChoiceField(
        choices=RackDimensionUnitChoices,
        required=False,
        help_text="Unit for outer dimensions",
    )

    class Meta:
        model = Rack
        fields = Rack.csv_headers

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit group queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get("site")}
            self.fields["group"].queryset = self.fields["group"].queryset.filter(**params)


class RackBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Rack.objects.all(), widget=forms.MultipleHiddenInput)
    group = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    role = DynamicModelChoiceField(queryset=RackRole.objects.all(), required=False)
    serial = forms.CharField(max_length=255, required=False, label="Serial Number")
    asset_tag = forms.CharField(max_length=50, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(RackTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    width = forms.ChoiceField(
        choices=add_blank_choice(RackWidthChoices),
        required=False,
        widget=StaticSelect2(),
    )
    u_height = forms.IntegerField(required=False, label="Height (U)")
    desc_units = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Descending units")
    outer_width = forms.IntegerField(required=False, min_value=1)
    outer_depth = forms.IntegerField(required=False, min_value=1)
    outer_unit = forms.ChoiceField(
        choices=add_blank_choice(RackDimensionUnitChoices),
        required=False,
        widget=StaticSelect2(),
    )
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        model = Rack
        nullable_fields = [
            "location",
            "group",
            "tenant",
            "role",
            "serial",
            "asset_tag",
            "outer_width",
            "outer_depth",
            "outer_unit",
            "comments",
        ]


class RackFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin, TenancyFilterForm, StatusModelFilterFormMixin):
    model = Rack
    field_order = [
        "q",
        "region",
        "site",
        "location",
        "group_id",
        "status",
        "role",
        "tenant_group",
        "tenant",
    ]
    q = forms.CharField(required=False, label="Search")
    group_id = DynamicModelMultipleChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        label="Rack group",
        null_option="None",
        query_params={"site": "$site"},
    )
    type = forms.MultipleChoiceField(choices=RackTypeChoices, required=False, widget=StaticSelect2Multiple())
    width = forms.MultipleChoiceField(choices=RackWidthChoices, required=False, widget=StaticSelect2Multiple())
    role = DynamicModelMultipleChoiceField(
        queryset=RackRole.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
    )
    tag = TagFilterField(model)


#
# Rack elevations
#


class RackElevationFilterForm(RackFilterForm):
    field_order = [
        "q",
        "region",
        "site",
        "group_id",
        "id",
        "status",
        "role",
        "tenant_group",
        "tenant",
    ]
    id = DynamicModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        label="Rack",
        required=False,
        query_params={
            "site": "$site",
            "group_id": "$group_id",
        },
    )


#
# Rack reservations
#


class RackReservationForm(NautobotModelForm, TenancyForm):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, initial_params={"sites": "$site"})
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={"region_id": "$region"},
    )
    rack_group = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        query_params={
            "site_id": "$site",
            "group_id": "$rack_group",
        },
    )
    units = NumericArrayField(
        base_field=forms.IntegerField(),
        help_text="Comma-separated list of numeric unit IDs. A range may be specified using a hyphen.",
    )
    user = forms.ModelChoiceField(queryset=get_user_model().objects.order_by("username"), widget=StaticSelect2())

    class Meta:
        model = RackReservation
        fields = [
            "rack",
            "units",
            "user",
            "tenant_group",
            "tenant",
            "description",
            "tags",
        ]


class RackReservationCSVForm(CustomFieldModelCSVForm):
    site = CSVModelChoiceField(queryset=Site.objects.all(), to_field_name="name", help_text="Parent site")
    rack_group = CSVModelChoiceField(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Rack's group (if any)",
    )
    rack = CSVModelChoiceField(queryset=Rack.objects.all(), to_field_name="name", help_text="Rack")
    units = SimpleArrayField(
        base_field=forms.IntegerField(),
        required=True,
        help_text="Comma-separated list of individual unit numbers",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned tenant",
    )

    class Meta:
        model = RackReservation
        fields = ("site", "rack_group", "rack", "units", "tenant", "description")

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit rack_group queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get("site")}
            self.fields["rack_group"].queryset = self.fields["rack_group"].queryset.filter(**params)

            # Limit rack queryset by assigned site and group
            params = {
                f"site__{self.fields['site'].to_field_name}": data.get("site"),
                f"group__{self.fields['rack_group'].to_field_name}": data.get("rack_group"),
            }
            self.fields["rack"].queryset = self.fields["rack"].queryset.filter(**params)


class RackReservationBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RackReservation.objects.all(), widget=forms.MultipleHiddenInput())
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.order_by("username"),
        required=False,
        widget=StaticSelect2(),
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=100, required=False)

    class Meta:
        nullable_fields = []


class RackReservationFilterForm(NautobotFilterForm, TenancyFilterForm):
    model = RackReservation
    field_order = [
        "q",
        "region",
        "site",
        "group_id",
        "user_id",
        "tenant_group",
        "tenant",
    ]
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    group_id = DynamicModelMultipleChoiceField(
        queryset=RackGroup.objects.prefetch_related("site"),
        required=False,
        label="Rack group",
        null_option="None",
    )
    user_id = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="User",
        widget=APISelectMultiple(
            api_url="/api/users/users/",
        ),
    )
    tag = TagFilterField(model)


#
# Manufacturers
#


class ManufacturerForm(NautobotModelForm):
    slug = SlugField()

    class Meta:
        model = Manufacturer
        fields = [
            "name",
            "slug",
            "description",
        ]


class ManufacturerCSVForm(CustomFieldModelCSVForm):
    class Meta:
        model = Manufacturer
        fields = Manufacturer.csv_headers


#
# Device types
#


class DeviceTypeForm(NautobotModelForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all())
    slug = SlugField(slug_source="model")
    comments = CommentField()

    class Meta:
        model = DeviceType
        fields = [
            "manufacturer",
            "model",
            "slug",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "front_image",
            "rear_image",
            "comments",
            "tags",
        ]
        widgets = {
            "subdevice_role": StaticSelect2(),
            # Exclude SVG images (unsupported by PIL)
            "front_image": forms.ClearableFileInput(
                attrs={"accept": "image/bmp,image/gif,image/jpeg,image/png,image/tiff"}
            ),
            "rear_image": forms.ClearableFileInput(
                attrs={"accept": "image/bmp,image/gif,image/jpeg,image/png,image/tiff"}
            ),
        }


class DeviceTypeImportForm(BootstrapMixin, forms.ModelForm):
    manufacturer = forms.ModelChoiceField(queryset=Manufacturer.objects.all(), to_field_name="name")

    class Meta:
        model = DeviceType
        fields = [
            "manufacturer",
            "model",
            "slug",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "comments",
        ]


class DeviceTypeBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=DeviceType.objects.all(), widget=forms.MultipleHiddenInput())
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    u_height = forms.IntegerField(required=False)
    is_full_depth = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect(), label="Is full depth")

    class Meta:
        nullable_fields = []


class DeviceTypeFilterForm(NautobotFilterForm):
    model = DeviceType
    q = forms.CharField(required=False, label="Search")
    manufacturer = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(), to_field_name="slug", required=False
    )
    subdevice_role = forms.MultipleChoiceField(
        choices=add_blank_choice(SubdeviceRoleChoices),
        required=False,
        widget=StaticSelect2Multiple(),
    )
    console_ports = forms.NullBooleanField(
        required=False,
        label="Has console ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    console_server_ports = forms.NullBooleanField(
        required=False,
        label="Has console server ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    power_ports = forms.NullBooleanField(
        required=False,
        label="Has power ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    power_outlets = forms.NullBooleanField(
        required=False,
        label="Has power outlets",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    interfaces = forms.NullBooleanField(
        required=False,
        label="Has interfaces",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    pass_through_ports = forms.NullBooleanField(
        required=False,
        label="Has pass-through ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)


#
# Device component templates
#


class ComponentTemplateCreateForm(ComponentForm):
    """
    Base form for the creation of device component templates (subclassed from ComponentTemplateModel).
    """

    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        initial_params={"device_types": "device_type"},
    )
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        query_params={"manufacturer_id": "$manufacturer"},
    )
    description = forms.CharField(required=False)


class ConsolePortTemplateForm(NautobotModelForm):
    class Meta:
        model = ConsolePortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
        }


class ConsolePortTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(choices=add_blank_choice(ConsolePortTypeChoices), widget=StaticSelect2())
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "description",
    )


class ConsolePortTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ConsolePortTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(ConsolePortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )

    class Meta:
        nullable_fields = ["label", "type", "description"]


class ConsoleServerPortTemplateForm(NautobotModelForm):
    class Meta:
        model = ConsoleServerPortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
        }


class ConsoleServerPortTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(choices=add_blank_choice(ConsolePortTypeChoices), widget=StaticSelect2())
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "description",
    )


class ConsoleServerPortTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=ConsoleServerPortTemplate.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(ConsolePortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = ["label", "type", "description"]


class PowerPortTemplateForm(NautobotModelForm):
    class Meta:
        model = PowerPortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
        }


class PowerPortTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(choices=add_blank_choice(PowerPortTypeChoices), required=False)
    maximum_draw = forms.IntegerField(min_value=1, required=False, help_text="Maximum power draw (watts)")
    allocated_draw = forms.IntegerField(min_value=1, required=False, help_text="Allocated power draw (watts)")
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "maximum_draw",
        "allocated_draw",
        "description",
    )


class PowerPortTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=PowerPortTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(PowerPortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    maximum_draw = forms.IntegerField(min_value=1, required=False, help_text="Maximum power draw (watts)")
    allocated_draw = forms.IntegerField(min_value=1, required=False, help_text="Allocated power draw (watts)")
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = [
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
        ]


class PowerOutletTemplateForm(NautobotModelForm):
    class Meta:
        model = PowerOutletTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Limit power_port choices to current DeviceType
        if hasattr(self.instance, "device_type"):
            self.fields["power_port"].queryset = PowerPortTemplate.objects.filter(device_type=self.instance.device_type)


class PowerOutletTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(choices=add_blank_choice(PowerOutletTypeChoices), required=False)
    power_port = forms.ModelChoiceField(queryset=PowerPortTemplate.objects.all(), required=False)
    feed_leg = forms.ChoiceField(
        choices=add_blank_choice(PowerOutletFeedLegChoices),
        required=False,
        widget=StaticSelect2(),
    )
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "power_port",
        "feed_leg",
        "description",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit power_port choices to current DeviceType
        device_type = DeviceType.objects.get(pk=self.initial.get("device_type") or self.data.get("device_type"))
        self.fields["power_port"].queryset = PowerPortTemplate.objects.filter(device_type=device_type)


class PowerOutletTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=PowerOutletTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    device_type = forms.ModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        disabled=True,
        widget=forms.HiddenInput(),
    )
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(PowerOutletTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    power_port = forms.ModelChoiceField(queryset=PowerPortTemplate.objects.all(), required=False)
    feed_leg = forms.ChoiceField(
        choices=add_blank_choice(PowerOutletFeedLegChoices),
        required=False,
        widget=StaticSelect2(),
    )
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = ["label", "type", "power_port", "feed_leg", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit power_port queryset to PowerPortTemplates which belong to the parent DeviceType
        if "device_type" in self.initial:
            device_type = DeviceType.objects.filter(pk=self.initial["device_type"]).first()
            self.fields["power_port"].queryset = PowerPortTemplate.objects.filter(device_type=device_type)
        else:
            self.fields["power_port"].choices = ()
            self.fields["power_port"].widget.attrs["disabled"] = True


class InterfaceTemplateForm(NautobotModelForm):
    class Meta:
        model = InterfaceTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "mgmt_only",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
            "type": StaticSelect2(),
        }


class InterfaceTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(choices=InterfaceTypeChoices, widget=StaticSelect2())
    mgmt_only = forms.BooleanField(required=False, label="Management only")
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "mgmt_only",
        "description",
    )


class InterfaceTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=InterfaceTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(InterfaceTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    mgmt_only = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Management only")
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = ["label", "description"]


class FrontPortTemplateForm(NautobotModelForm):
    class Meta:
        model = FrontPortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
            "rear_port": StaticSelect2(),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Limit rear_port choices to current DeviceType
        if hasattr(self.instance, "device_type"):
            self.fields["rear_port"].queryset = RearPortTemplate.objects.filter(device_type=self.instance.device_type)


class FrontPortTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(choices=PortTypeChoices, widget=StaticSelect2())
    rear_port_set = forms.MultipleChoiceField(
        choices=[],
        label="Rear ports",
        help_text="Select one rear port assignment for each front port being created.",
    )
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "rear_port_set",
        "description",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        device_type = DeviceType.objects.get(pk=self.initial.get("device_type") or self.data.get("device_type"))

        # Determine which rear port positions are occupied. These will be excluded from the list of available mappings.
        occupied_port_positions = [
            (front_port.rear_port_id, front_port.rear_port_position)
            for front_port in device_type.frontporttemplates.all()
        ]

        # Populate rear port choices
        choices = []
        rear_ports = RearPortTemplate.objects.filter(device_type=device_type)
        for rear_port in rear_ports:
            for i in range(1, rear_port.positions + 1):
                if (rear_port.pk, i) not in occupied_port_positions:
                    choices.append(
                        (
                            f"{rear_port.pk}:{i}",
                            f"{rear_port.name}:{i}",
                        )
                    )
        self.fields["rear_port_set"].choices = choices

    def clean(self):
        super().clean()

        # Validate that the number of ports being created equals the number of selected (rear port, position) tuples
        front_port_count = len(self.cleaned_data["name_pattern"])
        rear_port_count = len(self.cleaned_data["rear_port_set"])
        if front_port_count != rear_port_count:
            raise forms.ValidationError(
                {
                    "rear_port_set": (
                        f"The provided name pattern will create {front_port_count} ports, "
                        f"however {rear_port_count} rear port assignments were selected. These counts must match."
                    )
                }
            )

    def get_iterative_data(self, iteration):

        # Assign rear port and position from selected set
        rear_port, position = self.cleaned_data["rear_port_set"][iteration].split(":")

        return {
            "rear_port": rear_port,
            "rear_port_position": int(position),
        }


class FrontPortTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=FrontPortTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(PortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = ["description"]


class RearPortTemplateForm(NautobotModelForm):
    class Meta:
        model = RearPortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "positions",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
            "type": StaticSelect2(),
        }


class RearPortTemplateCreateForm(ComponentTemplateCreateForm):
    type = forms.ChoiceField(
        choices=PortTypeChoices,
        widget=StaticSelect2(),
    )
    positions = forms.IntegerField(
        min_value=REARPORT_POSITIONS_MIN,
        max_value=REARPORT_POSITIONS_MAX,
        initial=1,
        help_text="The number of front ports which may be mapped to each rear port",
    )
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "type",
        "positions",
        "description",
    )


class RearPortTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RearPortTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    label = forms.CharField(max_length=64, required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(PortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = ["description"]


class DeviceBayTemplateForm(NautobotModelForm):
    class Meta:
        model = DeviceBayTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "description",
        ]
        widgets = {
            "device_type": forms.HiddenInput(),
        }


class DeviceBayTemplateCreateForm(ComponentTemplateCreateForm):
    field_order = (
        "manufacturer",
        "device_type",
        "name_pattern",
        "label_pattern",
        "description",
    )


class DeviceBayTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=DeviceBayTemplate.objects.all(), widget=forms.MultipleHiddenInput())
    label = forms.CharField(max_length=64, required=False)
    description = forms.CharField(required=False)

    class Meta:
        nullable_fields = ("label", "description")


#
# Component template import forms
#


class ComponentTemplateImportForm(BootstrapMixin, CustomFieldModelCSVForm):
    def __init__(self, device_type, data=None, *args, **kwargs):

        # Must pass the parent DeviceType on form initialization
        data.update(
            {
                "device_type": device_type.pk,
            }
        )

        super().__init__(data, *args, **kwargs)

    def clean_device_type(self):

        data = self.cleaned_data["device_type"]

        # Limit fields referencing other components to the parent DeviceType
        for field_name, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField) and field_name != "device_type":
                field.queryset = field.queryset.filter(device_type=data)

        return data


class ConsolePortTemplateImportForm(ComponentTemplateImportForm):
    class Meta:
        model = ConsolePortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
        ]


class ConsoleServerPortTemplateImportForm(ComponentTemplateImportForm):
    class Meta:
        model = ConsoleServerPortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
        ]


class PowerPortTemplateImportForm(ComponentTemplateImportForm):
    class Meta:
        model = PowerPortTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
        ]


class PowerOutletTemplateImportForm(ComponentTemplateImportForm):
    power_port = forms.ModelChoiceField(queryset=PowerPortTemplate.objects.all(), to_field_name="name", required=False)

    class Meta:
        model = PowerOutletTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
        ]


class InterfaceTemplateImportForm(ComponentTemplateImportForm):
    type = forms.ChoiceField(choices=InterfaceTypeChoices.CHOICES)

    class Meta:
        model = InterfaceTemplate
        fields = [
            "device_type",
            "name",
            "label",
            "type",
            "mgmt_only",
        ]


class FrontPortTemplateImportForm(ComponentTemplateImportForm):
    type = forms.ChoiceField(choices=PortTypeChoices.CHOICES)
    rear_port = forms.ModelChoiceField(queryset=RearPortTemplate.objects.all(), to_field_name="name", required=False)

    class Meta:
        model = FrontPortTemplate
        fields = [
            "device_type",
            "name",
            "type",
            "rear_port",
            "rear_port_position",
        ]


class RearPortTemplateImportForm(ComponentTemplateImportForm):
    type = forms.ChoiceField(choices=PortTypeChoices.CHOICES)

    class Meta:
        model = RearPortTemplate
        fields = [
            "device_type",
            "name",
            "type",
            "positions",
        ]


class DeviceBayTemplateImportForm(ComponentTemplateImportForm):
    class Meta:
        model = DeviceBayTemplate
        fields = [
            "device_type",
            "name",
        ]


#
# Device roles
#


class DeviceRoleForm(NautobotModelForm):
    slug = SlugField()

    class Meta:
        model = DeviceRole
        fields = [
            "name",
            "slug",
            "color",
            "vm_role",
            "description",
        ]


class DeviceRoleCSVForm(CustomFieldModelCSVForm):
    class Meta:
        model = DeviceRole
        fields = DeviceRole.csv_headers
        help_texts = {
            "color": mark_safe("RGB color in hexadecimal (e.g. <code>00ff00</code>)"),
        }


#
# Platforms
#


class PlatformForm(NautobotModelForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    slug = SlugField(max_length=64)

    class Meta:
        model = Platform
        fields = [
            "name",
            "slug",
            "manufacturer",
            "napalm_driver",
            "napalm_args",
            "description",
        ]
        widgets = {
            "napalm_args": SmallTextarea(),
        }


class PlatformCSVForm(CustomFieldModelCSVForm):
    manufacturer = CSVModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Limit platform assignments to this manufacturer",
    )

    class Meta:
        model = Platform
        fields = Platform.csv_headers


#
# Devices
#


class DeviceForm(LocatableModelFormMixin, NautobotModelForm, TenancyForm, LocalContextModelForm):
    rack_group = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
        initial_params={"racks": "$rack"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        query_params={
            "site_id": "$site",
            "group_id": "$rack_group",
        },
    )
    position = forms.IntegerField(
        required=False,
        help_text="The lowest-numbered unit occupied by the device",
        widget=APISelect(
            api_url="/api/dcim/racks/{{rack}}/elevation/",
            attrs={
                "disabled-indicator": "device",
                "data-query-param-face": '["$face"]',
            },
        ),
    )
    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        initial_params={"device_types": "$device_type"},
    )
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        query_params={"manufacturer_id": "$manufacturer"},
    )
    device_role = DynamicModelChoiceField(queryset=DeviceRole.objects.all())
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        query_params={"manufacturer_id": ["$manufacturer", "null"]},
    )
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False)
    cluster_group = DynamicModelChoiceField(
        queryset=ClusterGroup.objects.all(),
        required=False,
        null_option="None",
        initial_params={"clusters": "$cluster"},
    )
    cluster = DynamicModelChoiceField(
        queryset=Cluster.objects.all(),
        required=False,
        query_params={"group_id": "$cluster_group"},
    )
    comments = CommentField()

    class Meta:
        model = Device
        fields = [
            "name",
            "device_role",
            "device_type",
            "serial",
            "asset_tag",
            "site",
            "location",
            "rack",
            "position",
            "face",
            "status",
            "platform",
            "primary_ip4",
            "primary_ip6",
            "secrets_group",
            "cluster_group",
            "cluster",
            "tenant_group",
            "tenant",
            "comments",
            "tags",
            "local_context_data",
            "local_context_schema",
        ]
        help_texts = {
            "device_role": "The function this device serves",
            "serial": "Chassis serial number",
            "local_context_data": "Local config context data overwrites all source contexts in the final rendered "
            "config context",
        }
        widgets = {
            "face": StaticSelect2(),
            "primary_ip4": StaticSelect2(),
            "primary_ip6": StaticSelect2(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.present_in_database:

            # Compile list of choices for primary IPv4 and IPv6 addresses
            for family in [4, 6]:
                ip_choices = [(None, "---------")]

                # Gather PKs of all interfaces belonging to this Device or a peer VirtualChassis member
                interface_ids = self.instance.vc_interfaces.values_list("pk", flat=True)

                # Collect interface IPs
                interface_ips = (
                    IPAddress.objects.ip_family(family)
                    .filter(
                        assigned_object_type=ContentType.objects.get_for_model(Interface),
                        assigned_object_id__in=interface_ids,
                    )
                    .prefetch_related("assigned_object")
                )
                if interface_ips:
                    ip_list = [(ip.id, f"{ip.address} ({ip.assigned_object})") for ip in interface_ips]
                    ip_choices.append(("Interface IPs", ip_list))
                # Collect NAT IPs
                nat_ips = (
                    IPAddress.objects.prefetch_related("nat_inside")
                    .ip_family(family)
                    .filter(
                        nat_inside__assigned_object_type=ContentType.objects.get_for_model(Interface),
                        nat_inside__assigned_object_id__in=interface_ids,
                    )
                    .prefetch_related("assigned_object")
                )
                if nat_ips:
                    ip_list = [(ip.id, f"{ip.address} (NAT)") for ip in nat_ips]
                    ip_choices.append(("NAT IPs", ip_list))
                self.fields[f"primary_ip{family}"].choices = ip_choices

            # If editing an existing device, exclude it from the list of occupied rack units. This ensures that a device
            # can be flipped from one face to another.
            self.fields["position"].widget.add_query_param("exclude", self.instance.pk)

            # Limit platform by manufacturer
            self.fields["platform"].queryset = Platform.objects.filter(
                Q(manufacturer__isnull=True) | Q(manufacturer=self.instance.device_type.manufacturer)
            )

            # Disable rack assignment if this is a child device installed in a parent device
            if self.instance.device_type.is_child_device and hasattr(self.instance, "parent_bay"):
                self.fields["site"].disabled = True
                self.fields["rack"].disabled = True
                self.initial["site"] = self.instance.parent_bay.device.site_id
                self.initial["rack"] = self.instance.parent_bay.device.rack_id

        else:

            # An object that doesn't exist yet can't have any IPs assigned to it
            self.fields["primary_ip4"].choices = []
            self.fields["primary_ip4"].widget.attrs["readonly"] = True
            self.fields["primary_ip6"].choices = []
            self.fields["primary_ip6"].widget.attrs["readonly"] = True

        # Rack position
        position = self.data.get("position") or self.initial.get("position")
        if position:
            self.fields["position"].widget.choices = [(position, f"U{position}")]


class BaseDeviceCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    device_role = CSVModelChoiceField(
        queryset=DeviceRole.objects.all(),
        to_field_name="name",
        help_text="Assigned role",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned tenant",
    )
    manufacturer = CSVModelChoiceField(
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        help_text="Device type manufacturer",
    )
    device_type = CSVModelChoiceField(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        help_text="Device type model",
    )
    platform = CSVModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned platform",
    )
    cluster = CSVModelChoiceField(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Virtualization cluster",
    )
    secrets_group = CSVModelChoiceField(
        queryset=SecretsGroup.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Secrets group",
    )

    class Meta:
        fields = []
        model = Device

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit device type queryset by manufacturer
            params = {f"manufacturer__{self.fields['manufacturer'].to_field_name}": data.get("manufacturer")}
            self.fields["device_type"].queryset = self.fields["device_type"].queryset.filter(**params)


class DeviceCSVForm(LocatableModelCSVFormMixin, BaseDeviceCSVForm):
    rack_group = CSVModelChoiceField(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Rack's group (if any)",
    )
    rack = CSVModelChoiceField(
        queryset=Rack.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Assigned rack",
    )
    face = CSVChoiceField(choices=DeviceFaceChoices, required=False, help_text="Mounted rack face")

    class Meta(BaseDeviceCSVForm.Meta):
        fields = [
            "name",
            "device_role",
            "tenant",
            "manufacturer",
            "device_type",
            "platform",
            "serial",
            "asset_tag",
            "status",
            "site",
            "location",
            "rack_group",
            "rack",
            "position",
            "face",
            "cluster",
            "comments",
        ]

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit rack_group queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get("site")}
            self.fields["rack_group"].queryset = self.fields["rack_group"].queryset.filter(**params)

            # Limit rack queryset by assigned site and group
            params = {
                f"site__{self.fields['site'].to_field_name}": data.get("site"),
                f"group__{self.fields['rack_group'].to_field_name}": data.get("rack_group"),
            }
            self.fields["rack"].queryset = self.fields["rack"].queryset.filter(**params)

            # TODO: limit location queryset by assigned site


class ChildDeviceCSVForm(BaseDeviceCSVForm):
    parent = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name", help_text="Parent device")
    device_bay = CSVModelChoiceField(
        queryset=DeviceBay.objects.all(),
        to_field_name="name",
        help_text="Device bay in which this device is installed",
    )

    class Meta(BaseDeviceCSVForm.Meta):
        fields = [
            "name",
            "device_role",
            "tenant",
            "manufacturer",
            "device_type",
            "platform",
            "serial",
            "asset_tag",
            "status",
            "parent",
            "device_bay",
            "cluster",
            "comments",
        ]

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit device bay queryset by parent device
            params = {f"device__{self.fields['parent'].to_field_name}": data.get("parent")}
            self.fields["device_bay"].queryset = self.fields["device_bay"].queryset.filter(**params)

    def clean(self):
        super().clean()

        # Set parent_bay reverse relationship
        device_bay = self.cleaned_data.get("device_bay")
        if device_bay:
            self.instance.parent_bay = device_bay

        # Inherit site and rack from parent device
        parent = self.cleaned_data.get("parent")
        if parent:
            self.instance.site = parent.site
            self.instance.rack = parent.rack


class DeviceBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    NautobotBulkEditForm,
    LocalContextModelBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Device.objects.all(), widget=forms.MultipleHiddenInput())
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        query_params={"manufacturer_id": "$manufacturer"},
    )
    rack = DynamicModelChoiceField(queryset=Rack.objects.all(), required=False)
    position = forms.IntegerField(required=False)
    face = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(DeviceFaceChoices),
        widget=StaticSelect2(),
    )
    rack_group = DynamicModelChoiceField(queryset=RackGroup.objects.all(), required=False)
    device_role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False)
    serial = forms.CharField(max_length=255, required=False, label="Serial Number")
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False)

    class Meta:
        model = Device
        nullable_fields = [
            "location",
            "tenant",
            "platform",
            "serial",
            "rack",
            "position",
            "face",
            "rack_group",
            "secrets_group",
        ]

    def __init__(self, *args, **kwrags):
        super().__init__(*args, **kwrags)

        # Disable position because only setting null value is required
        self.fields["position"].disabled = True


class DeviceFilterForm(
    NautobotFilterForm,
    LocalContextFilterForm,
    LocatableModelFilterFormMixin,
    TenancyFilterForm,
    StatusModelFilterFormMixin,
):
    model = Device
    field_order = [
        "q",
        "region",
        "site",
        "location",
        "rack_group_id",
        "rack_id",
        "status",
        "role",
        "tenant_group",
        "tenant",
        "manufacturer_id",
        "device_type_id",
        "mac_address",
        "has_primary_ip",
    ]
    q = forms.CharField(required=False, label="Search")
    rack_group_id = DynamicModelMultipleChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        label="Rack group",
        query_params={"site": "$site"},
    )
    rack_id = DynamicModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        label="Rack",
        null_option="None",
        query_params={
            "site": "$site",
            "group_id": "$rack_group_id",
        },
    )
    role = DynamicModelMultipleChoiceField(queryset=DeviceRole.objects.all(), to_field_name="slug", required=False)
    manufacturer = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        to_field_name="slug",
        required=False,
        label="Manufacturer",
    )
    device_type_id = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label="Model",
        query_params={"manufacturer": "$manufacturer"},
    )
    platform = DynamicModelMultipleChoiceField(
        queryset=Platform.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
    )
    mac_address = forms.CharField(required=False, label="MAC address")
    has_primary_ip = forms.NullBooleanField(
        required=False,
        label="Has a primary IP",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    virtual_chassis_member = forms.NullBooleanField(
        required=False,
        label="Virtual chassis member",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    console_ports = forms.NullBooleanField(
        required=False,
        label="Has console ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    console_server_ports = forms.NullBooleanField(
        required=False,
        label="Has console server ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    power_ports = forms.NullBooleanField(
        required=False,
        label="Has power ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    power_outlets = forms.NullBooleanField(
        required=False,
        label="Has power outlets",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    interfaces = forms.NullBooleanField(
        required=False,
        label="Has interfaces",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    pass_through_ports = forms.NullBooleanField(
        required=False,
        label="Has pass-through ports",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)


#
# Device components
#


class ComponentCreateForm(ComponentForm):
    """
    Base form for the creation of device components (models subclassed from ComponentModel).
    """

    device = DynamicModelChoiceField(queryset=Device.objects.all())
    description = forms.CharField(max_length=100, required=False)


class DeviceBulkAddComponentForm(ComponentForm, CustomFieldModelBulkEditFormMixin):
    pk = forms.ModelMultipleChoiceField(queryset=Device.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=100, required=False)

    class Meta:
        nullable_fields = []


#
# Console ports
#


class ConsolePortFilterForm(DeviceComponentFilterForm):
    model = ConsolePort
    type = forms.MultipleChoiceField(choices=ConsolePortTypeChoices, required=False, widget=StaticSelect2Multiple())
    tag = TagFilterField(model)


class ConsolePortForm(NautobotModelForm):
    class Meta:
        model = ConsolePort
        fields = [
            "device",
            "name",
            "label",
            "type",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
        }


class ConsolePortCreateForm(ComponentCreateForm):
    type = forms.ChoiceField(
        choices=add_blank_choice(ConsolePortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "type",
        "description",
        "tags",
    )


class ConsolePortBulkCreateForm(form_from_model(ConsolePort, ["type"]), DeviceBulkAddComponentForm):
    field_order = ("name_pattern", "label_pattern", "type", "description", "tags")


class ConsolePortBulkEditForm(
    form_from_model(ConsolePort, ["label", "type", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=ConsolePort.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        nullable_fields = ["label", "description"]


class ConsolePortCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    type = CSVChoiceField(choices=ConsolePortTypeChoices, required=False, help_text="Port type")

    class Meta:
        model = ConsolePort
        fields = ConsolePort.csv_headers


#
# Console server ports
#


class ConsoleServerPortFilterForm(DeviceComponentFilterForm):
    model = ConsoleServerPort
    type = forms.MultipleChoiceField(choices=ConsolePortTypeChoices, required=False, widget=StaticSelect2Multiple())
    tag = TagFilterField(model)


class ConsoleServerPortForm(NautobotModelForm):
    class Meta:
        model = ConsoleServerPort
        fields = [
            "device",
            "name",
            "label",
            "type",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
        }


class ConsoleServerPortCreateForm(ComponentCreateForm):
    type = forms.ChoiceField(
        choices=add_blank_choice(ConsolePortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "type",
        "description",
        "tags",
    )


class ConsoleServerPortBulkCreateForm(form_from_model(ConsoleServerPort, ["type"]), DeviceBulkAddComponentForm):
    field_order = ("name_pattern", "label_pattern", "type", "description", "tags")


class ConsoleServerPortBulkEditForm(
    form_from_model(ConsoleServerPort, ["label", "type", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=ConsoleServerPort.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        nullable_fields = ["label", "description"]


class ConsoleServerPortCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    type = CSVChoiceField(choices=ConsolePortTypeChoices, required=False, help_text="Port type")

    class Meta:
        model = ConsoleServerPort
        fields = ConsoleServerPort.csv_headers


#
# Power ports
#


class PowerPortFilterForm(DeviceComponentFilterForm):
    model = PowerPort
    type = forms.MultipleChoiceField(choices=PowerPortTypeChoices, required=False, widget=StaticSelect2Multiple())
    tag = TagFilterField(model)


class PowerPortForm(NautobotModelForm):
    class Meta:
        model = PowerPort
        fields = [
            "device",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
        }


class PowerPortCreateForm(ComponentCreateForm):
    type = forms.ChoiceField(
        choices=add_blank_choice(PowerPortTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    maximum_draw = forms.IntegerField(min_value=1, required=False, help_text="Maximum draw in watts")
    allocated_draw = forms.IntegerField(min_value=1, required=False, help_text="Allocated draw in watts")
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "type",
        "maximum_draw",
        "allocated_draw",
        "description",
        "tags",
    )


class PowerPortBulkCreateForm(
    form_from_model(PowerPort, ["type", "maximum_draw", "allocated_draw"]),
    DeviceBulkAddComponentForm,
):
    field_order = (
        "name_pattern",
        "label_pattern",
        "type",
        "maximum_draw",
        "allocated_draw",
        "description",
        "tags",
    )


class PowerPortBulkEditForm(
    form_from_model(PowerPort, ["label", "type", "maximum_draw", "allocated_draw", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=PowerPort.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        nullable_fields = ["label", "description"]


class PowerPortCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    type = CSVChoiceField(choices=PowerPortTypeChoices, required=False, help_text="Port type")

    class Meta:
        model = PowerPort
        fields = PowerPort.csv_headers


#
# Power outlets
#


class PowerOutletFilterForm(DeviceComponentFilterForm):
    model = PowerOutlet
    type = forms.MultipleChoiceField(choices=PowerOutletTypeChoices, required=False, widget=StaticSelect2Multiple())
    tag = TagFilterField(model)


class PowerOutletForm(NautobotModelForm):
    power_port = forms.ModelChoiceField(queryset=PowerPort.objects.all(), required=False)

    class Meta:
        model = PowerOutlet
        fields = [
            "device",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit power_port choices to the local device
        if hasattr(self.instance, "device"):
            self.fields["power_port"].queryset = PowerPort.objects.filter(device=self.instance.device)


class PowerOutletCreateForm(ComponentCreateForm):
    type = forms.ChoiceField(
        choices=add_blank_choice(PowerOutletTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    power_port = forms.ModelChoiceField(queryset=PowerPort.objects.all(), required=False)
    feed_leg = forms.ChoiceField(choices=add_blank_choice(PowerOutletFeedLegChoices), required=False)
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "type",
        "power_port",
        "feed_leg",
        "description",
        "tags",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit power_port queryset to PowerPorts which belong to the parent Device
        device = Device.objects.get(pk=self.initial.get("device") or self.data.get("device"))
        self.fields["power_port"].queryset = PowerPort.objects.filter(device=device)


class PowerOutletBulkCreateForm(form_from_model(PowerOutlet, ["type", "feed_leg"]), DeviceBulkAddComponentForm):
    field_order = (
        "name_pattern",
        "label_pattern",
        "type",
        "feed_leg",
        "description",
        "tags",
    )


class PowerOutletBulkEditForm(
    form_from_model(PowerOutlet, ["label", "type", "feed_leg", "power_port", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=PowerOutlet.objects.all(), widget=forms.MultipleHiddenInput())
    device = forms.ModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        disabled=True,
        widget=forms.HiddenInput(),
    )

    class Meta:
        nullable_fields = ["label", "type", "feed_leg", "power_port", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit power_port queryset to PowerPorts which belong to the parent Device
        if "device" in self.initial:
            device = Device.objects.filter(pk=self.initial["device"]).first()
            self.fields["power_port"].queryset = PowerPort.objects.filter(device=device)
        else:
            self.fields["power_port"].choices = ()
            self.fields["power_port"].widget.attrs["disabled"] = True


class PowerOutletCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    type = CSVChoiceField(choices=PowerOutletTypeChoices, required=False, help_text="Outlet type")
    power_port = CSVModelChoiceField(
        queryset=PowerPort.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Local power port which feeds this outlet",
    )
    feed_leg = CSVChoiceField(
        choices=PowerOutletFeedLegChoices,
        required=False,
        help_text="Electrical phase (for three-phase circuits)",
    )

    class Meta:
        model = PowerOutlet
        fields = PowerOutlet.csv_headers

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit PowerPort choices to those belonging to this device (or VC master)
        if self.is_bound:
            try:
                device = self.fields["device"].to_python(self.data["device"])
            except forms.ValidationError:
                device = None
        else:
            try:
                device = self.instance.device
            except Device.DoesNotExist:
                device = None

        if device:
            self.fields["power_port"].queryset = PowerPort.objects.filter(device__in=[device, device.get_vc_master()])
        else:
            self.fields["power_port"].queryset = PowerPort.objects.none()


#
# Interfaces
#


class InterfaceFilterForm(DeviceComponentFilterForm, StatusModelFilterFormMixin):
    model = Interface
    type = forms.MultipleChoiceField(choices=InterfaceTypeChoices, required=False, widget=StaticSelect2Multiple())
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    mgmt_only = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    mac_address = forms.CharField(required=False, label="MAC address")
    tag = TagFilterField(model)


class InterfaceForm(NautobotModelForm, InterfaceCommonForm):
    parent_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        label="Parent interface",
        query_params={
            "kind": "physical",
        },
        help_text="Assigned parent interface",
    )
    bridge = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        label="Bridge interface",
        help_text="Assigned bridge interface",
    )
    lag = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        label="LAG interface",
        query_params={
            "type": InterfaceTypeChoices.TYPE_LAG,
        },
        help_text="Assigned LAG interface",
    )
    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="Untagged VLAN",
        brief_mode=False,
        query_params={
            "site_id": "null",
        },
    )
    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="Tagged VLANs",
        brief_mode=False,
        query_params={
            "site_id": "null",
        },
    )

    class Meta:
        model = Interface
        fields = [
            "device",
            "name",
            "label",
            "type",
            "enabled",
            "parent_interface",
            "bridge",
            "lag",
            "mac_address",
            "mtu",
            "mgmt_only",
            "description",
            "mode",
            "untagged_vlan",
            "tagged_vlans",
            "tags",
            "status",
        ]
        widgets = {
            "device": forms.HiddenInput(),
            "type": StaticSelect2(),
            "mode": StaticSelect2(),
        }
        labels = {
            "mode": "802.1Q Mode",
        }
        help_texts = {
            "mode": INTERFACE_MODE_HELP_TEXT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.is_bound:
            device = Device.objects.get(pk=self.data["device"])
        else:
            device = self.instance.device

        # Restrict parent/bridge/LAG interface assignment by device
        self.fields["parent_interface"].widget.add_query_param("device_with_common_vc", device.pk)
        self.fields["bridge"].widget.add_query_param("device_with_common_vc", device.pk)
        self.fields["lag"].widget.add_query_param("device_with_common_vc", device.pk)

        # Add current site to VLANs query params
        self.fields["untagged_vlan"].widget.add_query_param("site_id", device.site.pk)
        self.fields["tagged_vlans"].widget.add_query_param("site_id", device.site.pk)


class InterfaceCreateForm(ComponentCreateForm, InterfaceCommonForm):
    type = forms.ChoiceField(
        choices=InterfaceTypeChoices,
        widget=StaticSelect2(),
    )
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={
            "content_types": Interface._meta.label_lower,
        },
    )
    enabled = forms.BooleanField(required=False, initial=True)
    parent_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            "device_with_common_vc": "$device",
            "kind": "physical",
        },
        help_text="Assigned parent interface",
    )
    bridge = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            "device_with_common_vc": "$device",
        },
        help_text="Assigned bridge interface",
    )
    lag = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            "device_with_common_vc": "$device",
            "type": InterfaceTypeChoices.TYPE_LAG,
        },
        help_text="Assigned LAG interface",
    )
    mtu = forms.IntegerField(
        required=False,
        min_value=INTERFACE_MTU_MIN,
        max_value=INTERFACE_MTU_MAX,
        label="MTU",
    )
    mac_address = forms.CharField(required=False, label="MAC Address")
    mgmt_only = forms.BooleanField(
        required=False,
        label="Management only",
        help_text="This interface is used only for out-of-band management",
    )
    mode = forms.ChoiceField(
        choices=add_blank_choice(InterfaceModeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        brief_mode=False,
        query_params={
            "available_on_device": "$device",
        },
    )
    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        brief_mode=False,
        query_params={"available_on_device": "$device"},
    )
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "status",
        "type",
        "enabled",
        "parent_interface",
        "bridge",
        "lag",
        "mtu",
        "mac_address",
        "description",
        "mgmt_only",
        "mode",
        "untagged_vlan",
        "tagged_vlans",
        "tags",
    )


class InterfaceBulkCreateForm(
    form_from_model(Interface, ["type", "enabled", "mtu", "mgmt_only"]),
    DeviceBulkAddComponentForm,
):
    field_order = (
        "name_pattern",
        "label_pattern",
        "type",
        "enabled",
        "mtu",
        "mgmt_only",
        "description",
        "tags",
    )


class InterfaceBulkEditForm(
    form_from_model(
        Interface, ["label", "type", "parent_interface", "bridge", "lag", "mac_address", "mtu", "description", "mode"]
    ),
    TagsBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Interface.objects.all(), widget=forms.MultipleHiddenInput())
    device = forms.ModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        disabled=True,
        widget=forms.HiddenInput(),
    )
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    parent_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            "kind": "physical",
        },
    )
    bridge = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
    )
    lag = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            "type": InterfaceTypeChoices.TYPE_LAG,
        },
    )
    mgmt_only = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Management only")
    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        brief_mode=False,
        query_params={
            "site_id": "null",
        },
    )
    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        brief_mode=False,
        query_params={
            "site_id": "null",
        },
    )

    class Meta:
        nullable_fields = [
            "label",
            "parent_interface",
            "bridge",
            "lag",
            "mac_address",
            "mtu",
            "description",
            "mode",
            "untagged_vlan",
            "tagged_vlans",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit LAG choices to interfaces which belong to the parent device (or VC master)
        if "device" in self.initial:
            device = Device.objects.filter(pk=self.initial["device"]).first()

            # Restrict parent/bridge/LAG interface assignment by device
            self.fields["parent_interface"].widget.add_query_param("device_with_common_vc", device.pk)
            self.fields["bridge"].widget.add_query_param("device_with_common_vc", device.pk)
            self.fields["lag"].widget.add_query_param("device_with_common_vc", device.pk)

            # Add current site to VLANs query params
            self.fields["untagged_vlan"].widget.add_query_param("site_id", device.site.pk)
            self.fields["tagged_vlans"].widget.add_query_param("site_id", device.site.pk)
        else:
            # See netbox-community/netbox#4523
            if "pk" in self.initial:
                site = None
                interfaces = Interface.objects.filter(pk__in=self.initial["pk"]).prefetch_related("device__site")

                # Check interface sites.  First interface should set site, further interfaces will either continue the
                # loop or reset back to no site and break the loop.
                for interface in interfaces:
                    if site is None:
                        site = interface.device.site
                    elif interface.device.site is not site:
                        site = None
                        break

                if site is not None:
                    self.fields["untagged_vlan"].widget.add_query_param("site_id", site.pk)
                    self.fields["tagged_vlans"].widget.add_query_param("site_id", site.pk)

            self.fields["parent_interface"].choices = ()
            self.fields["parent_interface"].widget.attrs["disabled"] = True
            self.fields["bridge"].choices = ()
            self.fields["bridge"].widget.attrs["disabled"] = True
            self.fields["lag"].choices = ()
            self.fields["lag"].widget.attrs["disabled"] = True

    def clean(self):
        super().clean()

        # Untagged interfaces cannot be assigned tagged VLANs
        if self.cleaned_data["mode"] == InterfaceModeChoices.MODE_ACCESS and self.cleaned_data["tagged_vlans"]:
            raise forms.ValidationError({"mode": "An access interface cannot have tagged VLANs assigned."})

        # Remove all tagged VLAN assignments from "tagged all" interfaces
        elif self.cleaned_data["mode"] == InterfaceModeChoices.MODE_TAGGED_ALL:
            self.cleaned_data["tagged_vlans"] = []


class InterfaceCSVForm(CustomFieldModelCSVForm, StatusModelCSVFormMixin):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    parent_interface = CSVModelChoiceField(
        queryset=Interface.objects.all(), required=False, to_field_name="name", help_text="Parent interface"
    )
    bridge = CSVModelChoiceField(
        queryset=Interface.objects.all(), required=False, to_field_name="name", help_text="Bridge interface"
    )
    lag = CSVModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Parent LAG interface",
    )
    type = CSVChoiceField(choices=InterfaceTypeChoices, help_text="Physical medium")
    mode = CSVChoiceField(
        choices=InterfaceModeChoices,
        required=False,
        help_text="IEEE 802.1Q operational mode (for L2 interfaces)",
    )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:
            # Limit choices for parent, bridge, and LAG interfaces to the assigned device (or VC)
            device_name = data.get("device")
            if device_name is not None:
                device = Device.objects.filter(name=device_name).first()

                filter_by = Q(device=device)

                if device and device.virtual_chassis:
                    filter_by |= Q(device__virtual_chassis=device.virtual_chassis)

                self.fields["parent_interface"].queryset = (
                    self.fields["parent_interface"]
                    .queryset.filter(Q(filter_by))
                    .exclude(type__in=NONCONNECTABLE_IFACE_TYPES)
                )
                self.fields["bridge"].queryset = self.fields["bridge"].queryset.filter(filter_by)

                filter_by &= Q(type=InterfaceTypeChoices.TYPE_LAG)
                self.fields["lag"].queryset = self.fields["lag"].queryset.filter(filter_by)
            else:
                self.fields["parent_interface"].queryset = self.fields["parent_interface"].queryset.none()
                self.fields["bridge"].queryset = self.fields["bridge"].queryset.none()
                self.fields["lag"].queryset = self.fields["lag"].queryset.none()

    class Meta:
        model = Interface
        fields = Interface.csv_headers

    def clean_enabled(self):
        # Make sure enabled is True when it's not included in the uploaded data
        if "enabled" not in self.data:
            return True
        else:
            return self.cleaned_data["enabled"]


#
# Front pass-through ports
#


class FrontPortFilterForm(DeviceComponentFilterForm):
    model = FrontPort
    type = forms.MultipleChoiceField(choices=PortTypeChoices, required=False, widget=StaticSelect2Multiple())
    tag = TagFilterField(model)


class FrontPortForm(NautobotModelForm):
    class Meta:
        model = FrontPort
        fields = [
            "device",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
            "type": StaticSelect2(),
            "rear_port": StaticSelect2(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit RearPort choices to the local device
        if hasattr(self.instance, "device"):
            self.fields["rear_port"].queryset = self.fields["rear_port"].queryset.filter(device=self.instance.device)


# TODO: Merge with FrontPortTemplateCreateForm to remove duplicate logic
class FrontPortCreateForm(ComponentCreateForm):
    type = forms.ChoiceField(
        choices=PortTypeChoices,
        widget=StaticSelect2(),
    )
    rear_port_set = forms.MultipleChoiceField(
        choices=[],
        label="Rear ports",
        help_text="Select one rear port assignment for each front port being created.",
    )
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "type",
        "rear_port_set",
        "description",
        "tags",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        device = Device.objects.get(pk=self.initial.get("device") or self.data.get("device"))

        # Determine which rear port positions are occupied. These will be excluded from the list of available
        # mappings.
        occupied_port_positions = [
            (front_port.rear_port_id, front_port.rear_port_position) for front_port in device.frontports.all()
        ]

        # Populate rear port choices
        choices = []
        rear_ports = RearPort.objects.filter(device=device)
        for rear_port in rear_ports:
            for i in range(1, rear_port.positions + 1):
                if (rear_port.pk, i) not in occupied_port_positions:
                    choices.append(
                        (
                            f"{rear_port.pk}:{i}",
                            f"{rear_port.name}:{i}",
                        )
                    )
        self.fields["rear_port_set"].choices = choices

    def clean(self):
        super().clean()

        # Validate that the number of ports being created equals the number of selected (rear port, position) tuples
        front_port_count = len(self.cleaned_data["name_pattern"])
        rear_port_count = len(self.cleaned_data["rear_port_set"])
        if front_port_count != rear_port_count:
            raise forms.ValidationError(
                {
                    "rear_port_set": (
                        f"The provided name pattern will create {front_port_count} ports, "
                        f"however {rear_port_count} rear port assignments were selected. These counts must match."
                    )
                }
            )

    def get_iterative_data(self, iteration):

        # Assign rear port and position from selected set
        rear_port, position = self.cleaned_data["rear_port_set"][iteration].split(":")

        return {
            "rear_port": rear_port,
            "rear_port_position": int(position),
        }


# class FrontPortBulkCreateForm(
#     form_from_model(FrontPort, ['label', 'type', 'description', 'tags']),
#     DeviceBulkAddComponentForm
# ):
#     pass


class FrontPortBulkEditForm(
    form_from_model(FrontPort, ["label", "type", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=FrontPort.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        nullable_fields = ["label", "description"]


class FrontPortCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    rear_port = CSVModelChoiceField(
        queryset=RearPort.objects.all(),
        to_field_name="name",
        help_text="Corresponding rear port",
    )
    type = CSVChoiceField(choices=PortTypeChoices, help_text="Physical medium classification")

    class Meta:
        model = FrontPort
        fields = FrontPort.csv_headers
        help_texts = {
            "rear_port_position": "Mapped position on corresponding rear port",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit RearPort choices to those belonging to this device (or VC master)
        if self.is_bound:
            try:
                device = self.fields["device"].to_python(self.data["device"])
            except forms.ValidationError:
                device = None
        else:
            try:
                device = self.instance.device
            except Device.DoesNotExist:
                device = None

        if device:
            self.fields["rear_port"].queryset = RearPort.objects.filter(device__in=[device, device.get_vc_master()])
        else:
            self.fields["rear_port"].queryset = RearPort.objects.none()


#
# Rear pass-through ports
#


class RearPortFilterForm(DeviceComponentFilterForm):
    model = RearPort
    type = forms.MultipleChoiceField(choices=PortTypeChoices, required=False, widget=StaticSelect2Multiple())
    tag = TagFilterField(model)


class RearPortForm(NautobotModelForm):
    class Meta:
        model = RearPort
        fields = [
            "device",
            "name",
            "label",
            "type",
            "positions",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
            "type": StaticSelect2(),
        }


class RearPortCreateForm(ComponentCreateForm):
    type = forms.ChoiceField(
        choices=PortTypeChoices,
        widget=StaticSelect2(),
    )
    positions = forms.IntegerField(
        min_value=REARPORT_POSITIONS_MIN,
        max_value=REARPORT_POSITIONS_MAX,
        initial=1,
        help_text="The number of front ports which may be mapped to each rear port",
    )
    field_order = (
        "device",
        "name_pattern",
        "label_pattern",
        "type",
        "positions",
        "description",
        "tags",
    )


class RearPortBulkCreateForm(form_from_model(RearPort, ["type", "positions"]), DeviceBulkAddComponentForm):
    field_order = (
        "name_pattern",
        "label_pattern",
        "type",
        "positions",
        "description",
        "tags",
    )


class RearPortBulkEditForm(
    form_from_model(RearPort, ["label", "type", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=RearPort.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        nullable_fields = ["label", "description"]


class RearPortCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    type = CSVChoiceField(
        help_text="Physical medium classification",
        choices=PortTypeChoices,
    )

    class Meta:
        model = RearPort
        fields = RearPort.csv_headers
        help_texts = {"positions": "Number of front ports which may be mapped"}


#
# Device bays
#


class DeviceBayFilterForm(DeviceComponentFilterForm):
    model = DeviceBay
    tag = TagFilterField(model)


class DeviceBayForm(NautobotModelForm):
    class Meta:
        model = DeviceBay
        fields = [
            "device",
            "name",
            "label",
            "description",
            "tags",
        ]
        widgets = {
            "device": forms.HiddenInput(),
        }


class DeviceBayCreateForm(ComponentCreateForm):
    field_order = ("device", "name_pattern", "label_pattern", "description", "tags")


class PopulateDeviceBayForm(BootstrapMixin, forms.Form):
    installed_device = forms.ModelChoiceField(
        queryset=Device.objects.all(),
        label="Child Device",
        help_text="Child devices must first be created and assigned to the site/rack of the parent device.",
        widget=StaticSelect2(),
    )

    def __init__(self, device_bay, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["installed_device"].queryset = Device.objects.filter(
            site=device_bay.device.site,
            rack=device_bay.device.rack,
            parent_bay__isnull=True,
            device_type__u_height=0,
            device_type__subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        ).exclude(pk=device_bay.device.pk)


class DeviceBayBulkCreateForm(DeviceBulkAddComponentForm):
    field_order = ("name_pattern", "label_pattern", "description", "tags")


class DeviceBayBulkEditForm(
    form_from_model(DeviceBay, ["label", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=DeviceBay.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        nullable_fields = ["label", "description"]


class DeviceBayCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    installed_device = CSVModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Child device installed within this bay",
        error_messages={
            "invalid_choice": "Child device not found.",
        },
    )

    class Meta:
        model = DeviceBay
        fields = DeviceBay.csv_headers

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit installed device choices to devices of the correct type and location
        if self.is_bound:
            try:
                device = self.fields["device"].to_python(self.data["device"])
            except forms.ValidationError:
                device = None
        else:
            try:
                device = self.instance.device
            except Device.DoesNotExist:
                device = None

        if device:
            self.fields["installed_device"].queryset = Device.objects.filter(
                site=device.site,
                rack=device.rack,
                parent_bay__isnull=True,
                device_type__u_height=0,
                device_type__subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
            ).exclude(pk=device.pk)
        else:
            self.fields["installed_device"].queryset = Interface.objects.none()


#
# Inventory items
#


class InventoryItemForm(NautobotModelForm):
    device = DynamicModelChoiceField(queryset=Device.objects.all())
    parent = DynamicModelChoiceField(
        queryset=InventoryItem.objects.all(),
        required=False,
        query_params={"device_id": "$device"},
    )
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)

    class Meta:
        model = InventoryItem
        fields = [
            "device",
            "parent",
            "name",
            "label",
            "manufacturer",
            "part_id",
            "serial",
            "asset_tag",
            "description",
            "tags",
        ]


class InventoryItemCreateForm(ComponentCreateForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    parent = DynamicModelChoiceField(
        queryset=InventoryItem.objects.all(),
        required=False,
        query_params={"device_id": "$device"},
    )
    part_id = forms.CharField(max_length=50, required=False, label="Part ID")
    serial = forms.CharField(
        max_length=255,
        required=False,
    )
    asset_tag = forms.CharField(
        max_length=50,
        required=False,
    )
    field_order = (
        "device",
        "parent",
        "name_pattern",
        "label_pattern",
        "manufacturer",
        "part_id",
        "serial",
        "asset_tag",
        "description",
        "tags",
    )


class InventoryItemCSVForm(CustomFieldModelCSVForm):
    device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name")
    manufacturer = CSVModelChoiceField(queryset=Manufacturer.objects.all(), to_field_name="name", required=False)

    class Meta:
        model = InventoryItem
        fields = InventoryItem.csv_headers


class InventoryItemBulkCreateForm(
    form_from_model(InventoryItem, ["manufacturer", "part_id", "serial", "asset_tag", "discovered"]),
    DeviceBulkAddComponentForm,
):
    field_order = (
        "name_pattern",
        "label_pattern",
        "manufacturer",
        "part_id",
        "serial",
        "asset_tag",
        "discovered",
        "description",
        "tags",
    )


class InventoryItemBulkEditForm(
    form_from_model(InventoryItem, ["label", "manufacturer", "part_id", "description"]),
    TagsBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=InventoryItem.objects.all(), widget=forms.MultipleHiddenInput())
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)

    class Meta:
        nullable_fields = ["label", "manufacturer", "part_id", "description"]


class InventoryItemFilterForm(DeviceComponentFilterForm):
    model = InventoryItem
    manufacturer = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(), to_field_name="slug", required=False
    )
    serial = forms.CharField(required=False)
    asset_tag = forms.CharField(required=False)
    discovered = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    tag = TagFilterField(model)


#
# Cables
#


class ConnectCableToDeviceForm(ConnectCableExcludeIDMixin, NautobotModelForm):
    """
    Base form for connecting a Cable to a Device component
    """

    termination_b_region = DynamicModelChoiceField(queryset=Region.objects.all(), label="Region", required=False)
    termination_b_site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label="Site",
        required=False,
        query_params={"region_id": "$termination_b_region"},
    )
    termination_b_rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        label="Rack",
        required=False,
        null_option="None",
        query_params={"site_id": "$termination_b_site"},
    )
    termination_b_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="Device",
        required=False,
        query_params={
            "site_id": "$termination_b_site",
            "rack_id": "$termination_b_rack",
        },
    )

    class Meta:
        model = Cable
        fields = [
            "termination_b_region",
            "termination_b_site",
            "termination_b_rack",
            "termination_b_device",
            "termination_b_id",
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
            "tags",
        ]
        widgets = {
            "type": StaticSelect2,
            "length_unit": StaticSelect2,
        }
        help_texts = {
            "status": "Connection status",
        }

    def clean_termination_b_id(self):
        # Return the PK rather than the object
        return getattr(self.cleaned_data["termination_b_id"], "pk", None)


class ConnectCableToConsolePortForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=ConsolePort.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"device_id": "$termination_b_device"},
    )


class ConnectCableToConsoleServerPortForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=ConsoleServerPort.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"device_id": "$termination_b_device"},
    )


class ConnectCableToPowerPortForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=PowerPort.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"device_id": "$termination_b_device"},
    )


class ConnectCableToPowerOutletForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=PowerOutlet.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"device_id": "$termination_b_device"},
    )


class ConnectCableToInterfaceForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={
            "device_id": "$termination_b_device",
            "kind": "physical",
        },
    )


class ConnectCableToFrontPortForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=FrontPort.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"device_id": "$termination_b_device"},
    )


class ConnectCableToRearPortForm(ConnectCableToDeviceForm):
    termination_b_id = DynamicModelChoiceField(
        queryset=RearPort.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"device_id": "$termination_b_device"},
    )


class ConnectCableToCircuitTerminationForm(ConnectCableExcludeIDMixin, NautobotModelForm):
    termination_b_provider = DynamicModelChoiceField(queryset=Provider.objects.all(), label="Provider", required=False)
    termination_b_region = DynamicModelChoiceField(queryset=Region.objects.all(), label="Region", required=False)
    termination_b_site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label="Site",
        required=False,
        query_params={"region_id": "$termination_b_region"},
    )
    termination_b_circuit = DynamicModelChoiceField(
        queryset=Circuit.objects.all(),
        label="Circuit",
        query_params={
            "provider_id": "$termination_b_provider",
            "site_id": "$termination_b_site",
        },
    )
    termination_b_id = DynamicModelChoiceField(
        queryset=CircuitTermination.objects.all(),
        label="Side",
        disabled_indicator="cable",
        query_params={"circuit_id": "$termination_b_circuit"},
    )

    class Meta:
        model = Cable
        fields = [
            "termination_b_provider",
            "termination_b_region",
            "termination_b_site",
            "termination_b_circuit",
            "termination_b_id",
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
            "tags",
        ]

    def clean_termination_b_id(self):
        # Return the PK rather than the object
        return getattr(self.cleaned_data["termination_b_id"], "pk", None)


class ConnectCableToPowerFeedForm(ConnectCableExcludeIDMixin, NautobotModelForm):
    termination_b_region = DynamicModelChoiceField(queryset=Region.objects.all(), label="Region", required=False)
    termination_b_site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label="Site",
        required=False,
        query_params={"region_id": "$termination_b_region"},
    )
    termination_b_rackgroup = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        label="Rack Group",
        required=False,
        query_params={"site_id": "$termination_b_site"},
    )
    termination_b_powerpanel = DynamicModelChoiceField(
        queryset=PowerPanel.objects.all(),
        label="Power Panel",
        required=False,
        query_params={
            "site_id": "$termination_b_site",
            "rack_group_id": "$termination_b_rackgroup",
        },
    )
    termination_b_id = DynamicModelChoiceField(
        queryset=PowerFeed.objects.all(),
        label="Name",
        disabled_indicator="cable",
        query_params={"power_panel_id": "$termination_b_powerpanel"},
    )

    class Meta:
        model = Cable
        fields = [
            "termination_b_rackgroup",
            "termination_b_powerpanel",
            "termination_b_id",
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
            "tags",
        ]

    def clean_termination_b_id(self):
        # Return the PK rather than the object
        return getattr(self.cleaned_data["termination_b_id"], "pk", None)


class CableForm(NautobotModelForm):
    class Meta:
        model = Cable
        fields = [
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
            "tags",
        ]
        widgets = {
            "type": StaticSelect2,
            "length_unit": StaticSelect2,
        }
        error_messages = {"length": {"max_value": "Maximum length is 32767 (any unit)"}}


class CableCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    # Termination A
    side_a_device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name", help_text="Side A device")
    side_a_type = CSVContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=CABLE_TERMINATION_MODELS,
        help_text="Side A type",
    )
    side_a_name = forms.CharField(help_text="Side A component name")

    # Termination B
    side_b_device = CSVModelChoiceField(queryset=Device.objects.all(), to_field_name="name", help_text="Side B device")
    side_b_type = CSVContentTypeField(
        queryset=ContentType.objects.all(),
        limit_choices_to=CABLE_TERMINATION_MODELS,
        help_text="Side B type",
    )
    side_b_name = forms.CharField(help_text="Side B component name")

    # Cable attributes
    type = CSVChoiceField(
        choices=CableTypeChoices,
        required=False,
        help_text="Physical medium classification",
    )
    length_unit = CSVChoiceField(choices=CableLengthUnitChoices, required=False, help_text="Length unit")

    class Meta:
        model = Cable
        fields = [
            "side_a_device",
            "side_a_type",
            "side_a_name",
            "side_b_device",
            "side_b_type",
            "side_b_name",
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
        ]
        help_texts = {
            "color": mark_safe("RGB color in hexadecimal (e.g. <code>00ff00</code>)"),
            "status": "Connection status",
        }

    def _clean_side(self, side):
        """
        Derive a Cable's A/B termination objects.

        :param side: 'a' or 'b'
        """
        assert side in "ab", f"Invalid side designation: {side}"

        device = self.cleaned_data.get(f"side_{side}_device")
        content_type = self.cleaned_data.get(f"side_{side}_type")
        name = self.cleaned_data.get(f"side_{side}_name")
        if not device or not content_type or not name:
            return None

        model = content_type.model_class()
        try:
            termination_object = model.objects.get(device=device, name=name)
            if termination_object.cable is not None:
                raise forms.ValidationError(f"Side {side.upper()}: {device} {termination_object} is already connected")
        except ObjectDoesNotExist:
            raise forms.ValidationError(f"{side.upper()} side termination not found: {device} {name}")

        setattr(self.instance, f"termination_{side}", termination_object)
        return termination_object

    def clean_side_a_name(self):
        return self._clean_side("a")

    def clean_side_b_name(self):
        return self._clean_side("b")

    def clean_length_unit(self):
        # Avoid trying to save as NULL
        length_unit = self.cleaned_data.get("length_unit", None)
        return length_unit if length_unit is not None else ""

    def add_error(self, field, error):
        # Edge Case: some fields in error are not properties in this instance
        #   e.g: termination_a_id not an property in CableCSVForm, This would raise a ValueError Exception
        # Solution: convert those fields to its equivalent in CableCSVForm
        #   e.g: termination_a_id > side_a_name

        final_error = error
        if hasattr(error, "error_dict"):
            error_dict = error.error_dict
            termination_keys = [key for key in error_dict.keys() if key.startswith("termination")]
            for error_field in termination_keys:
                side_value = error_field.split("_")[1]
                error_msg = error_dict.pop(error_field)
                error_dict[f"side_{side_value}_name"] = error_msg

            final_error = ValidationError(error_dict)
        super().add_error(field, final_error)


class CableBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Cable.objects.all(), widget=forms.MultipleHiddenInput)
    type = forms.ChoiceField(
        choices=add_blank_choice(CableTypeChoices),
        required=False,
        initial="",
        widget=StaticSelect2(),
    )
    label = forms.CharField(max_length=100, required=False)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())  # RGB color code
    length = forms.IntegerField(min_value=1, required=False)
    length_unit = forms.ChoiceField(
        choices=add_blank_choice(CableLengthUnitChoices),
        required=False,
        initial="",
        widget=StaticSelect2(),
    )

    class Meta:
        nullable_fields = [
            "type",
            "status",
            "label",
            "color",
            "length",
        ]

    def clean(self):
        super().clean()

        # Validate length/unit
        length = self.cleaned_data.get("length")
        length_unit = self.cleaned_data.get("length_unit")
        if length and not length_unit:
            raise forms.ValidationError({"length_unit": "Must specify a unit when setting length"})


class CableFilterForm(BootstrapMixin, StatusModelFilterFormMixin, forms.Form):
    model = Cable
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    tenant = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), to_field_name="slug", required=False)
    rack_id = DynamicModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        label="Rack",
        null_option="None",
        query_params={"site": "$site"},
    )
    type = forms.MultipleChoiceField(
        choices=add_blank_choice(CableTypeChoices),
        required=False,
        widget=StaticSelect2Multiple(),
    )
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())  # RGB color code
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
        query_params={
            "site": "$site",
            "tenant": "$tenant",
            "rack_id": "$rack_id",
        },
    )
    tag = TagFilterField(model)


#
# Connections
#


class ConsoleConnectionFilterForm(BootstrapMixin, forms.Form):
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
        query_params={"site": "$site"},
    )


class PowerConnectionFilterForm(BootstrapMixin, forms.Form):
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
        query_params={"site": "$site"},
    )


class InterfaceConnectionFilterForm(BootstrapMixin, forms.Form):
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    device_id = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
        query_params={"site": "$site"},
    )


#
# Virtual chassis
#


class DeviceSelectionForm(forms.Form):
    pk = forms.ModelMultipleChoiceField(queryset=Device.objects.all(), widget=forms.MultipleHiddenInput())


class VirtualChassisCreateForm(NautobotModelForm):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, initial_params={"sites": "$site"})
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={"region_id": "$region"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        null_option="None",
        query_params={"site_id": "$site"},
    )
    members = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        query_params={
            "site_id": "$site",
            "rack_id": "$rack",
        },
    )
    initial_position = forms.IntegerField(
        initial=1,
        required=False,
        help_text="Position of the first member device. Increases by one for each additional member.",
    )

    class Meta:
        model = VirtualChassis
        fields = [
            "name",
            "domain",
            "region",
            "site",
            "rack",
            "members",
            "initial_position",
            "tags",
        ]

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # Assign VC members
        if instance.present_in_database:
            initial_position = self.cleaned_data.get("initial_position") or 1
            for i, member in enumerate(self.cleaned_data["members"], start=initial_position):
                member.virtual_chassis = instance
                member.vc_position = i
                member.save()

        return instance


class VirtualChassisForm(NautobotModelForm):
    master = forms.ModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )

    class Meta:
        model = VirtualChassis
        fields = [
            "name",
            "domain",
            "master",
            "tags",
        ]
        widgets = {
            "master": SelectWithPK(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["master"].queryset = Device.objects.filter(virtual_chassis=self.instance)


class BaseVCMemberFormSet(forms.BaseModelFormSet):
    def clean(self):
        super().clean()

        # Check for duplicate VC position values
        vc_position_list = []
        for form in self.forms:
            vc_position = form.cleaned_data.get("vc_position")
            if vc_position:
                if vc_position in vc_position_list:
                    error_msg = f"A virtual chassis member already exists in position {vc_position}."
                    form.add_error("vc_position", error_msg)
                vc_position_list.append(vc_position)


class DeviceVCMembershipForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "vc_position",
            "vc_priority",
        ]
        labels = {
            "vc_position": "Position",
            "vc_priority": "Priority",
        }

    def __init__(self, validate_vc_position=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Require VC position (only required when the Device is a VirtualChassis member)
        self.fields["vc_position"].required = True

        # Validation of vc_position is optional. This is only required when adding a new member to an existing
        # VirtualChassis. Otherwise, vc_position validation is handled by BaseVCMemberFormSet.
        self.validate_vc_position = validate_vc_position

    def clean_vc_position(self):
        vc_position = self.cleaned_data["vc_position"]

        if self.validate_vc_position:
            conflicting_members = Device.objects.filter(
                virtual_chassis=self.instance.virtual_chassis, vc_position=vc_position
            )
            if conflicting_members.exists():
                raise forms.ValidationError(f"A virtual chassis member already exists in position {vc_position}.")

        return vc_position


class VCMemberSelectForm(BootstrapMixin, forms.Form):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, initial_params={"sites": "$site"})
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={"region_id": "$region"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        null_option="None",
        query_params={"site_id": "$site"},
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        query_params={
            "site_id": "$site",
            "rack_id": "$rack",
            "virtual_chassis_id": "null",
        },
    )

    def clean_device(self):
        device = self.cleaned_data["device"]
        if device.virtual_chassis is not None:
            raise forms.ValidationError(f"Device {device} is already assigned to a virtual chassis.")
        return device


class VirtualChassisBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=VirtualChassis.objects.all(), widget=forms.MultipleHiddenInput())
    domain = forms.CharField(max_length=30, required=False)

    class Meta:
        nullable_fields = ["domain"]


class VirtualChassisCSVForm(CustomFieldModelCSVForm):
    master = CSVModelChoiceField(
        queryset=Device.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Master device",
    )

    class Meta:
        model = VirtualChassis
        fields = VirtualChassis.csv_headers


class VirtualChassisFilterForm(NautobotFilterForm):
    model = VirtualChassis
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    tenant_group = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
    )
    tenant = DynamicModelMultipleChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
        query_params={"group": "$tenant_group"},
    )
    tag = TagFilterField(model)


#
# Power panels
#


class PowerPanelForm(LocatableModelFormMixin, NautobotModelForm):
    rack_group = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )

    class Meta:
        model = PowerPanel
        fields = [
            "region",
            "site",
            "location",
            "rack_group",
            "name",
            "tags",
        ]


class PowerPanelCSVForm(LocatableModelCSVFormMixin, CustomFieldModelCSVForm):
    rack_group = CSVModelChoiceField(queryset=RackGroup.objects.all(), required=False, to_field_name="name")

    class Meta:
        model = PowerPanel
        fields = PowerPanel.csv_headers

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit group queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get("site")}
            self.fields["rack_group"].queryset = self.fields["rack_group"].queryset.filter(**params)


class PowerPanelBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=PowerPanel.objects.all(), widget=forms.MultipleHiddenInput)
    rack_group = DynamicModelChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )

    class Meta:
        model = PowerPanel
        nullable_fields = ["location", "rack_group"]


class PowerPanelFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin):
    model = PowerPanel
    q = forms.CharField(required=False, label="Search")
    rack_group_id = DynamicModelMultipleChoiceField(
        queryset=RackGroup.objects.all(),
        required=False,
        label="Rack group (ID)",
        null_option="None",
        query_params={"site": "$site"},
    )
    tag = TagFilterField(model)


#
# Power feeds
#


class PowerFeedForm(NautobotModelForm):
    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        initial_params={"sites__powerpanel": "$power_panel"},
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        initial_params={"powerpanel": "$power_panel"},
        query_params={"region_id": "$region"},
    )
    power_panel = DynamicModelChoiceField(queryset=PowerPanel.objects.all(), query_params={"site_id": "$site"})
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        query_params={"site_id": "$site"},
    )
    comments = CommentField()

    class Meta:
        model = PowerFeed
        fields = [
            "region",
            "site",
            "power_panel",
            "rack",
            "name",
            "status",
            "type",
            "supply",
            "phase",
            "voltage",
            "amperage",
            "max_utilization",
            "comments",
            "tags",
        ]
        widgets = {
            "type": StaticSelect2(),
            "supply": StaticSelect2(),
            "phase": StaticSelect2(),
        }


class PowerFeedCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    site = CSVModelChoiceField(queryset=Site.objects.all(), to_field_name="name", help_text="Assigned site")
    power_panel = CSVModelChoiceField(
        queryset=PowerPanel.objects.all(),
        to_field_name="name",
        help_text="Upstream power panel",
    )
    rack_group = CSVModelChoiceField(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Rack's group (if any)",
    )
    rack = CSVModelChoiceField(
        queryset=Rack.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Rack",
    )
    type = CSVChoiceField(choices=PowerFeedTypeChoices, required=False, help_text="Primary or redundant")
    supply = CSVChoiceField(choices=PowerFeedSupplyChoices, required=False, help_text="Supply type (AC/DC)")
    phase = CSVChoiceField(choices=PowerFeedPhaseChoices, required=False, help_text="Single or three-phase")

    class Meta:
        model = PowerFeed
        fields = PowerFeed.csv_headers

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit power_panel queryset by site
            params = {f"site__{self.fields['site'].to_field_name}": data.get("site")}
            self.fields["power_panel"].queryset = self.fields["power_panel"].queryset.filter(**params)

            # Limit rack_group queryset by site
            params = {f"site__{self.fields['site'].to_field_name}": data.get("site")}
            self.fields["rack_group"].queryset = self.fields["rack_group"].queryset.filter(**params)

            # Limit rack queryset by site and group
            params = {
                f"site__{self.fields['site'].to_field_name}": data.get("site"),
                f"group__{self.fields['rack_group'].to_field_name}": data.get("rack_group"),
            }
            self.fields["rack"].queryset = self.fields["rack"].queryset.filter(**params)


class PowerFeedBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=PowerFeed.objects.all(), widget=forms.MultipleHiddenInput)
    power_panel = DynamicModelChoiceField(queryset=PowerPanel.objects.all(), required=False)
    rack = DynamicModelChoiceField(queryset=Rack.objects.all(), required=False)
    type = forms.ChoiceField(
        choices=add_blank_choice(PowerFeedTypeChoices),
        required=False,
        initial="",
        widget=StaticSelect2(),
    )
    supply = forms.ChoiceField(
        choices=add_blank_choice(PowerFeedSupplyChoices),
        required=False,
        initial="",
        widget=StaticSelect2(),
    )
    phase = forms.ChoiceField(
        choices=add_blank_choice(PowerFeedPhaseChoices),
        required=False,
        initial="",
        widget=StaticSelect2(),
    )
    voltage = forms.IntegerField(required=False)
    amperage = forms.IntegerField(required=False)
    max_utilization = forms.IntegerField(required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        nullable_fields = [
            "rackgroup",
            "comments",
        ]


class PowerFeedFilterForm(NautobotFilterForm, StatusModelFilterFormMixin):
    model = PowerFeed
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    power_panel_id = DynamicModelMultipleChoiceField(
        queryset=PowerPanel.objects.all(),
        required=False,
        label="Power panel",
        null_option="None",
        query_params={"site": "$site"},
    )
    rack_id = DynamicModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        label="Rack",
        null_option="None",
        query_params={"site": "$site"},
    )
    type = forms.ChoiceField(
        choices=add_blank_choice(PowerFeedTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    supply = forms.ChoiceField(
        choices=add_blank_choice(PowerFeedSupplyChoices),
        required=False,
        widget=StaticSelect2(),
    )
    phase = forms.ChoiceField(
        choices=add_blank_choice(PowerFeedPhaseChoices),
        required=False,
        widget=StaticSelect2(),
    )
    voltage = forms.IntegerField(required=False)
    amperage = forms.IntegerField(required=False)
    max_utilization = forms.IntegerField(required=False)
    tag = TagFilterField(model)
