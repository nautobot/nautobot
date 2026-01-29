"""Forms for the vpn models."""

import logging

from django import forms

from nautobot.apps.forms import (
    add_blank_choice,
    APISelect,
    BulkEditNullBooleanSelect,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    JSONArrayFormField,
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    StaticSelect2,
    TagFilterField,
    TagsBulkEditFormMixin,
    StaticSelect2Multiple,
)
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import DynamicGroup, SecretsGroup
from nautobot.ipam.models import IPAddress, Prefix, RouteTarget, VLAN
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.virtualization.models import VMInterface

from . import choices
from . import models

logger = logging.getLogger(__name__)


class VPNProfileForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating VPNProfile."""

    secrets_group = DynamicModelChoiceField(
        queryset=SecretsGroup.objects.all(),
        required=False,
        label="Secrets Group",
        help_text="Secrets Group for the VPN Profile.",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNProfile
        fields = [
            "name",
            "description",
            "keepalive_interval",
            "keepalive_retries",
            "keepalive_enabled",
            "secrets_group",
            "role",
            "extra_options",
            "nat_traversal",
            "tenant_group",
            "tenant",
            "tags",
        ]


class VPNProfileBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPNProfile bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VPNProfile.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, label="Description")
    keepalive_interval = forms.IntegerField(
        min_value=0,
        required=False,
    )
    keepalive_retries = forms.IntegerField(
        min_value=0,
        required=False,
    )
    keepalive_enabled = forms.NullBooleanField(
        required=False, widget=BulkEditNullBooleanSelect, label="Keepalive Enabled"
    )
    nat_traversal = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Nat Traversal")

    class Meta:
        """Meta attributes."""

        model = models.VPNProfile
        nullable_fields = [
            "description",
            "keepalive_interval",
            "keepalive_retries",
        ]


VPNProfilePh1FormSet = forms.inlineformset_factory(
    parent_model=models.VPNProfile,
    model=models.VPNProfilePhase1PolicyAssignment,
    fields=("vpn_phase1_policy", "weight"),
    extra=1,
    widgets={
        "vpn_phase1_policy": APISelect(api_url="/api/vpn/vpn-phase-1-policies/"),
        "weight": forms.NumberInput(attrs={"class": "form-control"}),
    },
)


VPNProfilePh2FormSet = forms.inlineformset_factory(
    parent_model=models.VPNProfile,
    model=models.VPNProfilePhase2PolicyAssignment,
    fields=("vpn_phase2_policy", "weight"),
    extra=1,
    widgets={
        "vpn_phase2_policy": APISelect(api_url="/api/vpn/vpn-phase-2-policies/"),
        "weight": forms.NumberInput(attrs={"class": "form-control"}),
    },
)


class VPNProfileFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPNProfile."""

    model = models.VPNProfile
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class VPNPhase1PolicyForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating VPNPhase1Policy."""

    ike_version = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IkeVersionChoices),
        widget=StaticSelect2,
        label="IKE Version",
    )
    authentication_method = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.AuthenticationMethodChoices),
        widget=StaticSelect2,
        label="Authentication Method",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase1Policy
        fields = "__all__"


class VPNPhase1PolicyBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPNPhase1Policy bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VPNPhase1Policy.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, label="Description")
    ike_version = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IkeVersionChoices),
        widget=StaticSelect2,
        label="Ike Version",
    )
    aggressive_mode = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Aggressive Mode")
    encryption_algorithm = JSONArrayFormField(
        choices=choices.EncryptionAlgorithmChoices,
        base_field=forms.CharField(),
        required=False,
        label="Encryption Algorithm",
    )
    integrity_algorithm = JSONArrayFormField(
        choices=choices.IntegrityAlgorithmChoices,
        base_field=forms.CharField(),
        required=False,
        label="Integrity Algorithm",
    )
    dh_group = JSONArrayFormField(
        choices=choices.DhGroupChoices,
        base_field=forms.CharField(),
        required=False,
        label="Dh Group",
    )
    lifetime_seconds = forms.IntegerField(
        min_value=0,
        required=False,
    )
    lifetime_kb = forms.IntegerField(
        min_value=0,
        required=False,
    )
    authentication_method = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.AuthenticationMethodChoices),
        widget=StaticSelect2,
        label="Authentication Method",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase1Policy
        nullable_fields = [
            "description",
            "ike_version",
            "encryption_algorithm",
            "integrity_algorithm",
            "dh_group",
            "lifetime_seconds",
            "lifetime_kb",
            "authentication_method",
        ]


class VPNPhase1PolicyFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPNPhase1Policy."""

    model = models.VPNPhase1Policy
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class VPNPhase2PolicyForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating VPNPhase2Policy."""

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase2Policy
        fields = "__all__"


class VPNPhase2PolicyBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPNPhase2Policy bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VPNPhase2Policy.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, label="Description")
    encryption_algorithm = JSONArrayFormField(
        choices=choices.EncryptionAlgorithmChoices,
        base_field=forms.CharField(),
        required=False,
        label="Encryption Algorithm",
    )
    integrity_algorithm = JSONArrayFormField(
        choices=choices.IntegrityAlgorithmChoices,
        base_field=forms.CharField(),
        required=False,
        label="Integrity Algorithm",
    )
    pfs_group = JSONArrayFormField(
        choices=choices.DhGroupChoices,
        base_field=forms.CharField(),
        required=False,
        label="Pfs Group",
    )
    lifetime = forms.IntegerField(
        min_value=0,
        required=False,
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase2Policy
        nullable_fields = [
            "description",
            "encryption_algorithm",
            "integrity_algorithm",
            "pfs_group",
            "lifetime",
        ]


class VPNPhase2PolicyFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPNPhase2Policy."""

    model = models.VPNPhase2Policy
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class VPNForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating VPN."""

    vpn_profile = DynamicModelChoiceField(
        queryset=models.VPNProfile.objects.all(),
        required=False,
        label="VPN Profile",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPN
        fields = "__all__"


class VPNBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPN bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VPN.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, label="Description")
    vpn_profile = DynamicModelChoiceField(
        queryset=models.VPNProfile.objects.all(),
        required=False,
        label="VPN Profile",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPN
        nullable_fields = [
            "description",
            "vpn_profile",
        ]


class VPNFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPN."""

    model = models.VPN
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class VPNTunnelForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating VPNTunnel."""

    vpn_profile = DynamicModelChoiceField(
        queryset=models.VPNProfile.objects.all(),
        required=False,
        label="VPN Profile",
    )
    vpn = DynamicModelChoiceField(
        queryset=models.VPN.objects.all(),
        required=False,
        label="VPN",
    )
    encapsulation = forms.ChoiceField(
        required=True,
        choices=add_blank_choice(choices.EncapsulationChoices),
        widget=StaticSelect2,
        label="Encapsulation",
    )
    endpoint_a = DynamicModelChoiceField(
        queryset=models.VPNTunnelEndpoint.objects.all(),
        required=False,
        label="Endpoint A",
    )
    endpoint_z = DynamicModelChoiceField(
        queryset=models.VPNTunnelEndpoint.objects.all(),
        required=False,
        label="Endpoint Z",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnel
        fields = "__all__"


class VPNTunnelBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPNTunnel bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VPNTunnel.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, label="Description")
    vpn_profile = DynamicModelChoiceField(
        queryset=models.VPNProfile.objects.all(),
        required=False,
        label="VPN Profile",
    )
    vpn = DynamicModelChoiceField(
        queryset=models.VPN.objects.all(),
        required=False,
        label="VPN",
    )
    encapsulation = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.EncapsulationChoices),
        widget=StaticSelect2,
        label="Encapsulation",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnel
        nullable_fields = [
            "vpn_profile",
            "vpn",
            "description",
            "encapsulation",
        ]


class VPNTunnelFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPNTunnel."""

    model = models.VPNTunnel
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class VPNTunnelEndpointForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating VPNTunnelEndpoint."""

    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Device",
    )
    source_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        label="Source Interface",
        query_params={
            "device": "$device",
        },
    )
    source_ipaddress = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="Source IP Address",
        query_params={
            "interfaces": "$source_interface",
        },
    )
    tunnel_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        label="Tunnel Interface",
        query_params={
            "device": "$device",
            "type": InterfaceTypeChoices.TYPE_TUNNEL,
        },
        help_text="Interface must be of type Tunnel",
    )
    vpn_profile = DynamicModelChoiceField(
        queryset=models.VPNProfile.objects.all(),
        required=False,
        label="VPN Profile",
        help_text="VPN Profile for the tunnel endpoint.",
    )
    protected_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(),
        required=False,
        label="Protected Prefixes",
        help_text="Protected Prefixes behind the tunnel endpoint.",
    )
    protected_prefixes_dg = DynamicModelMultipleChoiceField(
        queryset=DynamicGroup.objects.all(),
        required=False,
        label="Protected Prefixes Dynamic Group",
        to_field_name="name",
        query_params={"content_type": "ipam.prefix"},
        help_text="Protected Prefixes behind the tunnel endpoint.",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnelEndpoint
        fields = "__all__"


class VPNTunnelEndpointBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPNTunnelEndpoint bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.VPNTunnelEndpoint.objects.all(), widget=forms.MultipleHiddenInput
    )
    vpn_profile = DynamicModelChoiceField(
        queryset=models.VPNProfile.objects.all(),
        required=False,
        label="VPN Profile",
        help_text="VPN Profile for the tunnel endpoint.",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnelEndpoint
        nullable_fields = [
            "vpn_profile",
        ]


class VPNTunnelEndpointFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPNTunnelEndpoint."""

    model = models.VPNTunnelEndpoint
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


#
# L2VPN Forms
#


class L2VPNForm(NautobotModelForm):
    """Form for creating and updating L2VPN."""

    import_targets = DynamicModelMultipleChoiceField(
        queryset=RouteTarget.objects.all(),
        required=False,
        label="Import Targets",
    )
    export_targets = DynamicModelMultipleChoiceField(
        queryset=RouteTarget.objects.all(),
        required=False,
        label="Export Targets",
    )

    class Meta:
        model = models.L2VPN
        fields = [
            "name",
            "slug",
            "type",
            "status",
            "identifier",
            "description",
            "import_targets",
            "export_targets",
            "tenant",
            "tags",
        ]


class L2VPNBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """L2VPN bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.L2VPN.objects.all(),
        widget=forms.MultipleHiddenInput
    )
    type = forms.ChoiceField(
        choices=add_blank_choice(choices.L2VPNTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    identifier = forms.IntegerField(required=False)
    description = forms.CharField(required=False)

    class Meta:
        model = models.L2VPN
        nullable_fields = ["identifier", "description", "tenant"]


class L2VPNFilterForm(NautobotFilterForm, TenancyFilterForm):
    """Filter form for L2VPN list view."""

    model = models.L2VPN
    q = forms.CharField(required=False, label="Search")
    type = forms.MultipleChoiceField(
        choices=choices.L2VPNTypeChoices,
        required=False,
        widget=StaticSelect2Multiple(),
    )
    tags = TagFilterField(model)


class L2VPNTerminationForm(forms.ModelForm):
    """Form for creating and updating L2VPNTermination.

    Note: Uses plain Django ModelForm to avoid complexity with GenericForeignKey handling.
    """
    # The model has ONE generic field (assigned_object)
    # But the form has THREE separate fields for UI
    # VLAN,Interface,VM Interface
    # self.instance.assigned_object = selected_one
    # L2VPNTermination Model
    # assigned_object_type = ContentType (auto)
    # assigned_object_id = UUID (auto)
    #assigned_object = GenericFK (the actual object)
    l2vpn = DynamicModelChoiceField(
        queryset=models.L2VPN.objects.all(),
        required=True,
        label="L2VPN",
    )
    vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="VLAN",
    )
    interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
        label="Interface",
    )
    vminterface = DynamicModelChoiceField(
        queryset=VMInterface.objects.all(),
        required=False,
        label="VM Interface",
    )

    class Meta:
        model = models.L2VPNTermination
        fields = ["l2vpn"]

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        initial = kwargs.get("initial", {}).copy()
        # If editing existing termination, pre-populate the right field
        if instance and instance.pk:
            if isinstance(instance.assigned_object, Interface):
                initial["interface"] = instance.assigned_object
            elif isinstance(instance.assigned_object, VLAN):
                initial["vlan"] = instance.assigned_object
            elif isinstance(instance.assigned_object, VMInterface):
                initial["vminterface"] = instance.assigned_object
            kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        # Rule 1: At least one must be selected
        # Rule 2: Only ONE can be selected
        interface = self.cleaned_data.get("interface")
        vminterface = self.cleaned_data.get("vminterface")
        vlan = self.cleaned_data.get("vlan")

        if not (interface or vminterface or vlan):
            raise forms.ValidationError(
                "Must specify an interface or VLAN."
            )

        selected = [x for x in (interface, vminterface, vlan) if x]
        if len(selected) > 1:
            raise forms.ValidationError(
                "Can only have one terminating object."
            )
        # Set the model's assigned_object to whichever was selected
        self.instance.assigned_object = interface or vminterface or vlan


class L2VPNTerminationFilterForm(NautobotFilterForm):
    """Filter form for L2VPNTermination list view."""

    model = models.L2VPNTermination
    q = forms.CharField(required=False, label="Search")
    l2vpn = DynamicModelChoiceField(
        queryset=models.L2VPN.objects.all(),
        required=False,
        label="L2VPN",
    )
