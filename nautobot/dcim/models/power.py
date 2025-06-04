from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.validators import ExclusionValidator
from nautobot.dcim.choices import (
    BreakerPoleChoices,
    PanelTypeChoices,
    PanelVoltageChoices,
    PhaseAssignmentChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
)
from nautobot.dcim.constants import (
    POWERFEED_AMPERAGE_DEFAULT,
    POWERFEED_MAX_UTILIZATION_DEFAULT,
    POWERFEED_VOLTAGE_DEFAULT,
)
from nautobot.extras.models import StatusField
from nautobot.extras.utils import extras_features

from .device_components import CableTermination, PathEndpoint

__all__ = (
    "PowerFeed",
    "PowerPanel",
)


#
# Power
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "webhooks",
)
class PowerPanel(PrimaryModel):
    """
    A distribution point for electrical power; e.g. a data center RPP.
    """

    location = models.ForeignKey(to="dcim.Location", on_delete=models.PROTECT, related_name="power_panels")
    rack_group = models.ForeignKey(
        to="RackGroup", on_delete=models.PROTECT, blank=True, null=True, related_name="power_panels"
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    panel_type = models.CharField(
        max_length=30,
        choices=PanelTypeChoices,
        blank=True,
        help_text="Panel configuration type"
    )
    voltage_configuration = models.CharField(
        max_length=20,
        choices=PanelVoltageChoices,
        blank=True,
        help_text="Panel voltage configuration (e.g., 208/120V-3Φ-4W)"
    )
    main_amperage = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Panel main breaker amperage rating (e.g., 400)"
    )
    circuit_positions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total number of circuit positions in the panel (e.g., 42)"
    )

    natural_key_field_names = ["name", "location"]

    class Meta:
        ordering = ["location", "name"]
        unique_together = ["location", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:
            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {
                        "location": "Power panels may not associate to locations of type "
                        f'"{self.location.location_type}".'
                    }
                )

        # RackGroup must belong to assigned Location
        if self.rack_group:
            if (
                self.location is not None
                and self.rack_group.location is not None  # pylint: disable=no-member
                and self.rack_group.location not in self.location.ancestors(include_self=True)  # pylint: disable=no-member
            ):
                raise ValidationError(
                    {  # pylint: disable=no-member  # false positive on rack_group.location
                        "rack_group": f'Rack group "{self.rack_group}" belongs to a location '
                        f'("{self.rack_group.location}") that does not contain "{self.location}".'
                    }
                )


@extras_features(
    "cable_terminations",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class PowerFeed(PrimaryModel, PathEndpoint, CableTermination):
    """
    An electrical circuit delivered from a PowerPanel.
    """

    power_panel = models.ForeignKey(
        to="PowerPanel",
        on_delete=models.PROTECT,
        related_name="power_feeds",
        help_text="Source panel that originates this power feed"
    )
    destination_panel = models.ForeignKey(
        to="PowerPanel",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="feeders",
        help_text="Destination panel for panel-to-panel power distribution"
    )
    rack = models.ForeignKey(to="Rack", on_delete=models.PROTECT, blank=True, null=True, related_name="power_feeds")
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    status = StatusField(blank=False, null=False)
    type = models.CharField(
        max_length=50,
        choices=PowerFeedTypeChoices,
        default=PowerFeedTypeChoices.TYPE_PRIMARY,
    )
    supply = models.CharField(
        max_length=50,
        choices=PowerFeedSupplyChoices,
        default=PowerFeedSupplyChoices.SUPPLY_AC,
    )
    phase = models.CharField(
        max_length=50,
        choices=PowerFeedPhaseChoices,
        default=PowerFeedPhaseChoices.PHASE_SINGLE,
    )
    voltage = models.SmallIntegerField(default=POWERFEED_VOLTAGE_DEFAULT, validators=[ExclusionValidator([0])])
    amperage = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)], default=POWERFEED_AMPERAGE_DEFAULT)
    max_utilization = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        default=POWERFEED_MAX_UTILIZATION_DEFAULT,
        help_text="Maximum permissible draw (percentage)",
    )
    circuit_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Circuit position in panel (1, 2, 3, etc.)"
    )
    breaker_poles = models.CharField(
        max_length=3,
        choices=BreakerPoleChoices,
        blank=True,
        help_text="Breaker poles (1P, 2P, 3P)"
    )
    phase_assignment = models.CharField(
        max_length=5,
        choices=PhaseAssignmentChoices,
        blank=True,
        help_text="Phase assignment (A, B, C, A-B, etc.)"
    )
    available_power = models.PositiveIntegerField(default=0, editable=False)
    comments = models.TextField(blank=True)

    clone_fields = [
        "power_panel",
        "destination_panel",
        "rack",
        "status",
        "type",
        "supply",
        "phase",
        "voltage",
        "amperage",
        "max_utilization",
        "circuit_position",
        "breaker_poles",
        "phase_assignment",
        "available_power",
    ]

    class Meta:
        ordering = ["power_panel", "name"]
        unique_together = ["power_panel", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # AC voltage cannot be negative
        if self.voltage < 0 and self.supply == PowerFeedSupplyChoices.SUPPLY_AC:
            raise ValidationError({"voltage": "Voltage cannot be negative for AC supply"})

        # Destination panel validation
        if self.destination_panel:
            # Cannot feed into the same panel
            if self.destination_panel == self.power_panel:
                raise ValidationError({"destination_panel": "A power feed cannot connect a panel to itself"})

    def save(self, *args, **kwargs):
        # Cache the available_power property on the instance
        kva = abs(self.voltage) * self.amperage * (self.max_utilization / 100)
        if self.phase == PowerFeedPhaseChoices.PHASE_3PHASE:
            self.available_power = round(kva * 1.732)
        else:
            self.available_power = round(kva)

        super().save(*args, **kwargs)

    @property
    def parent(self):
        return self.power_panel

    def get_type_class(self):
        return PowerFeedTypeChoices.CSS_CLASSES.get(self.type)
