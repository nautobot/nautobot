from django import forms
from django.core.exceptions import ValidationError

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    add_blank_choice,
    AddressFieldMixin,
    BootstrapMixin,
    DateTimePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    ExpandableIPAddressField,
    NumericArrayField,
    PrefixFieldMixin,
    ReturnURLForm,
    StaticSelect2,
    StaticSelect2Multiple,
    TagFilterField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.dcim.form_mixins import (
    LocatableModelBulkEditFormMixin,
    LocatableModelFilterFormMixin,
    LocatableModelFormMixin,
)
from nautobot.dcim.models import Device, Location, Rack, VirtualDeviceContext
from nautobot.extras.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    RoleModelBulkEditFormMixin,
    RoleModelFilterFormMixin,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, VirtualMachine

from .choices import IPAddressTypeChoices, IPAddressVersionChoices, PrefixTypeChoices, ServiceProtocolChoices
from .constants import (
    IPADDRESS_MASK_LENGTH_MAX,
    IPADDRESS_MASK_LENGTH_MIN,
    PREFIX_LENGTH_MAX,
    PREFIX_LENGTH_MIN,
    SERVICE_PORT_MAX,
    SERVICE_PORT_MIN,
)
from .models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)

PREFIX_MASK_LENGTH_CHOICES = add_blank_choice([(i, i) for i in range(PREFIX_LENGTH_MIN, PREFIX_LENGTH_MAX + 1)])

IPADDRESS_MASK_LENGTH_CHOICES = add_blank_choice(
    [(i, i) for i in range(IPADDRESS_MASK_LENGTH_MIN, IPADDRESS_MASK_LENGTH_MAX + 1)]
)


#
# Namespaces
#


class NamespaceForm(LocatableModelFormMixin, NautobotModelForm):
    class Meta:
        model = Namespace
        fields = ["name", "description", "location", "tags"]


class NamespaceBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Namespace.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = Namespace
        nullable_fields = [
            "description",
            "location",
        ]


class NamespaceFilterForm(LocatableModelFilterFormMixin, NautobotFilterForm):
    model = Namespace
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)


#
# VRFs
#


class VRFForm(NautobotModelForm, TenancyForm):
    import_targets = DynamicModelMultipleChoiceField(queryset=RouteTarget.objects.all(), required=False)
    export_targets = DynamicModelMultipleChoiceField(queryset=RouteTarget.objects.all(), required=False)
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all())
    devices = DynamicModelMultipleChoiceField(queryset=Device.objects.all(), required=False)
    virtual_machines = DynamicModelMultipleChoiceField(queryset=VirtualMachine.objects.all(), required=False)
    virtual_device_contexts = DynamicModelMultipleChoiceField(
        queryset=VirtualDeviceContext.objects.all(), required=False
    )
    prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(),
        required=False,
        query_params={
            "namespace": "$namespace",
        },
    )

    class Meta:
        model = VRF
        fields = [
            "name",
            "rd",
            "namespace",
            "status",
            "description",
            "import_targets",
            "export_targets",
            "tenant_group",
            "tenant",
            "tags",
            "devices",
            "virtual_machines",
            "virtual_device_contexts",
            "prefixes",
        ]
        labels = {
            "rd": "RD",
        }
        help_texts = {
            "rd": "Route distinguisher unique to this Namespace (as defined in RFC 4364)",
            "status": "Operational status of this VRF",
        }


class VRFBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=VRF.objects.all(), widget=forms.MultipleHiddenInput())
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    add_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    remove_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    add_virtual_device_contexts = DynamicModelMultipleChoiceField(
        queryset=VirtualDeviceContext.objects.all(),
        required=False,
    )
    remove_virtual_device_contexts = DynamicModelMultipleChoiceField(
        queryset=VirtualDeviceContext.objects.all(),
        required=False,
    )

    class Meta:
        nullable_fields = [
            "tenant",
            "description",
        ]


class VRFFilterForm(NautobotFilterForm, StatusModelFilterFormMixin, TenancyFilterForm):
    model = VRF
    field_order = ["q", "import_targets", "export_targets", "status", "tenant_group", "tenant"]
    q = forms.CharField(required=False, label="Search")
    import_targets = DynamicModelMultipleChoiceField(
        queryset=RouteTarget.objects.all(), to_field_name="name", required=False
    )
    export_targets = DynamicModelMultipleChoiceField(
        queryset=RouteTarget.objects.all(), to_field_name="name", required=False
    )
    tags = TagFilterField(model)


#
# Route targets
#


class RouteTargetForm(NautobotModelForm, TenancyForm):
    class Meta:
        model = RouteTarget
        fields = [
            "name",
            "description",
            "tenant_group",
            "tenant",
            "tags",
        ]


class RouteTargetBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RouteTarget.objects.all(), widget=forms.MultipleHiddenInput())
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "tenant",
            "description",
        ]


class RouteTargetFilterForm(NautobotFilterForm, TenancyFilterForm):
    model = RouteTarget
    field_order = [
        "q",
        "name",
        "tenant_group",
        "tenant",
        "importing_vrfs",
        "exporting_vrfs",
    ]
    q = forms.CharField(required=False, label="Search")
    importing_vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(), required=False, label="Imported by VRF(s)"
    )
    exporting_vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(), required=False, label="Exported by VRF(s)"
    )
    tags = TagFilterField(model)


#
# RIRs
#


class RIRForm(NautobotModelForm):
    class Meta:
        model = RIR
        fields = [
            "name",
            "is_private",
            "description",
        ]


class RIRFilterForm(NautobotFilterForm):
    model = RIR
    is_private = forms.NullBooleanField(
        required=False,
        label="Private",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )


class RIRBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RIR.objects.all(), widget=forms.MultipleHiddenInput())
    is_private = forms.NullBooleanField(
        required=False,
        label="Private",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "description",
        ]


#
# Prefixes
#


class PrefixForm(NautobotModelForm, TenancyForm, PrefixFieldMixin):
    locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Locations",
        null_option="None",
        query_params={"content_type": Prefix._meta.label_lower},
    )
    vlan_group = DynamicModelChoiceField(
        queryset=VLANGroup.objects.all(),
        required=False,
        label="VLAN group",
        null_option="None",
        initial_params={"vlans": "$vlan"},
    )
    vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="VLAN",
        query_params={
            "locations": "$locations",
            "vlan_group": "$vlan_group",
        },
    )
    rir = DynamicModelChoiceField(queryset=RIR.objects.all(), required=False, label="RIR")
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all())
    vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="VRFs",
        query_params={
            "namespace": "$namespace",
        },
    )
    # It is required to add prefix_length here and set it to required=False and hidden input so that
    # form validation doesn't complain and that it doesn't show in forms.
    # Ref:  https://github.com/nautobot/nautobot/issues/4550
    prefix_length = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Prefix
        fields = [
            "prefix",
            "namespace",
            "vrfs",
            "locations",
            "vlan",
            "status",
            "role",
            "type",
            "description",
            "tenant_group",
            "tenant",
            "rir",
            "date_allocated",
            "tags",
        ]
        widgets = {
            "date_allocated": DateTimePicker(),
        }

    def _get_validation_exclusions(self):
        """
        By default Django excludes "network"/"prefix_length" from model validation because they are not form fields.

        This is wrong since we need those fields to be included in the validate_unique() calculation!
        """
        exclude = super()._get_validation_exclusions()
        exclude.remove("network")
        exclude.remove("prefix_length")
        return exclude

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.initial["vrfs"] = self.instance.vrfs.values_list("id", flat=True)

    def clean(self):
        # Translate model ValidationError to forms.ValidationError
        try:
            return super().clean()
        except ValidationError as e:
            raise forms.ValidationError(e.message_dict) from e

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.vrfs.set(self.cleaned_data["vrfs"])
        instance.locations.set(self.cleaned_data["locations"])
        return instance


class PrefixBulkEditForm(
    TagsBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    RoleModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=Prefix.objects.all(), widget=forms.MultipleHiddenInput())
    type = forms.ChoiceField(
        choices=add_blank_choice(PrefixTypeChoices),
        required=False,
    )
    """
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="VRF",
    )
    """
    prefix_length = forms.IntegerField(min_value=PREFIX_LENGTH_MIN, max_value=PREFIX_LENGTH_MAX, required=False)
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), required=False)
    add_locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(), required=False, query_params={"content_type": Prefix._meta.label_lower}
    )
    remove_locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(), required=False, query_params={"content_type": Prefix._meta.label_lower}
    )
    add_vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    remove_vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    rir = DynamicModelChoiceField(queryset=RIR.objects.all(), required=False, label="RIR")
    date_allocated = forms.DateTimeField(required=False, widget=DateTimePicker)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = Prefix
        nullable_fields = [
            # "vrf",
            "tenant",
            "rir",
            "date_allocated",
            "description",
        ]


class PrefixFilterForm(
    NautobotFilterForm,
    TenancyFilterForm,
    StatusModelFilterFormMixin,
    RoleModelFilterFormMixin,
):
    model = Prefix
    field_order = [
        "q",
        "within_include",
        "type",
        "ip_version",
        "prefix_length",
        "vrfs",
        "present_in_vrf_id",
        "status",
        "locations",
        "role",
        "tenant_group",
        "tenant",
        "rir",
    ]
    prefix_length__lte = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    q = forms.CharField(required=False, label="Search")
    within_include = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Prefix",
            }
        ),
        label="Search within",
    )
    ip_version = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(IPAddressVersionChoices),
        label="IP version",
        widget=StaticSelect2(),
    )
    prefix_length = forms.ChoiceField(
        required=False,
        choices=PREFIX_MASK_LENGTH_CHOICES,
        label="Prefix length",
        widget=StaticSelect2(),
    )
    vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="Assigned VRF(s)",
        null_option="Global",
    )
    present_in_vrf_id = DynamicModelChoiceField(queryset=VRF.objects.all(), required=False, label="Present in VRF")
    locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
        query_params={"content_type": VLAN._meta.label_lower},
    )
    type = forms.MultipleChoiceField(
        required=False,
        choices=PrefixTypeChoices,
        widget=StaticSelect2Multiple(),
    )
    rir = DynamicModelChoiceField(queryset=RIR.objects.all(), required=False, label="RIR")
    tags = TagFilterField(model)


#
# IP addresses
#


class IPAddressFormMixin(NautobotModelForm, TenancyForm, AddressFieldMixin):
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), label="Namespace")

    def clean_namespace(self):
        """
        Explicitly set the Namespace on the instance so it will be used on save.

        While the model does this itself on create, the model form is creating a bare instance first
        and setting attributes individually based on the form field values. Since namespace isn't an
        actual model field, it gets ignored by default.
        """
        namespace = self.cleaned_data.pop("namespace")
        setattr(self.instance, "_namespace", namespace)
        # Since 'parent' is always derived from 'namespace', we set the current instance's 'parent' to 'None'.
        # This prevents the model from revalidating the 'parent', which could raise a validation error when the current
        # parent differs from the parent derived from the new `namespace`.
        self.instance.parent = None


class IPAddressForm(IPAddressFormMixin, ReturnURLForm):
    nat_location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Location",
    )
    nat_rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        label="Rack",
        null_option="None",
        query_params={"location": "$nat_location"},
    )
    nat_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
        query_params={
            "location": "$nat_location",
            "rack": "$nat_rack",
        },
    )
    nat_cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    nat_virtual_machine = DynamicModelChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        label="Virtual Machine",
        query_params={
            "cluster_id": "$nat_cluster",
        },
    )
    nat_vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="VRF",
    )
    nat_inside = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="IP Address",
        query_params={
            "device_id": "$nat_device",
            "virtual_machine_id": "$nat_virtual_machine",
            "vrf_id": "$nat_vrf",
        },
    )

    class Meta:
        model = IPAddress
        fields = [
            "address",
            "namespace",
            "type",
            "status",
            "role",
            "dns_name",
            "description",
            "nat_rack",
            "nat_device",
            "nat_cluster",
            "nat_virtual_machine",
            "nat_vrf",
            "nat_inside",
            "tenant_group",
            "tenant",
            "tags",
        ]

    def _get_validation_exclusions(self):
        """
        By default Django excludes "host" and "parent" from model validation because they are not form fields.

        This is wrong since we need those fields to be included in the validate_unique() calculation!
        """
        exclude = super()._get_validation_exclusions()
        exclude.remove("host")
        exclude.remove("parent")
        return exclude

    def clean(self):
        # Pass address to the instance, because this is required to be accessible in the IPAddress.clean method
        self.instance.address = self.cleaned_data.get("address")
        super().clean()

    def __init__(self, *args, **kwargs):
        # Initialize helper selectors
        instance = kwargs.get("instance")
        initial = kwargs.get("initial", {}).copy()

        if instance:
            if instance.nat_inside:
                # TODO: Does this make sense with ip address to interface relationship changing to m2m?
                nat_inside_parent = IPAddressToInterface.objects.filter(ip_address=instance.nat_inside)
                if nat_inside_parent.count() == 1:
                    nat_inside_parent = nat_inside_parent.first()
                    if nat_inside_parent.interface is not None:
                        parent_device = nat_inside_parent.interface.device
                        if parent_device is None and nat_inside_parent.interface.module is not None:
                            parent_device = nat_inside_parent.interface.module.device
                        if parent_device:
                            initial["nat_location"] = parent_device.location.pk
                            if parent_device.rack:
                                initial["nat_rack"] = parent_device.rack.pk
                            initial["nat_device"] = parent_device.pk
                    elif nat_inside_parent.vm_interface is not None:
                        initial["nat_cluster"] = nat_inside_parent.vm_interface.virtual_machine.cluster.pk
                        initial["nat_virtual_machine"] = nat_inside_parent.vm_interface.virtual_machine.pk

            # Always populate the namespace from the parent.
            if instance.present_in_database:
                initial["namespace"] = instance.parent.namespace

        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)


class IPAddressBulkCreateForm(BootstrapMixin, forms.Form):
    pattern = ExpandableIPAddressField(label="Address pattern")


class IPAddressBulkAddForm(IPAddressFormMixin):
    class Meta:
        model = IPAddress
        fields = [
            "address",
            "namespace",
            "status",
            "type",
            "role",
            "dns_name",
            "description",
            "tenant_group",
            "tenant",
            "tags",
        ]


class IPAddressBulkEditForm(
    TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, RoleModelBulkEditFormMixin, NautobotBulkEditForm
):
    pk = forms.ModelMultipleChoiceField(queryset=IPAddress.objects.all(), widget=forms.MultipleHiddenInput())
    mask_length = forms.IntegerField(
        min_value=IPADDRESS_MASK_LENGTH_MIN,
        max_value=IPADDRESS_MASK_LENGTH_MAX,
        required=False,
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    dns_name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(IPAddressTypeChoices),
        widget=StaticSelect2(),
    )

    class Meta:
        nullable_fields = [
            "tenant",
            "dns_name",
            "description",
        ]


class IPAddressAssignForm(BootstrapMixin, forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
    )


class IPAddressFilterForm(NautobotFilterForm, TenancyFilterForm, StatusModelFilterFormMixin, RoleModelFilterFormMixin):
    model = IPAddress
    field_order = [
        "q",
        "parent",
        "ip_version",
        "mask_length",
        "vrfs",
        "present_in_vrf_id",
        "status",
        "role",
        "tenant_group",
        "tenant",
        "nat_inside",
        "has_nat_inside",
    ]
    q = forms.CharField(required=False, label="Search")
    parent = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(),
        required=False,
        label="Parent Prefix",
    )
    ip_version = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(IPAddressVersionChoices),
        label="IP version",
        widget=StaticSelect2(),
    )
    mask_length = forms.MultipleChoiceField(
        required=False,
        choices=IPADDRESS_MASK_LENGTH_CHOICES,
        label="Mask length",
        widget=StaticSelect2Multiple(),
    )
    vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label="Assigned VRF(s)",
        null_option="Global",
    )
    present_in_vrf_id = DynamicModelChoiceField(queryset=VRF.objects.all(), required=False, label="Present in VRF")
    type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(IPAddressTypeChoices),
        widget=StaticSelect2(),
    )
    tags = TagFilterField(model)
    nat_inside = DynamicModelChoiceField(queryset=IPAddress.objects.all(), required=False, label="NAT Inside Address")
    has_nat_inside = forms.NullBooleanField(
        required=False,
        label="Has NAT Inside",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )


#
# VLAN groups
#


class VLANGroupBulkEditForm(LocatableModelBulkEditFormMixin, NautobotBulkEditForm):
    """Bulk edit form for VLANGroup objects."""

    pk = forms.ModelMultipleChoiceField(queryset=VLANGroup.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    range = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = VLANGroup
        nullable_fields = ["location", "description"]


class VLANGroupForm(LocatableModelFormMixin, NautobotModelForm):
    class Meta:
        model = VLANGroup
        fields = [
            "location",
            "name",
            "range",
            "description",
            "tags",
        ]


class VLANGroupFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin):
    model = VLANGroup


#
# VLANs
#


class VLANForm(NautobotModelForm, TenancyForm):
    locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Locations",
        null_option="None",
        query_params={"content_type": VLAN._meta.label_lower},
    )
    vlan_group = DynamicModelChoiceField(
        queryset=VLANGroup.objects.all(),
        query_params={"location": "$locations"},
        required=False,
    )

    class Meta:
        model = VLAN
        fields = [
            "locations",
            "vlan_group",
            "vid",
            "name",
            "status",
            "role",
            "description",
            "tenant_group",
            "tenant",
            "tags",
        ]
        help_texts = {
            "locations": "Leave blank if this VLAN spans all locations",
            "vlan_group": "VLAN group (optional)",
            "vid": "Configured VLAN ID",
            "name": "Configured VLAN name",
            "status": "Operational status of this VLAN",
            "role": "The primary function of this VLAN",
        }

    def clean(self):
        vlan_group = self.cleaned_data["vlan_group"]
        locations = self.cleaned_data["locations"]
        # Validate Vlan Group Location is one of the ancestors of the VLAN locations specified.
        if vlan_group and vlan_group.location and locations:
            vlan_group_location = vlan_group.location
            is_vlan_group_valid = False
            for location in locations:
                if vlan_group_location in location.ancestors(include_self=True):
                    is_vlan_group_valid = True
                    break

            if not is_vlan_group_valid:
                locations = list(locations.values_list("name", flat=True))
                raise ValidationError(
                    {"vlan_group": [f"VLAN Group {vlan_group} is not in locations {locations} or their ancestors."]}
                )
        # Validation error raised in signal is not properly handled in form clean
        # Hence handling any validationError that might occur.
        try:
            return super().clean()
        except ValidationError as e:
            raise forms.ValidationError(e.message_dict) from e

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.locations.set(self.cleaned_data["locations"])
        return instance


class VLANBulkEditForm(
    TagsBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    RoleModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=VLAN.objects.all(), widget=forms.MultipleHiddenInput())
    vlan_group = DynamicModelChoiceField(
        queryset=VLANGroup.objects.all(),
        required=False,
        query_params={"location_id": "$location"},
    )
    add_locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(), required=False, query_params={"content_type": VLAN._meta.label_lower}
    )
    remove_locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(), required=False, query_params={"content_type": VLAN._meta.label_lower}
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = VLAN
        nullable_fields = [
            "vlan_group",
            "tenant",
            "description",
        ]


class VLANFilterForm(
    NautobotFilterForm,
    TenancyFilterForm,
    StatusModelFilterFormMixin,
    RoleModelFilterFormMixin,
):
    model = VLAN
    field_order = [
        "q",
        "locations",
        "vlan_group",
        "status",
        "role",
        "tenant_group",
        "tenant",
    ]
    q = forms.CharField(required=False, label="Search")
    locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
        query_params={"content_type": VLAN._meta.label_lower},
    )
    vlan_group = DynamicModelMultipleChoiceField(
        queryset=VLANGroup.objects.all(),
        required=False,
        label="VLAN group",
        null_option="None",
    )
    tags = TagFilterField(model)


#
# Services
#


class ServiceForm(NautobotModelForm):
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
    )
    virtual_machine = DynamicModelChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        label="Virtual Machine",
    )
    ports = NumericArrayField(
        base_field=forms.IntegerField(min_value=SERVICE_PORT_MIN, max_value=SERVICE_PORT_MAX),
        help_text="Comma-separated list of one or more port numbers. A range may be specified using a hyphen.",
    )
    ip_addresses = DynamicModelMultipleChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="IP addresses",
        query_params={"device_id": "$device", "virtual_machine_id": "$virtual_machine"},
    )

    class Meta:
        model = Service
        fields = [
            "name",
            "device",
            "virtual_machine",
            "protocol",
            "ports",
            "ip_addresses",
            "description",
            "tags",
        ]
        help_texts = {
            "ip_addresses": "IP address assignment is optional. If no IPs are selected, the service is assumed to be "
            "reachable via all IPs assigned to the device.",
        }
        widgets = {
            "protocol": StaticSelect2(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit IP address choices to those assigned to interfaces of the parent device/VM
        if self.instance.device:
            self.fields["ip_addresses"].queryset = IPAddress.objects.filter(
                interfaces__in=self.instance.device.vc_interfaces.values_list("id", flat=True)
            )
        elif self.instance.virtual_machine:
            self.fields["ip_addresses"].queryset = IPAddress.objects.filter(
                vm_interfaces__in=self.instance.virtual_machine.interfaces.values_list("id", flat=True)
            )
        else:
            self.fields["ip_addresses"].choices = []


class ServiceFilterForm(NautobotFilterForm):
    model = Service
    q = forms.CharField(required=False, label="Search")
    protocol = forms.ChoiceField(
        choices=add_blank_choice(ServiceProtocolChoices),
        required=False,
        widget=StaticSelect2Multiple(),
    )
    ports = forms.IntegerField(
        required=False,
    )
    tags = TagFilterField(model)


class ServiceBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Service.objects.all(), widget=forms.MultipleHiddenInput())
    protocol = forms.ChoiceField(
        choices=add_blank_choice(ServiceProtocolChoices),
        required=False,
        widget=StaticSelect2(),
    )
    ports = NumericArrayField(
        base_field=forms.IntegerField(min_value=SERVICE_PORT_MIN, max_value=SERVICE_PORT_MAX),
        required=False,
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "description",
        ]
