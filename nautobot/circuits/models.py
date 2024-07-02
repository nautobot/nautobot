from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.dcim.fields import ASNField
from nautobot.dcim.models import CableTermination, PathEndpoint
from nautobot.extras.models import StatusField
from nautobot.extras.utils import extras_features

from nautobot.core.models.generics import OrganizationalModel, PrimaryModel  # isort: skip - avoid circular imports

from .choices import CircuitTerminationSideChoices

__all__ = (
    "Circuit",
    "CircuitTermination",
    "CircuitType",
    "Provider",
    "ProviderNetwork",
)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ProviderNetwork(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    provider = models.ForeignKey(to="circuits.Provider", on_delete=models.PROTECT, related_name="provider_networks")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("provider", "name")
        constraints = (
            models.UniqueConstraint(fields=("provider", "name"), name="circuits_providernetwork_provider_name"),
        )
        unique_together = ("provider", "name")

    def __str__(self):
        return self.name

    @property
    def display(self):
        return f"{self.provider} {self.name}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class Provider(PrimaryModel):
    """
    Each Circuit belongs to a Provider. This is usually a telecommunications company or similar organization. This model
    stores information pertinent to the user's relationship with the Provider.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    asn = ASNField(
        blank=True,
        null=True,
        verbose_name="ASN",
        help_text="32-bit autonomous system number",
    )
    # todoindex:
    account = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, verbose_name="Account number")
    portal_url = models.URLField(blank=True, verbose_name="Portal URL")
    noc_contact = models.TextField(blank=True, verbose_name="NOC contact")
    admin_contact = models.TextField(blank=True, verbose_name="Admin contact")
    comments = models.TextField(blank=True)

    clone_fields = [
        "asn",
        "account",
        "portal_url",
        "noc_contact",
        "admin_contact",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features("custom_validators", "graphql")
class CircuitType(OrganizationalModel):
    """
    Circuits can be organized by their functional role. For example, a user might wish to define CircuitTypes named
    "Long Haul," "Metro," or "Out-of-Band".
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class Circuit(PrimaryModel):
    """
    A communications circuit connects two points.
    Each Circuit belongs to a Provider; Providers may have multiple circuits.
    Each circuit is also assigned a CircuitType.
    Circuit port speed and commit rate are measured in Kbps.
    """

    cid = models.CharField(max_length=CHARFIELD_MAX_LENGTH, verbose_name="Circuit ID")
    status = StatusField(blank=False, null=False)
    provider = models.ForeignKey(to="circuits.Provider", on_delete=models.PROTECT, related_name="circuits")
    circuit_type = models.ForeignKey(to="CircuitType", on_delete=models.PROTECT, related_name="circuits")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="circuits",
        blank=True,
        null=True,
    )
    install_date = models.DateField(blank=True, null=True, verbose_name="Date installed")
    commit_rate = models.PositiveIntegerField(blank=True, null=True, verbose_name="Commit rate (Kbps)")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    comments = models.TextField(blank=True)

    # Cache associated CircuitTerminations
    circuit_termination_a = models.ForeignKey(
        to="circuits.CircuitTermination",
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )
    circuit_termination_z = models.ForeignKey(
        to="circuits.CircuitTermination",
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )

    clone_fields = [
        "provider",
        "circuit_type",
        "status",
        "tenant",
        "install_date",
        "commit_rate",
        "description",
    ]

    class Meta:
        ordering = ["provider", "cid"]
        unique_together = ["provider", "cid"]

    def __str__(self):
        return self.cid


@extras_features(
    "cable_terminations",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "webhooks",
)
class CircuitTermination(PrimaryModel, PathEndpoint, CableTermination):
    circuit = models.ForeignKey(to="circuits.Circuit", on_delete=models.CASCADE, related_name="circuit_terminations")
    term_side = models.CharField(max_length=1, choices=CircuitTerminationSideChoices, verbose_name="Termination")
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="circuit_terminations",
        blank=True,
        null=True,
    )
    provider_network = models.ForeignKey(
        to="circuits.ProviderNetwork",
        on_delete=models.PROTECT,
        related_name="circuit_terminations",
        blank=True,
        null=True,
    )
    cloud_network = models.ForeignKey(
        to="cloud.CloudNetwork",
        on_delete=models.PROTECT,
        related_name="circuit_terminations",
        blank=True,
        null=True,
    )
    port_speed = models.PositiveIntegerField(verbose_name="Port speed (Kbps)", blank=True, null=True)
    upstream_speed = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Upstream speed (Kbps)",
        help_text="Upstream speed, if different from port speed",
    )
    xconnect_id = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, verbose_name="Cross-connect ID")
    pp_info = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, verbose_name="Patch panel/port(s)")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ["circuit", "term_side"]
        unique_together = ["circuit", "term_side"]

    def __str__(self):
        return f"Termination {self.term_side}: {self.location or self.provider_network or self.cloud_network}"

    def clean(self):
        super().clean()

        # Must define either location *or* provider network
        if self.location is None and self.provider_network is None and self.cloud_network is None:
            raise ValidationError(
                "A circuit termination must attach to a location, a provider network or a cloud network."
            )
        if self.location and self.provider_network:
            raise ValidationError("A circuit termination cannot attach to both a location and a provider network.")
        elif self.location and self.cloud_network:
            raise ValidationError("A circuit termination cannot attach to both a location and a cloud network.")
        elif self.provider_network and self.cloud_network:
            raise ValidationError("A circuit termination cannot attach to both a provider network and a cloud network.")
        # A valid location for contenttype CircuitTermination must be assigned.
        if self.location is not None:
            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {
                        "location": "Circuit terminations may not associate to locations of type "
                        f'"{self.location.location_type}"'
                    }
                )

    def to_objectchange(self, action, related_object=None, **kwargs):
        # Annotate the parent Circuit
        try:
            related_object = self.circuit
        except Circuit.DoesNotExist:
            # Parent circuit has been deleted
            related_object = None

        return super().to_objectchange(action, related_object=related_object, **kwargs)

    @property
    def parent(self):
        return self.circuit

    def get_peer_termination(self):
        peer_side = "Z" if self.term_side == "A" else "A"
        try:
            return CircuitTermination.objects.select_related("location").get(circuit=self.circuit, term_side=peer_side)
        except CircuitTermination.DoesNotExist:
            return None
