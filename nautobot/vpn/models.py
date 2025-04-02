from django.db import models

from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import BaseModel, extras_features, PrimaryModel, StatusField
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
    """VPNProfile model for nautobot_vpn_models."""

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
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True, help_text="Name")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Description")
    keepalive_enabled = models.BooleanField(
        # TODO INIT Confirm the default value
        default=False,
        help_text="Keepalive enabled",
    )
    keepalive_interval = models.PositiveIntegerField(blank=True, null=True, help_text="Keepalive interval")
    keepalive_retries = models.PositiveIntegerField(blank=True, null=True, help_text="Keepalive retries")
    nat_traversal = models.BooleanField(
        # TODO INIT Confirm the default value
        default=False,
        help_text="NAT traversal",
    )
    extra_options = models.JSONField(blank=True, null=True, help_text="Extra options")
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        related_name="vpn_profiles",
        default=None,
        blank=True,
        null=True,
    )
    role = RoleField(blank=True, null=True)

    # TODO INIT Nautobot recommends that all models have a tenant field, unless you have a good reason not to.
    # tenant = models.ForeignKey(
    #     to="tenancy.Tenant",
    #     on_delete=models.PROTECT,
    #     related_name="vpn_profiles",
    #     blank=True,
    #     null=True,
    # )

    class Meta:
        """Meta class for VPNProfile."""

        # TODO INIT Confirm the verbose_name of the model
        verbose_name = "VPN Profile"

    # TODO INIT Confirm the string representation of the model
    def __str__(self):
        """Stringify instance."""
        return self.name

    @property
    def priority_ph1_policy(self):
        # TODO add trough-table with weight.
        return "return with highest prio"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VPNPhase1Policy(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNPhase1Policy model for nautobot_vpn_models."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True, help_text="Name")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Description")
    ike_version = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, choices=choices.IkeVersionChoices, blank=True, help_text="IKE version"
    )
    aggressive_mode = models.BooleanField(
        # TODO INIT Confirm the default value
        default=False,
        help_text="Use aggressive mode",
    )
    encryption_algorithm = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.EncryptionAlgorithmChoices,
        blank=True,
        help_text="AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES",
    )
    integrity_algorithm = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.IntegrityAlgorithmChoices,
        blank=True,
        help_text="SHA512, SHA384, SHA256, SHA1, MD5",
    )
    dh_group = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, choices=choices.DhGroupChoices, blank=True, help_text="Diffie-Hellman group"
    )
    lifetime_seconds = models.PositiveIntegerField(blank=True, null=True, help_text="Lifetime in seconds")
    lifetime_kb = models.PositiveIntegerField(blank=True, null=True, help_text="Lifetime in kiolbytes")
    authentication_method = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.AuthenticationMethodChoices,
        blank=True,
        help_text="PSK, RSA, ECDSA, Certificate",
    )
    # TODO INIT Nautobot recommends that all models have a tenant field, unless you have a good reason not to.
    # tenant = models.ForeignKey(
    #     to="tenancy.Tenant",
    #     on_delete=models.PROTECT,
    #     related_name="vpn_phase_1_policys",
    #     blank=True,
    #     null=True,
    # )

    class Meta:
        """Meta class for VPNPhase1Policy."""

        # TODO INIT Confirm the verbose_name of the model
        verbose_name = "VPN Phase 1 Policy"

    # TODO INIT Confirm the string representation of the model
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
    """VPNPhase2Policy model for nautobot_vpn_models."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True, help_text="Name")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Description")
    encryption_algorithm = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.EncryptionAlgorithmChoices,
        blank=True,
        help_text="AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES",
    )
    integrity_algorithm = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.IntegrityAlgorithmChoices,
        blank=True,
        help_text="SHA512, SHA384, SHA256, SHA1, MD5",
    )
    pfs_group = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.DhGroupChoices,
        blank=True,
        help_text="Perfect Forward Secrecy group",
    )
    lifetime = models.PositiveIntegerField(blank=True, null=True, help_text="Lifetime in seconds")
    # TODO INIT Nautobot recommends that all models have a tenant field, unless you have a good reason not to.
    # tenant = models.ForeignKey(
    #     to="tenancy.Tenant",
    #     on_delete=models.PROTECT,
    #     related_name="vpn_phase_2_policys",
    #     blank=True,
    #     null=True,
    # )

    class Meta:
        """Meta class for VPNPhase2Policy."""

        # TODO INIT Confirm the verbose_name of the model
        verbose_name = "VPN Phase 2 Policy"

    # TODO INIT Confirm the string representation of the model
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
    """VPN model for nautobot_vpn_models."""

    vpn_profile = models.ForeignKey(
        to="vpn.VPNProfile",
        on_delete=models.PROTECT,
        related_name="vpns",
        default=None,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True, help_text="Name")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Description")
    vpn_id = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="VPN ID")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpns",
        blank=True,
        null=True,
    )
    role = RoleField(blank=True, null=True)
    # contact_associations = models.ManyToManyField(
    #     to="extras.ContactAssociations",
    #     related_name="vpns",
    #     verbose_name="Contact Associations",
    #     blank=True,
    #     null=True,
    #     help_text="Contact Associations"
    # )  # TODO should come from PrimaryModel

    class Meta:
        """Meta class for VPN."""

        # TODO INIT Confirm the verbose_name of the model
        verbose_name = "VPN"

    # TODO INIT Confirm the string representation of the model
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
    """VPNTunnel model for nautobot_vpn_models."""

    vpn_profile = models.ForeignKey(
        to="vpn.VPNProfile",
        on_delete=models.PROTECT,
        related_name="vpn_tunnels",
        blank=False,
        null=False,
        verbose_name="VPN Profile",
    )
    vpn = models.ForeignKey(
        to="vpn.VPN",
        on_delete=models.CASCADE,
        related_name="vpn_tunnels",
        blank=False,
        null=False,
        verbose_name="VPN",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True, help_text="Name")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Description")
    tunnel_id = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Tunnel ID")
    encapsulation = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=choices.EncapsulationChoices,
        blank=True,
        help_text="IPsec - Transport, IPsec - Tunnel, IP-in-IP, GRE, WireGuard, L2TP, PPTP, OpenVPN, EoIP",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnels",
        blank=True,
        null=True,
    )
    role = RoleField(blank=False, null=False)
    # contact_associations = models.ManyToManyField(
    #     to="extras.ContactAssociations",
    #     related_name="vpn_tunnels",
    #     verbose_name="Contact Associations",
    #     blank=True,
    #     null=True,
    #     help_text="Contact Associations"
    # )  # TODO should come from PrimaryModel
    status = StatusField(blank=False, null=False)

    class Meta:
        """Meta class for VPNTunnel."""

        # TODO INIT Confirm the verbose_name of the model
        verbose_name = "VPN Tunnel"

    # TODO INIT Confirm the string representation of the model
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
class VPNTunnelEndpoint(PrimaryModel):  # pylint: disable=too-many-ancestors
    """VPNTunnelEndpoint model for nautobot_vpn_models."""

    vpn_profile = models.ForeignKey(
        to="vpn.VPNProfile",
        on_delete=models.PROTECT,
        related_name="vpn_tunnel_endpoints",
        blank=False,
        null=False,
        verbose_name="VPN Profile",
    )
    vpn_tunnel = models.ForeignKey(
        to="vpn.VPNTunnel",
        on_delete=models.CASCADE,  # TODO add protection mechanism for hub and spoke.
        related_name="vpn_tunnel_endpoints",
        blank=False,
        null=False,
        verbose_name="VPN Tunnel",
    )
    source_ipaddress = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.PROTECT,
        related_name="vpn_tunnel_endpoints_src_ip",
        blank=True,
        null=True,
        verbose_name="Source IP Address",
    )  # TODO add validation source_ipaddress or source_interface must be defined.
    source_interface = models.OneToOneField(
        to="dcim.Interface",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnel_endpoints_src_int",
        blank=True,
        null=True,
        verbose_name="Source Interface",
    )
    destination_ipaddress = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnel_endpoints_dst_ip",
        blank=True,
        null=True,
        verbose_name="Destination IP Address",
    )
    destination_fqdn = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Destination FQDN")
    tunnel_interface = models.OneToOneField(
        to="dcim.Interface",
        on_delete=models.SET_NULL,
        related_name="vpn_tunnel_endpoints_tunnel",
        blank=True,
        null=True,
        verbose_name="Tunnel Interface",
    )
    protected_prefixes_dg = models.ManyToManyField(
        to="extras.DynamicGroup",
        related_name="vpn_tunnel_endpoints",
        verbose_name="Dynamic Group",
        blank=True,
        help_text="Protected Prefixes in Dynamic Groups",
    )
    protected_prefixes = models.ManyToManyField(
        to="ipam.Prefix",
        related_name="vpn_tunnel_endpoints",
        verbose_name="Prefix",
        blank=True,
        help_text="Protected Prefixes",
    )
    role = RoleField(blank=True, null=True)
    # contact_associations = models.ManyToManyField(
    #     to="extras.ContactAssociations",
    #     related_name="vpn_tunnel_endpoints",
    #     verbose_name="Contact Associations",
    #     blank=True,
    #     null=True,
    #     help_text="Contact Associations"
    # )
    # TODO INIT Nautobot recommends that all models have a tenant field, unless you have a good reason not to.
    # tenant = models.ForeignKey(
    #     to="tenancy.Tenant",
    #     on_delete=models.PROTECT,
    #     related_name="vpn_tunnel_endpoints",
    #     blank=True,
    #     null=True,
    # )

    class Meta:
        """Meta class for VPNTunnelEndpoint."""

        # TODO INIT Confirm the verbose_name of the model
        verbose_name = "VPN Tunnel Endpoint"

    # TODO INIT Confirm the string representation of the model

    @property
    def name(self):
        return f"{self.vpn_tunnel.name} --> {self.source_ipaddress.address}"  # TODO IP or source interface.

    def __str__(self):
        """Stringify instance."""
        return self.name
