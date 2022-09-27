from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.constants import INTERFACE_MTU_MAX, INTERFACE_MTU_MIN
from nautobot.dcim.forms import InterfaceCommonForm, INTERFACE_MODE_HELP_TEXT
from nautobot.dcim.form_mixins import (
    LocatableModelBulkEditFormMixin,
    LocatableModelCSVFormMixin,
    LocatableModelFilterFormMixin,
    LocatableModelFormMixin,
)
from nautobot.dcim.models import Device, DeviceRole, Location, Platform, Rack, Region, Site
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
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant
from nautobot.utilities.forms import (
    add_blank_choice,
    BootstrapMixin,
    BulkEditNullBooleanSelect,
    BulkRenameForm,
    CommentField,
    ConfirmationForm,
    CSVChoiceField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    ExpandableNameField,
    form_from_model,
    SlugField,
    SmallTextarea,
    StaticSelect2,
    TagFilterField,
)
from nautobot.utilities.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface


#
# Cluster types
#


class ClusterTypeForm(NautobotModelForm):
    slug = SlugField()

    class Meta:
        model = ClusterType
        fields = [
            "name",
            "slug",
            "description",
        ]


class ClusterTypeCSVForm(CustomFieldModelCSVForm):
    class Meta:
        model = ClusterType
        fields = ClusterType.csv_headers


#
# Cluster groups
#


class ClusterGroupForm(NautobotModelForm):
    slug = SlugField()

    class Meta:
        model = ClusterGroup
        fields = [
            "name",
            "slug",
            "description",
        ]


class ClusterGroupCSVForm(CustomFieldModelCSVForm):
    class Meta:
        model = ClusterGroup
        fields = ClusterGroup.csv_headers


#
# Clusters
#


class ClusterForm(LocatableModelFormMixin, NautobotModelForm, TenancyForm):
    type = DynamicModelChoiceField(queryset=ClusterType.objects.all())
    group = DynamicModelChoiceField(queryset=ClusterGroup.objects.all(), required=False)
    comments = CommentField()

    class Meta:
        model = Cluster
        fields = (
            "name",
            "type",
            "group",
            "tenant",
            "region",
            "site",
            "location",
            "comments",
            "tags",
        )


class ClusterCSVForm(LocatableModelCSVFormMixin, CustomFieldModelCSVForm):
    type = CSVModelChoiceField(
        queryset=ClusterType.objects.all(),
        to_field_name="name",
        help_text="Type of cluster",
    )
    group = CSVModelChoiceField(
        queryset=ClusterGroup.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Assigned cluster group",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Assigned tenant",
    )

    class Meta:
        model = Cluster
        fields = Cluster.csv_headers


class ClusterBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Cluster.objects.all(), widget=forms.MultipleHiddenInput())
    type = DynamicModelChoiceField(queryset=ClusterType.objects.all(), required=False)
    group = DynamicModelChoiceField(queryset=ClusterGroup.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        model = Cluster
        nullable_fields = [
            "group",
            "site",
            "location",
            "comments",
            "tenant",
        ]


class ClusterFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin, TenancyFilterForm):
    model = Cluster
    field_order = ["q", "type", "region", "site", "group", "tenant_group", "tenant"]
    q = forms.CharField(required=False, label="Search")
    type = DynamicModelMultipleChoiceField(queryset=ClusterType.objects.all(), to_field_name="slug", required=False)
    group = DynamicModelMultipleChoiceField(
        queryset=ClusterGroup.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
    )
    tag = TagFilterField(model)


class ClusterAddDevicesForm(BootstrapMixin, forms.Form):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, null_option="None")
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={"region_id": "$region"},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={"content_type": "virtualization.cluster"},  # TODO: base_site: $site
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        null_option="None",
        query_params={
            "site_id": "$site",
            "location_id": "$location",
        },
    )
    devices = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        query_params={
            "site_id": "$site",
            "location_id": "$location",
            "rack_id": "$rack",
            "cluster_id": "null",
        },
    )

    class Meta:
        fields = [
            "region",
            "site",
            "location",
            "rack",
            "devices",
        ]

    def __init__(self, cluster, *args, **kwargs):

        self.cluster = cluster

        super().__init__(*args, **kwargs)

        self.fields["devices"].choices = []

    def clean(self):
        super().clean()

        # If the Cluster is assigned to a Site, all Devices must be assigned to that Site.
        if self.cluster.site is not None:
            for device in self.cleaned_data.get("devices", []):
                if device.site != self.cluster.site:
                    raise ValidationError(
                        {
                            "devices": f"{device} belongs to a different site ({device.site}) than the cluster ({self.cluster.site})"
                        }
                    )

        # If the Cluster is assigned to a Location, all Devices must exist within that Location
        if self.cluster.location is not None:
            for device in self.cleaned_data.get("devices", []):
                if device.location and self.cluster.location not in device.location.ancestors(include_self=True):
                    raise ValidationError(
                        {
                            "devices": f"{device} belongs to a location ({device.location}) that "
                            f"does not fall within this cluster's location ({self.cluster.location})."
                        }
                    )


class ClusterRemoveDevicesForm(ConfirmationForm):
    pk = forms.ModelMultipleChoiceField(queryset=Device.objects.all(), widget=forms.MultipleHiddenInput())


#
# Virtual Machines
#


class VirtualMachineForm(NautobotModelForm, TenancyForm, LocalContextModelForm):
    cluster_group = DynamicModelChoiceField(
        queryset=ClusterGroup.objects.all(),
        required=False,
        null_option="None",
        initial_params={"clusters": "$cluster"},
    )
    cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), query_params={"group_id": "$cluster_group"})
    role = DynamicModelChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
        query_params={"vm_role": "True"},
    )
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False)

    class Meta:
        model = VirtualMachine
        fields = [
            "name",
            "status",
            "cluster_group",
            "cluster",
            "role",
            "tenant_group",
            "tenant",
            "platform",
            "primary_ip4",
            "primary_ip6",
            "vcpus",
            "memory",
            "disk",
            "comments",
            "tags",
            "local_context_data",
            "local_context_schema",
        ]
        help_texts = {
            "local_context_data": "Local config context data overwrites all sources contexts in the final rendered "
            "config context",
        }
        widgets = {
            "primary_ip4": StaticSelect2(),
            "primary_ip6": StaticSelect2(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.present_in_database:

            # Compile list of choices for primary IPv4 and IPv6 addresses
            for family in [4, 6]:
                ip_choices = [(None, "---------")]

                # Gather PKs of all interfaces belonging to this VM
                interface_ids = self.instance.interfaces.values_list("pk", flat=True)

                # Collect interface IPs
                interface_ips = IPAddress.objects.ip_family(family).filter(
                    assigned_object_type=ContentType.objects.get_for_model(VMInterface),
                    assigned_object_id__in=interface_ids,
                )
                if interface_ips:
                    ip_list = [(ip.id, f"{ip.address} ({ip.assigned_object})") for ip in interface_ips]
                    ip_choices.append(("Interface IPs", ip_list))
                # Collect NAT IPs
                # v2 TODO(jathan): Replace prefetch_related with select_related
                nat_ips = (
                    IPAddress.objects.prefetch_related("nat_inside")
                    .ip_family(family)
                    .filter(
                        nat_inside__assigned_object_type=ContentType.objects.get_for_model(VMInterface),
                        nat_inside__assigned_object_id__in=interface_ids,
                    )
                )
                if nat_ips:
                    ip_list = [(ip.id, f"{ip.address} (NAT)") for ip in nat_ips]
                    ip_choices.append(("NAT IPs", ip_list))
                self.fields[f"primary_ip{family}"].choices = ip_choices

        else:

            # An object that doesn't exist yet can't have any IPs assigned to it
            self.fields["primary_ip4"].choices = []
            self.fields["primary_ip4"].widget.attrs["readonly"] = True
            self.fields["primary_ip6"].choices = []
            self.fields["primary_ip6"].widget.attrs["readonly"] = True


class VirtualMachineCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    cluster = CSVModelChoiceField(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        help_text="Assigned cluster",
    )
    role = CSVModelChoiceField(
        queryset=DeviceRole.objects.filter(vm_role=True),
        required=False,
        to_field_name="name",
        help_text="Functional role",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned tenant",
    )
    platform = CSVModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned platform",
    )

    class Meta:
        model = VirtualMachine
        fields = VirtualMachine.csv_headers


class VirtualMachineBulkEditForm(
    TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm, LocalContextModelBulkEditForm
):
    pk = forms.ModelMultipleChoiceField(queryset=VirtualMachine.objects.all(), widget=forms.MultipleHiddenInput())
    cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), required=False)
    role = DynamicModelChoiceField(
        queryset=DeviceRole.objects.filter(vm_role=True),
        required=False,
        query_params={"vm_role": "True"},
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False)
    vcpus = forms.IntegerField(required=False, label="vCPUs")
    memory = forms.IntegerField(required=False, label="Memory (MB)")
    disk = forms.IntegerField(required=False, label="Disk (GB)")
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        nullable_fields = [
            "role",
            "tenant",
            "platform",
            "vcpus",
            "memory",
            "disk",
            "comments",
        ]


class VirtualMachineFilterForm(
    NautobotFilterForm,
    LocatableModelFilterFormMixin,
    TenancyFilterForm,
    StatusModelFilterFormMixin,
    LocalContextFilterForm,
):
    model = VirtualMachine
    field_order = [
        "q",
        "cluster_group",
        "cluster_type",
        "cluster_id",
        "status",
        "role",
        "region",
        "site",
        "location",
        "tenant_group",
        "tenant",
        "platform",
        "mac_address",
    ]
    q = forms.CharField(required=False, label="Search")
    cluster_group = DynamicModelMultipleChoiceField(
        queryset=ClusterGroup.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
    )
    cluster_type = DynamicModelMultipleChoiceField(
        queryset=ClusterType.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
    )
    cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    role = DynamicModelMultipleChoiceField(
        queryset=DeviceRole.objects.filter(vm_role=True),
        to_field_name="slug",
        required=False,
        null_option="None",
        query_params={"vm_role": "True"},
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
    tag = TagFilterField(model)


#
# VM interfaces
#


class VMInterfaceForm(NautobotModelForm, InterfaceCommonForm):
    parent_interface = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        label="Parent interface",
        help_text="Assigned parent VMinterface",
    )
    bridge = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        label="Bridge interface",
        help_text="Assigned bridge VMinterface",
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
        model = VMInterface
        fields = [
            "virtual_machine",
            "name",
            "enabled",
            "parent_interface",
            "bridge",
            "mac_address",
            "mtu",
            "description",
            "mode",
            "tags",
            "untagged_vlan",
            "tagged_vlans",
            "status",
        ]
        widgets = {"virtual_machine": forms.HiddenInput(), "mode": StaticSelect2()}
        labels = {
            "mode": "802.1Q Mode",
        }
        help_texts = {
            "mode": INTERFACE_MODE_HELP_TEXT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vm_id = self.initial.get("virtual_machine") or self.data.get("virtual_machine")

        # Restrict parent interface assignment by VM
        self.fields["parent_interface"].widget.add_query_param("virtual_machine_id", vm_id)
        self.fields["bridge"].widget.add_query_param("virtual_machine_id", vm_id)

        virtual_machine = VirtualMachine.objects.get(
            pk=self.initial.get("virtual_machine") or self.data.get("virtual_machine")
        )

        # Add current site to VLANs query params
        site = virtual_machine.site
        if site:
            self.fields["untagged_vlan"].widget.add_query_param("site_id", site.pk)
            self.fields["tagged_vlans"].widget.add_query_param("site_id", site.pk)


class VMInterfaceCreateForm(BootstrapMixin, InterfaceCommonForm):
    virtual_machine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all())
    name_pattern = ExpandableNameField(label="Name")
    enabled = forms.BooleanField(required=False, initial=True)
    parent_interface = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        query_params={
            "virtual_machine_id": "$virtual_machine",
        },
        help_text="Assigned parent VMinterface",
    )
    bridge = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        query_params={
            "virtual_machine_id": "$virtual_machine",
        },
        help_text="Assigned bridge VMinterface",
    )
    mtu = forms.IntegerField(
        required=False,
        min_value=INTERFACE_MTU_MIN,
        max_value=INTERFACE_MTU_MAX,
        label="MTU",
    )
    mac_address = forms.CharField(required=False, label="MAC Address")
    description = forms.CharField(max_length=100, required=False)
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
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={
            "content_types": VMInterface._meta.label_lower,
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vm_id = self.initial.get("virtual_machine") or self.data.get("virtual_machine")

        # Restrict parent interface assignment by VM
        self.fields["parent_interface"].widget.add_query_param("virtual_machine_id", vm_id)
        self.fields["bridge"].widget.add_query_param("virtual_machine_id", vm_id)

        virtual_machine = VirtualMachine.objects.get(
            pk=self.initial.get("virtual_machine") or self.data.get("virtual_machine")
        )

        # Add current site to VLANs query params
        site = virtual_machine.site
        if site:
            self.fields["untagged_vlan"].widget.add_query_param("site_id", site.pk)
            self.fields["tagged_vlans"].widget.add_query_param("site_id", site.pk)


class VMInterfaceCSVForm(CustomFieldModelCSVForm, StatusModelCSVFormMixin):
    virtual_machine = CSVModelChoiceField(queryset=VirtualMachine.objects.all(), to_field_name="name")
    parent_interface = CSVModelChoiceField(
        queryset=VMInterface.objects.all(), required=False, to_field_name="name", help_text="Parent interface"
    )
    bridge = CSVModelChoiceField(
        queryset=VMInterface.objects.all(), required=False, to_field_name="name", help_text="Bridge interface"
    )
    mode = CSVChoiceField(
        choices=InterfaceModeChoices,
        required=False,
        help_text="IEEE 802.1Q operational mode (for L2 interfaces)",
    )

    class Meta:
        model = VMInterface
        fields = VMInterface.csv_headers

    def clean_enabled(self):
        # Make sure enabled is True when it's not included in the uploaded data
        if "enabled" not in self.data:
            return True
        else:
            return self.cleaned_data["enabled"]


class VMInterfaceBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=VMInterface.objects.all(), widget=forms.MultipleHiddenInput())
    virtual_machine = forms.ModelChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        disabled=True,
        widget=forms.HiddenInput(),
    )
    parent_interface = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(), required=False, display_field="display_name"
    )
    bridge = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
    )
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect())
    mtu = forms.IntegerField(
        required=False,
        min_value=INTERFACE_MTU_MIN,
        max_value=INTERFACE_MTU_MAX,
        label="MTU",
    )
    description = forms.CharField(max_length=100, required=False)
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
            "parent_interface",
            "bridge",
            "mtu",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vm_id = self.initial.get("virtual_machine") or self.data.get("virtual_machine")

        # Restrict parent/bridge interface assignment by VM
        self.fields["parent_interface"].widget.add_query_param("virtual_machine_id", vm_id)
        self.fields["bridge"].widget.add_query_param("virtual_machine_id", vm_id)

        # Limit available VLANs based on the parent VirtualMachine
        if "virtual_machine" in self.initial:
            parent_obj = VirtualMachine.objects.filter(pk=self.initial["virtual_machine"]).first()

            site = getattr(parent_obj.cluster, "site", None)
            if site is not None:
                # Add current site to VLANs query params
                self.fields["untagged_vlan"].widget.add_query_param("site_id", site.pk)
                self.fields["tagged_vlans"].widget.add_query_param("site_id", site.pk)

        self.fields["parent_interface"].choices = ()
        self.fields["parent_interface"].widget.attrs["disabled"] = True
        self.fields["bridge"].choices = ()
        self.fields["bridge"].widget.attrs["disabled"] = True


class VMInterfaceBulkRenameForm(BulkRenameForm):
    pk = forms.ModelMultipleChoiceField(queryset=VMInterface.objects.all(), widget=forms.MultipleHiddenInput())


class VMInterfaceFilterForm(NautobotFilterForm, StatusModelFilterFormMixin):
    model = VMInterface
    cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    virtual_machine_id = DynamicModelMultipleChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        label="Virtual machine",
        query_params={"cluster_id": "$cluster_id"},
    )
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    tag = TagFilterField(model)


#
# Bulk VirtualMachine component creation
#


class VirtualMachineBulkAddComponentForm(CustomFieldModelBulkEditFormMixin, BootstrapMixin, forms.Form):
    pk = forms.ModelMultipleChoiceField(queryset=VirtualMachine.objects.all(), widget=forms.MultipleHiddenInput())
    name_pattern = ExpandableNameField(label="Name")

    class Meta:
        nullable_fields = []


class VMInterfaceBulkCreateForm(
    form_from_model(VMInterface, ["enabled", "mtu", "description", "mode"]),
    VirtualMachineBulkAddComponentForm,
):
    field_order = (
        "name_pattern",
        "enabled",
        "mtu",
        "description",
        "mode",
        "tags",
    )
