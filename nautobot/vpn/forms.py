"""Forms for the vpn models."""

import logging

from django import forms

from nautobot.apps.forms import (
    add_blank_choice,
    APISelect,
    BulkEditNullBooleanSelect,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    StaticSelect2,
    TagFilterField,
    TagsBulkEditFormMixin,
)
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import DynamicGroup, SecretsGroup
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm

from . import choices, models

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
    name = forms.CharField(required=False, label="Name")
    description = forms.CharField(required=False, label="Description")
    keepalive_enabled = forms.NullBooleanField(
        required=False, widget=BulkEditNullBooleanSelect, label="Keepalive Enabled"
    )
    nat_traversal = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Nat Traversal")

    class Meta:
        """Meta attributes."""

        model = models.VPNProfile
        nullable_fields = [
            # TODO INIT Add any fields that should be nullable
            # "vpn_phase1_policy",
            # "vpn_phase2_policy",
            "description",
            "keepalive_interval",
            "keepalive_retries",
            "extra_options",
            "secrets_group",
            "role",
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
    encryption_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.EncryptionAlgorithmChoices),
        widget=StaticSelect2,
        label="Encryption Algorithm",
    )
    integrity_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IntegrityAlgorithmChoices),
        widget=StaticSelect2,
        label="Integrity Algorithm",
    )
    dh_group = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.DhGroupChoices),
        widget=StaticSelect2,
        label="Diffie-Hellman Group",
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
    name = forms.CharField(required=False, label="Name")
    description = forms.CharField(required=False, label="Description")
    ike_version = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IkeVersionChoices),
        widget=StaticSelect2,
        label="Ike Version",
    )
    aggressive_mode = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Aggressive Mode")
    encryption_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.EncryptionAlgorithmChoices),
        widget=StaticSelect2,
        label="Encryption Algorithm",
    )
    integrity_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IntegrityAlgorithmChoices),
        widget=StaticSelect2,
        label="Integrity Algorithm",
    )
    dh_group = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.DhGroupChoices),
        widget=StaticSelect2,
        label="Dh Group",
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
            "aggressive_mode",
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

    encryption_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.EncryptionAlgorithmChoices),
        widget=StaticSelect2,
        label="Encryption Algorithm",
    )
    integrity_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IntegrityAlgorithmChoices),
        widget=StaticSelect2,
        label="Integrity Algorithm",
    )
    pfs_group = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.DhGroupChoices),
        widget=StaticSelect2,
        label="PFS Group",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase2Policy
        fields = "__all__"


class VPNPhase2PolicyBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VPNPhase2Policy bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VPNPhase2Policy.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(required=False, label="Name")
    description = forms.CharField(required=False, label="Description")
    encryption_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.EncryptionAlgorithmChoices),
        widget=StaticSelect2,
        label="Encryption Algorithm",
    )
    integrity_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.IntegrityAlgorithmChoices),
        widget=StaticSelect2,
        label="Integrity Algorithm",
    )
    pfs_group = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.DhGroupChoices),
        widget=StaticSelect2,
        label="Pfs Group",
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
    name = forms.CharField(required=False, label="Name")
    description = forms.CharField(required=False, label="Description")
    vpn_id = forms.CharField(required=False, label="Vpn Id")

    class Meta:
        """Meta attributes."""

        model = models.VPN
        nullable_fields = [
            "vpn_profile",
            "description",
            "vpn_id",
            "tenant",
            "role",
            "contact_associations",
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
    name = forms.CharField(required=False, label="Name")
    description = forms.CharField(required=False, label="Description")
    tunnel_id = forms.CharField(required=False, label="Tunnel Id")
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
            "tunnel_id",
            "encapsulation",
            "tenant",
            "role",
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
        label="Protected Prefixes (from Dynamic Group)",
        to_field_name="name",
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
    source_fqdn = forms.CharField(required=False, label="Source Fqdn")
    protected_prefixes_dg = DynamicModelMultipleChoiceField(
        queryset=DynamicGroup.objects.all(),
        required=False,
        label="Dynamic Group",
        # TODO INIT defaulting to the common field `name`, you may want to change this.
        to_field_name="name",
    )
    protected_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(),
        required=False,
        label="Prefix",
        # TODO INIT defaulting to the common field `name`, you may want to change this.
        to_field_name="name",
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnelEndpoint
        nullable_fields = [
            # TODO INIT Add any fields that should be nullable
            "vpn_profile",
            "source_ipaddress",
            "source_interface",
            "source_fqdn",
            "tunnel_interface",
            "protected_prefixes_dg",
            "protected_prefixes",
            "role",
            "status",
        ]


class VPNTunnelEndpointFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for VPNTunnelEndpoint."""

    model = models.VPNTunnelEndpoint
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)
