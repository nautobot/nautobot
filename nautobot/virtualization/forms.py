from django import forms
from django.core.exceptions import ValidationError

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    add_blank_choice,
    BootstrapMixin,
    BulkEditNullBooleanSelect,
    BulkRenameForm,
    CommentField,
    ConfirmationForm,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    ExpandableNameField,
    form_from_model,
    SmallTextarea,
    StaticSelect2,
    TagFilterField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.constants import INTERFACE_MTU_MAX, INTERFACE_MTU_MIN
from nautobot.dcim.form_mixins import (
    LocatableModelBulkEditFormMixin,
    LocatableModelFilterFormMixin,
    LocatableModelFormMixin,
)
from nautobot.dcim.forms import INTERFACE_MODE_HELP_TEXT, InterfaceCommonForm
from nautobot.dcim.models import Device, Location, Platform, Rack, SoftwareImageFile, SoftwareVersion
from nautobot.extras.forms import (
    CustomFieldModelBulkEditFormMixin,
    LocalContextFilterForm,
    LocalContextModelBulkEditForm,
    LocalContextModelForm,
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    RoleModelBulkEditFormMixin,
    RoleModelFilterFormMixin,
    RoleNotRequiredModelFormMixin,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, IPAddressToInterface, VLAN, VRF
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant

from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface

#
# Cluster types
#


class ClusterTypeForm(NautobotModelForm):
    class Meta:
        model = ClusterType
        fields = [
            "name",
            "description",
        ]


class ClusterTypeFilterForm(NautobotFilterForm):
    model = ClusterType
    q = forms.CharField(required=False, label="Search")
    clusters = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), to_field_name="name", required=False)


class ClusterTypeBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ClusterType.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "description",
        ]


#
# Cluster groups
#


class ClusterGroupForm(NautobotModelForm):
    class Meta:
        model = ClusterGroup
        fields = [
            "name",
            "description",
        ]


class ClusterGroupFilterForm(NautobotFilterForm):
    model = ClusterGroup
    q = forms.CharField(required=False, label="Search")
    clusters = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), to_field_name="name", required=False)


class ClusterGroupBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ClusterGroup.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "description",
        ]


#
# Clusters
#


class ClusterForm(LocatableModelFormMixin, NautobotModelForm, TenancyForm):
    cluster_type = DynamicModelChoiceField(queryset=ClusterType.objects.all())
    cluster_group = DynamicModelChoiceField(queryset=ClusterGroup.objects.all(), required=False)
    comments = CommentField()

    class Meta:
        model = Cluster
        fields = (
            "name",
            "cluster_type",
            "cluster_group",
            "tenant",
            "location",
            "comments",
            "tags",
        )


class ClusterBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Cluster.objects.all(), widget=forms.MultipleHiddenInput())
    cluster_type = DynamicModelChoiceField(queryset=ClusterType.objects.all(), required=False)
    cluster_group = DynamicModelChoiceField(queryset=ClusterGroup.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        model = Cluster
        nullable_fields = [
            "cluster_group",
            "location",
            "comments",
            "tenant",
        ]


class ClusterFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin, TenancyFilterForm):
    model = Cluster
    field_order = ["q", "cluster_type", "location", "cluster_group", "tenant_group", "tenant"]
    q = forms.CharField(required=False, label="Search")
    cluster_type = DynamicModelMultipleChoiceField(
        queryset=ClusterType.objects.all(), to_field_name="name", required=False
    )
    cluster_group = DynamicModelMultipleChoiceField(
        queryset=ClusterGroup.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
    tags = TagFilterField(model)


class ClusterAddDevicesForm(BootstrapMixin, forms.Form):
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={"content_type": "virtualization.cluster"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        null_option="None",
        query_params={
            "location": "$location",
        },
    )
    devices = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        query_params={
            "location": "$location",
            "rack": "$rack",
            "cluster": "null",
        },
    )

    class Meta:
        fields = [
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
    cluster = DynamicModelChoiceField(
        queryset=Cluster.objects.all(), query_params={"cluster_group_id": "$cluster_group"}
    )
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False)
    software_image_files = DynamicModelMultipleChoiceField(
        queryset=SoftwareImageFile.objects.all(),
        required=False,
        label="Software image files",
        help_text="Override the software image files associated with the software version for this virtual machine",
    )
    software_version = DynamicModelChoiceField(queryset=SoftwareVersion.objects.all(), required=False)
    vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="VRFs",
    )

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
            "vrfs",
            "platform",
            "primary_ip4",
            "primary_ip6",
            "software_image_files",
            "software_version",
            "vcpus",
            "memory",
            "disk",
            "comments",
            "tags",
            "local_config_context_data",
            "local_config_context_schema",
        ]
        help_texts = {
            "local_config_context_data": "Local config context data overwrites all sources contexts in the final rendered "
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
            for ip_version in [4, 6]:
                ip_choices = [(None, "---------")]

                # Gather PKs of all interfaces belonging to this VM
                interface_ids = self.instance.interfaces.values_list("pk", flat=True)

                # Collect interface IPs
                interface_ip_assignments = IPAddressToInterface.objects.filter(
                    vm_interface__in=interface_ids
                ).select_related("ip_address")
                if interface_ip_assignments.exists():
                    ip_list = [
                        (
                            assignment.ip_address.id,
                            f"{assignment.ip_address.address} ({assignment.vm_interface})",
                        )
                        for assignment in interface_ip_assignments
                        if assignment.ip_address.ip_version == ip_version
                    ]
                    ip_choices.append(("Interface IPs", ip_list))

                    # Collect NAT IPs
                    nat_ips = []
                    for ip_assignment in interface_ip_assignments:
                        if not ip_assignment.ip_address.nat_outside_list.exists():
                            continue
                        nat_ips.extend(
                            [
                                (ip.id, f"{ip.address} (NAT)")
                                for ip in ip_assignment.ip_address.nat_outside_list.all()
                                if ip.ip_version == ip_version
                            ]
                        )
                    ip_choices.append(("NAT IPs", nat_ips))
                self.fields[f"primary_ip{ip_version}"].choices = ip_choices

            self.initial["vrfs"] = self.instance.vrfs.values_list("id", flat=True)

        else:
            # An object that doesn't exist yet can't have any IPs assigned to it
            self.fields["primary_ip4"].choices = []
            self.fields["primary_ip4"].widget.attrs["readonly"] = True
            self.fields["primary_ip6"].choices = []
            self.fields["primary_ip6"].widget.attrs["readonly"] = True

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.vrfs.set(self.cleaned_data["vrfs"])
        return instance


class VirtualMachineBulkEditForm(
    TagsBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    RoleModelBulkEditFormMixin,
    NautobotBulkEditForm,
    LocalContextModelBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=VirtualMachine.objects.all(), widget=forms.MultipleHiddenInput())
    cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False)
    vcpus = forms.IntegerField(required=False, label="vCPUs")
    memory = forms.IntegerField(required=False, label="Memory (MB)")
    disk = forms.IntegerField(required=False, label="Disk (GB)")
    comments = CommentField(widget=SmallTextarea, label="Comments")
    software_version = DynamicModelChoiceField(queryset=SoftwareVersion.objects.all(), required=False)
    software_image_files = DynamicModelMultipleChoiceField(queryset=SoftwareImageFile.objects.all(), required=False)

    class Meta:
        nullable_fields = [
            "tenant",
            "platform",
            "vcpus",
            "memory",
            "disk",
            "comments",
            "software_image_files",
            "software_version",
        ]


class VirtualMachineFilterForm(
    NautobotFilterForm,
    LocatableModelFilterFormMixin,
    TenancyFilterForm,
    StatusModelFilterFormMixin,
    RoleModelFilterFormMixin,
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
        "location",
        "tenant_group",
        "tenant",
        "platform",
        "mac_address",
    ]
    q = forms.CharField(required=False, label="Search")
    cluster_group = DynamicModelMultipleChoiceField(
        queryset=ClusterGroup.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
    cluster_type = DynamicModelMultipleChoiceField(
        queryset=ClusterType.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
    cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    platform = DynamicModelMultipleChoiceField(
        queryset=Platform.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
    mac_address = forms.CharField(required=False, label="MAC address")
    has_primary_ip = forms.NullBooleanField(
        required=False,
        label="Has a primary IP",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    software_version = DynamicModelMultipleChoiceField(
        queryset=SoftwareVersion.objects.all(),
        required=False,
        label="Software version",
    )
    has_software_version = forms.NullBooleanField(
        required=False,
        label="Has software version",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tags = TagFilterField(model)


#
# VM interfaces
#


class VMInterfaceForm(NautobotModelForm, InterfaceCommonForm):
    virtual_machine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all())
    parent_interface = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        label="Parent interface",
        help_text="Assigned parent VMinterface",
        query_params={"virtual_machine": "$virtual_machine"},
    )
    bridge = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        label="Bridge interface",
        help_text="Assigned bridge VMinterface",
        query_params={"virtual_machine": "$virtual_machine"},
    )
    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="Untagged VLAN",
        query_params={
            "locations": "null",
        },
    )
    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="Tagged VLANs",
        query_params={
            "locations": "null",
        },
    )
    ip_addresses = DynamicModelMultipleChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="IP Addresses",
    )
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        label="VRF",
        required=False,
        query_params={
            "virtual_machines": "$virtual_machine",
        },
    )

    class Meta:
        model = VMInterface
        fields = [
            "virtual_machine",
            "name",
            "role",
            "enabled",
            "parent_interface",
            "bridge",
            "mac_address",
            "ip_addresses",
            "mtu",
            "description",
            "mode",
            "tags",
            "untagged_vlan",
            "tagged_vlans",
            "status",
            "vrf",
        ]
        widgets = {"mode": StaticSelect2()}
        labels = {
            "mode": "802.1Q Mode",
        }
        help_texts = {
            "mode": INTERFACE_MODE_HELP_TEXT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Disallow changing the virtual_machine of an existing vminterface
        if self.instance is not None and self.instance.present_in_database:
            self.fields["virtual_machine"].disabled = True

        virtual_machine = VirtualMachine.objects.get(
            pk=self.initial.get("virtual_machine") or self.data.get("virtual_machine")
        )

        # Add current location to VLANs query params
        location = virtual_machine.location
        if location:
            self.fields["untagged_vlan"].widget.add_query_param("locations", location.pk)
            self.fields["tagged_vlans"].widget.add_query_param("locations", location.pk)


class VMInterfaceCreateForm(BootstrapMixin, InterfaceCommonForm, RoleNotRequiredModelFormMixin):
    model = VMInterface
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
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    mode = forms.ChoiceField(
        choices=add_blank_choice(InterfaceModeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        query_params={
            "locations": "null",
        },
    )
    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        query_params={
            "locations": "null",
        },
    )
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={
            "content_types": VMInterface._meta.label_lower,
        },
    )
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        label="VRF",
        required=False,
        query_params={
            "virtual_machines": "$virtual_machine",
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

        # Add current location to VLANs query params
        location = virtual_machine.location
        if location:
            self.fields["untagged_vlan"].widget.add_query_param("locations", location.pk)
            self.fields["tagged_vlans"].widget.add_query_param("locations", location.pk)


class VMInterfaceBulkEditForm(
    TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, RoleModelBulkEditFormMixin, NautobotBulkEditForm
):
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
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        query_params={
            "virtual_machines": "$virtual_machine",
        },
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
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    mode = forms.ChoiceField(
        choices=add_blank_choice(InterfaceModeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        query_params={
            "locations": "null",
        },
    )
    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        query_params={
            "locations": "null",
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

            location = getattr(parent_obj.cluster, "location", None)
            if location is not None:
                # Add current location to VLANs query params
                self.fields["untagged_vlan"].widget.add_query_param("locations", location.pk)
                self.fields["tagged_vlans"].widget.add_query_param("locations", location.pk)

        self.fields["parent_interface"].choices = ()
        self.fields["parent_interface"].widget.attrs["disabled"] = True
        self.fields["bridge"].choices = ()
        self.fields["bridge"].widget.attrs["disabled"] = True


class VMInterfaceBulkRenameForm(BulkRenameForm):
    pk = forms.ModelMultipleChoiceField(queryset=VMInterface.objects.all(), widget=forms.MultipleHiddenInput())


class VMInterfaceFilterForm(NautobotFilterForm, RoleModelFilterFormMixin, StatusModelFilterFormMixin):
    model = VMInterface
    cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    virtual_machine_id = DynamicModelMultipleChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        label="Virtual machine",
        query_params={"cluster_id": "$cluster_id"},
    )
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    tags = TagFilterField(model)


#
# Bulk VirtualMachine component creation
#


class VirtualMachineBulkAddComponentForm(CustomFieldModelBulkEditFormMixin, BootstrapMixin, forms.Form):
    pk = forms.ModelMultipleChoiceField(queryset=VirtualMachine.objects.all(), widget=forms.MultipleHiddenInput())
    name_pattern = ExpandableNameField(label="Name")

    class Meta:
        nullable_fields = []


class VMInterfaceBulkCreateForm(
    form_from_model(VMInterface, ["enabled", "mtu", "description", "mode", "tags"]),
    VirtualMachineBulkAddComponentForm,
    RoleNotRequiredModelFormMixin,
):
    model = VMInterface
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": VMInterface._meta.label_lower},
    )

    field_order = (
        "name_pattern",
        "status",
        "role",
        "enabled",
        "mtu",
        "description",
        "mode",
        "tags",
    )
