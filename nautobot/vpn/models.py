from django.core.exceptions import ValidationError
from django.db import models

from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import BaseModel, extras_features, JSONArrayField, PrimaryModel, StatusField
from nautobot.extras.models import RoleField
from nautobot.vpn import choices


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VPNProfile(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNProfile model."""

    vpn_phase1_policies = models.ManyToManyField(
        to="vpn.VPNPhase1Policy",
        related_name="vpn_profiles",
        verbose_name="VPN Phase 1 Policy",
        through="vpn.VPNProfilePhase1PolicyAssignment",
        blank=True,
        help_text="Phase 1 Policy",
    )
    vpn_phase2_policies = models.ManyToManyField(
        to="vpn.VPNPhase2Policy",
        related_name="vpn_profiles",
        verbose_name="VPN Phase 2 Policy",
        through="vpn.VPNProfilePhase2PolicyAssignment",
        blank=True,
        help_text="Phase 2 Policy",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    role = RoleField(blank=True, null=True)
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        related_name="vpn_profiles",
        default=None,
        blank=True,
        null=True,
    )
    keepalive_enabled = models.BooleanField(default=False, verbose_name="Enable keepalive")
    keepalive_interval = models.PositiveIntegerField(blank=True, null=True)
    keepalive_retries = models.PositiveIntegerField(blank=True, null=True)
    nat_traversal = models.BooleanField(default=False, verbose_name="Enable NAT Traversal")
    extra_options = models.JSONField(
        blank=True, null=True, help_text="Additional options specific to the VPN technology and/or implementation"
    )

    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpn_profiles",
        blank=True,
        null=True,
    )

    clone_fields = [
        "description",
        "role",
        "secrets_group",
        "keepalive_enabled",
        "keepalive_interval",
        "keepalive_retries",
        "nat_traversal",
        "extra_options",
    ]

    class Meta:
        """Meta class for VPNProfile."""

        ordering = ("name",)
        verbose_name = "VPN Profile"

    def __str__(self):
        """Stringify instance."""
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VPNPhase1Policy(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNPhase1Policy model."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    ike_version = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, choices=choices.IkeVersionChoices, blank=True, verbose_name="IKE version"
    )
    aggressive_mode = models.BooleanField(
        default=False,
        help_text="Only applicable to IKEv1",
    )
    encryption_algorithm = JSONArrayField(
        base_field=models.CharField(choices=choices.EncryptionAlgorithmChoices),
        blank=True,
        null=True,
    )
    integrity_algorithm = JSONArrayField(
        base_field=models.CharField(choices=choices.IntegrityAlgorithmChoices),
        blank=True,
        null=True,
    )
    dh_group = JSONArrayField(
        base_field=models.CharField(choices=choices.DhGroupChoices),
        blank=True,
        null=True,
        verbose_name="Diffie-Hellman group",
    )
    lifetime_seconds = models.PositiveIntegerField(blank=True, null=True, verbose_name="Lifetime (seconds)")
    lifetime_kb = models.PositiveIntegerField(blank=True, null=True, verbose_name="Lifetime (kilobytes)")
    authentication_method = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.AuthenticationMethodChoices,
        blank=True,
        help_text="PSK, RSA, ECDSA, Certificate",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpn_phase_1_policies",
        blank=True,
        null=True,
    )

    clone_fields = [
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

    class Meta:
        """Meta class for VPNPhase1Policy."""

        ordering = ("name",)
        verbose_name = "VPN Phase 1 Policy"
        verbose_name_plural = "VPN Phase 1 Policies"

    def __str__(self):
        """Stringify instance."""
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VPNPhase2Policy(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNPhase2Policy model."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    encryption_algorithm = JSONArrayField(
        base_field=models.CharField(choices=choices.EncryptionAlgorithmChoices),
        blank=True,
        null=True,
    )
    integrity_algorithm = JSONArrayField(
        base_field=models.CharField(choices=choices.IntegrityAlgorithmChoices),
        blank=True,
        null=True,
    )
    pfs_group = JSONArrayField(
        base_field=models.CharField(choices=choices.DhGroupChoices),
        blank=True,
        null=True,
        verbose_name="PFS group",
    )
    lifetime = models.PositiveIntegerField(blank=True, null=True, verbose_name="Lifetime (seconds)")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpn_phase_2_policies",
        blank=True,
        null=True,
    )

    clone_fields = [
        "description",
        "encryption_algorithm",
        "integrity_algorithm",
        "pfs_group",
        "lifetime",
    ]

    class Meta:
        """Meta class for VPNPhase2Policy."""

        ordering = ("name",)
        verbose_name = "VPN Phase 2 Policy"
        verbose_name_plural = "VPN Phase 2 Policies"

    def __str__(self):
        """Stringify instance."""
        return self.name


@extras_features("graphql")
class VPNProfilePhase1PolicyAssignment(BaseModel):
    vpn_profile = models.ForeignKey(
        "vpn.VPNProfile", on_delete=models.CASCADE, related_name="vpn_profile_phase1_policy_assignments"
    )
    vpn_phase1_policy = models.ForeignKey(
        "vpn.VPNPhase1Policy", on_delete=models.CASCADE, related_name="vpn_profile_phase1_policy_assignments"
    )
    weight = models.PositiveIntegerField(default=100, help_text="Higher weights appear later in the list")
    is_metadata_associable_model = False
    documentation_static_path = "docs/user-guide/core-data-model/vpn/vpnprofile.html"

    class Meta:
        unique_together = ["vpn_profile", "vpn_phase1_policy"]
        ordering = ["weight", "vpn_profile", "vpn_phase1_policy"]

    def __str__(self):
        return f"{self.vpn_profile}: {self.vpn_phase1_policy}"


@extras_features("graphql")
class VPNProfilePhase2PolicyAssignment(BaseModel):
    vpn_profile = models.ForeignKey(
        "vpn.VPNProfile", on_delete=models.CASCADE, related_name="vpn_profile_phase2_policy_assignments"
    )
    vpn_phase2_policy = models.ForeignKey(
        "vpn.VPNPhase2Policy", on_delete=models.CASCADE, related_name="vpn_profile_phase2_policy_assignments"
    )
    weight = models.PositiveIntegerField(default=100, help_text="Higher weights appear later in the list")
    is_metadata_associable_model = False
    documentation_static_path = "docs/user-guide/core-data-model/vpn/vpnprofile.html"

    class Meta:
        unique_together = ["vpn_profile", "vpn_phase2_policy"]
        ordering = ["weight", "vpn_profile", "vpn_phase2_policy"]

    def __str__(self):
        return f"{self.vpn_profile}: {self.vpn_phase2_policy}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VPN(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPN model."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    vpn_id = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, verbose_name="VPN ID")
    vpn_profile = models.ForeignKey(
        to="vpn.VPNProfile",
        on_delete=models.PROTECT,
        related_name="vpns",
        default=None,
        blank=True,
        null=True,
        verbose_name="VPN Profile",
    )
    role = RoleField(blank=True, null=True)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpns",
        blank=True,
        null=True,
    )

    clone_fields = [
        "description",
        "vpn_id",
        "vpn_profile",
        "role",
        "tenant",
    ]

    class Meta:
        """Meta class for VPN."""

        ordering = ("name",)
        verbose_name = "VPN"

    def __str__(self):
        """Stringify instance."""
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class VPNTunnel(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNTunnel model."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    tunnel_id = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, verbose_name="Tunnel ID")
    vpn_profile = models.ForeignKey(
        to="vpn.VPNProfile",
        on_delete=models.PROTECT,
        related_name="vpn_tunnels",
        blank=True,
        null=True,
        verbose_name="VPN Profile",
    )
    vpn = models.ForeignKey(
        to="vpn.VPN",
        on_delete=models.CASCADE,
        related_name="vpn_tunnels",
        blank=True,
        null=True,
        verbose_name="VPN",
        help_text="VPN to which this tunnel belongs",
    )
    status = StatusField(blank=False, null=False)
    role = RoleField(blank=True, null=True)
    encapsulation = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.EncapsulationChoices,
        blank=True,
    )
    endpoint_a = models.ForeignKey(
        to="vpn.VPNTunnelEndpoint",
        on_delete=models.SET_NULL,
        related_name="endpoint_a_vpn_tunnels",
        blank=True,
        null=True,
        verbose_name="Endpoint A",
        help_text="Tunnel termination A",
    )
    endpoint_z = models.ForeignKey(
        to="vpn.VPNTunnelEndpoint",
        on_delete=models.SET_NULL,
        related_name="endpoint_z_vpn_tunnels",
        blank=True,
        null=True,
        verbose_name="Endpoint Z",
        help_text="Tunnel termination Z",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnels",
        blank=True,
        null=True,
    )

    clone_fields = [
        "description",
        "vpn",
        "tunnel_id",
        "encapsulation",
        "endpoint_a",
        "endpoint_z",
        "status",
        "vpn_profile",
        "tenant",
        "role",
    ]

    class Meta:
        """Meta class for VPNTunnel."""

        ordering = ("name",)
        verbose_name = "VPN Tunnel"

    def __str__(self):
        """Stringify instance."""
        return self.name

    def clean(self):
        if self.endpoint_a and self.endpoint_z and self.endpoint_a == self.endpoint_z:
            raise ValidationError("Endpoint A and Endpoint Z cannot be the same.")
        return super().clean()


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VPNTunnelEndpoint(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNTunnelEndpoint model."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, editable=False)
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="vpn_tunnel_endpoints",
        blank=True,
        null=True,
        verbose_name="Device",
    )
    source_interface = models.OneToOneField(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="vpn_tunnel_endpoints_src_int",
        blank=True,
        null=True,
        verbose_name="Source Interface",
    )
    source_ipaddress = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnel_endpoints_src_ip",
        blank=True,
        null=True,
        verbose_name="Source IP Address",
        help_text="Mutually Exclusive with Source FQDN.",
    )
    source_fqdn = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        verbose_name="Source FQDN",
        help_text="Mutually Exclusive with Source IP Address",
    )
    tunnel_interface = models.OneToOneField(
        to="dcim.Interface",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnel_endpoints_tunnel",
        blank=True,
        null=True,
        verbose_name="Tunnel Interface",
    )
    vpn_profile = models.ForeignKey(
        to="vpn.VPNProfile",
        on_delete=models.PROTECT,
        related_name="vpn_tunnel_endpoints",
        blank=True,
        null=True,
        verbose_name="VPN Profile",
    )
    role = RoleField(blank=True, null=True)
    protected_prefixes = models.ManyToManyField(
        to="ipam.Prefix",
        related_name="vpn_tunnel_endpoints",
        blank=True,
        verbose_name="Protected Prefixes",
    )
    protected_prefixes_dg = models.ManyToManyField(
        to="extras.DynamicGroup",
        related_name="vpn_tunnel_endpoints",
        blank=True,
        verbose_name="Protected Prefixes Dynamic Group",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnel_endpoints",
        blank=True,
        null=True,
    )

    clone_fields = [
        "vpn_profile",
        "device",
        "source_interface",
        "source_ipaddress",
        "source_fqdn",
        "protected_prefixes",
        "protected_prefixes_dg",
    ]

    natural_key_field_names = ["pk"]  # TODO: name is not unique, nor are there any uniqueness criteria on this model?

    class Meta:
        """Meta class for VPNTunnelEndpoint."""

        ordering = ("name",)
        verbose_name = "VPN Tunnel Endpoint"

    def _name(self):
        """Dynamic name field."""
        if self.source_interface:
            parent_intf = f"{self.source_interface.parent.name} {self.source_interface.name}"
            if self.source_ipaddress:
                return f"{parent_intf} ({self.source_ipaddress.address})"
            return parent_intf
        return self.source_fqdn

    def __str__(self):
        """Stringify instance."""
        return self.name

    def clean(self):
        if self.source_ipaddress and self.source_fqdn:
            raise ValidationError("Source IP Address and Source FQDN are mutually exclusive fields. Select only one.")
        if not any([self.source_interface, self.source_ipaddress, self.source_fqdn]):
            raise ValidationError("Source Interface or Source IP Address or Source FQDN Is required.")
        if self.source_interface and not self.source_interface.parent:
            raise ValidationError("Source Interface must belong to a device.")
        if (
            self.source_ipaddress
            and self.source_interface
            and (self.source_ipaddress not in self.source_interface.ip_addresses.all())
        ):
            raise ValidationError("Source IP address must be assigned to Source Interface.")
        if (
            self.tunnel_interface
            and self.source_interface
            and (self.tunnel_interface not in self.source_interface.parent.all_interfaces)
        ):
            raise ValidationError("Tunnel Interface and Source Interface must be on the same device")
        return super().clean()

    def save(self, *args, **kwargs):
        if self.source_interface:
            self.device = self.source_interface.parent
        self.name = self._name()
        super().save(*args, **kwargs)
