from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from nautobot.dcim.fields import ASNField
from nautobot.dcim.models import CableTermination, PathEndpoint
from nautobot.extras.models import StatusModel
from nautobot.extras.utils import extras_features
from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel

from .choices import CircuitTerminationSideChoices


__all__ = (
    "Circuit",
    "CircuitTermination",
    "CircuitType",
    "Provider",
    "ProviderNetwork",
)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class ProviderNetwork(PrimaryModel):
    name = models.CharField(max_length=100, db_index=True)
    slug = AutoSlugField(populate_from="name")
    provider = models.ForeignKey(to="circuits.Provider", on_delete=models.PROTECT, related_name="provider_networks")
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    csv_headers = [
        "provider",
        "name",
        "slug",
        "description",
        "comments",
    ]

    class Meta:
        ordering = ("provider", "name")
        constraints = (
            models.UniqueConstraint(fields=("provider", "name"), name="circuits_providernetwork_provider_name"),
        )
        unique_together = ("provider", "name")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("circuits:providernetwork", args=[self.slug])

    def to_csv(self):
        return (
            self.provider.name,
            self.name,
            self.slug,
            self.description,
            self.comments,
        )

    @property
    def display(self):
        return f"{self.provider} {self.name}"


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Provider(PrimaryModel):
    """
    Each Circuit belongs to a Provider. This is usually a telecommunications company or similar organization. This model
    stores information pertinent to the user's relationship with the Provider.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    asn = ASNField(
        blank=True,
        null=True,
        verbose_name="ASN",
        help_text="32-bit autonomous system number",
    )
    # todoindex:
    account = models.CharField(max_length=100, blank=True, verbose_name="Account number")
    portal_url = models.URLField(blank=True, verbose_name="Portal URL")
    noc_contact = models.TextField(blank=True, verbose_name="NOC contact")
    admin_contact = models.TextField(blank=True, verbose_name="Admin contact")
    comments = models.TextField(blank=True)

    csv_headers = [
        "name",
        "slug",
        "asn",
        "account",
        "portal_url",
        "noc_contact",
        "admin_contact",
        "comments",
    ]
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

    def get_absolute_url(self):
        return reverse("circuits:provider", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.asn,
            self.account,
            self.portal_url,
            self.noc_contact,
            self.admin_contact,
            self.comments,
        )


@extras_features("custom_fields", "custom_validators", "graphql", "relationships")
class CircuitType(OrganizationalModel):
    """
    Circuits can be organized by their functional role. For example, a user might wish to define CircuitTypes named
    "Long Haul," "Metro," or "Out-of-Band".
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    csv_headers = ["name", "slug", "description"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("circuits:circuittype", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.description,
        )


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class Circuit(PrimaryModel, StatusModel):
    """
    A communications circuit connects two points.
    Each Circuit belongs to a Provider; Providers may have multiple circuits.
    Each circuit is also assigned a CircuitType.
    Circuit port speed and commit rate are measured in Kbps.
    """

    cid = models.CharField(max_length=100, verbose_name="Circuit ID")
    provider = models.ForeignKey(to="circuits.Provider", on_delete=models.PROTECT, related_name="circuits")
    type = models.ForeignKey(to="CircuitType", on_delete=models.PROTECT, related_name="circuits")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="circuits",
        blank=True,
        null=True,
    )
    install_date = models.DateField(blank=True, null=True, verbose_name="Date installed")
    commit_rate = models.PositiveIntegerField(blank=True, null=True, verbose_name="Commit rate (Kbps)")
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    # Cache associated CircuitTerminations
    termination_a = models.ForeignKey(
        to="circuits.CircuitTermination",
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )
    termination_z = models.ForeignKey(
        to="circuits.CircuitTermination",
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )

    csv_headers = [
        "cid",
        "provider",
        "type",
        "status",
        "tenant",
        "install_date",
        "commit_rate",
        "description",
        "comments",
    ]
    clone_fields = [
        "provider",
        "type",
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

    def get_absolute_url(self):
        return reverse("circuits:circuit", args=[self.pk])

    def to_csv(self):
        return (
            self.cid,
            self.provider.name,
            self.type.name,
            self.get_status_display(),
            self.tenant.name if self.tenant else None,
            self.install_date,
            self.commit_rate,
            self.description,
            self.comments,
        )


@extras_features(
    "cable_terminations",
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "relationships",
    "webhooks",
)
class CircuitTermination(PrimaryModel, PathEndpoint, CableTermination):
    circuit = models.ForeignKey(to="circuits.Circuit", on_delete=models.CASCADE, related_name="terminations")
    term_side = models.CharField(max_length=1, choices=CircuitTerminationSideChoices, verbose_name="Termination")
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.PROTECT,
        related_name="circuit_terminations",
        blank=True,
        null=True,
    )
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
    port_speed = models.PositiveIntegerField(verbose_name="Port speed (Kbps)", blank=True, null=True)
    upstream_speed = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Upstream speed (Kbps)",
        help_text="Upstream speed, if different from port speed",
    )
    xconnect_id = models.CharField(max_length=50, blank=True, verbose_name="Cross-connect ID")
    pp_info = models.CharField(max_length=100, blank=True, verbose_name="Patch panel/port(s)")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["circuit", "term_side"]
        unique_together = ["circuit", "term_side"]

    def __str__(self):
        return f"Termination {self.term_side}: {self.site or self.provider_network}"

    def get_absolute_url(self):
        return reverse("circuits:circuittermination", args=[self.pk])

    def clean(self):
        super().clean()

        # Must define either site *or* provider network
        if self.site is None and self.provider_network is None:
            raise ValidationError("A circuit termination must attach to either a site or a provider network.")
        if self.site and self.provider_network:
            raise ValidationError("A circuit termination cannot attach to both a site and a provider network.")
        # If and only if a site is defined, a location *may* also be defined.
        if self.location is not None:
            if self.provider_network is not None:
                raise ValidationError("A circuit termination cannot attach to both a location and a provider network.")
            if self.site is not None and self.location.base_site != self.site:
                raise ValidationError(
                    {"location": f'Location "{self.location}" does not belong to site "{self.site}".'}
                )
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
            # v2 TODO(jathan): Replace prefetch_related with select_related
            return CircuitTermination.objects.prefetch_related("site").get(circuit=self.circuit, term_side=peer_side)
        except CircuitTermination.DoesNotExist:
            return None
