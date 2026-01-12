from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.validators import ExclusionValidator
from nautobot.dcim.choices import (
    PowerFeedBreakerPoleChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerPanelTypeChoices,
    PowerPathChoices,
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
    panel_type = models.CharField(max_length=30, choices=PowerPanelTypeChoices, blank=True)
    breaker_position_count = models.PositiveIntegerField(
        null=True, blank=True, help_text="Total number of breaker positions in the panel (e.g., 42)"
    )
    power_path = models.CharField(
        max_length=20,
        choices=PowerPathChoices,
        help_text="Physical power distribution redundancy path.",
        blank=True,
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
        help_text="Source panel that originates this power feed",
    )
    destination_panel = models.ForeignKey(
        to="PowerPanel",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="feeders",
        help_text="Destination panel that receives power from this feed",
    )
    rack = models.ForeignKey(to="Rack", on_delete=models.PROTECT, blank=True, null=True, related_name="power_feeds")
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    status = StatusField(blank=False, null=False)
    type = models.CharField(
        max_length=50,
        choices=PowerFeedTypeChoices,
        default=PowerFeedTypeChoices.TYPE_PRIMARY,
    )
    power_path = models.CharField(
        max_length=20,
        choices=PowerPathChoices,
        help_text="Physical power distribution redundancy path.",
        blank=True,
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
    breaker_position = models.PositiveIntegerField(
        null=True, blank=True, help_text="Starting circuit breaker position in panel"
    )
    breaker_pole_count = models.PositiveSmallIntegerField(
        choices=PowerFeedBreakerPoleChoices, blank=True, null=True, help_text="Number of breaker poles"
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
        "breaker_pole_count",
        "available_power",
    ]

    class Meta:
        ordering = ["power_panel", "breaker_position", "name"]
        unique_together = [
            ["power_panel", "name"],
            ["power_panel", "breaker_position"],
        ]
        indexes = [
            models.Index(fields=["power_panel", "breaker_position"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # Rack must belong to same location hierarchy as PowerPanel
        if self.rack and self.power_panel.location:  # pylint: disable=no-member
            if self.rack.location not in self.power_panel.location.ancestors(  # pylint: disable=no-member
                include_self=True
            ) and self.power_panel.location not in self.rack.location.ancestors(include_self=True):  # pylint: disable=no-member
                raise ValidationError(
                    {
                        "rack": f'Rack "{self.rack}" ({self.rack.location}) and '  # pylint: disable=no-member
                        f'power panel "{self.power_panel}" ({self.power_panel.location}) '  # pylint: disable=no-member
                        f"are not in the same location hierarchy."
                    }
                )

        # AC voltage cannot be negative
        if self.voltage < 0 and self.supply == PowerFeedSupplyChoices.SUPPLY_AC:
            raise ValidationError({"voltage": "Voltage cannot be negative for AC supply"})

        # Destination panel validation
        if self.destination_panel:
            # Cannot feed into the same panel
            if self.destination_panel == self.power_panel:
                raise ValidationError({"destination_panel": "A power feed cannot connect a panel to itself"})
            # TODO: add loop detection when graph structure is implemented for path tracing

        # Enforce mutual exclusivity between cable connections and destination_panel
        if self.destination_panel and self.cable:
            raise ValidationError(
                {
                    "destination_panel": "Cannot specify a destination panel when the power feed is connected via cable. "
                    "Power feeds can either connect to a panel OR be cabled to an endpoint, but not both."
                }
            )

        # Breaker position and pole validation
        if self.breaker_position is not None:
            # Default to single pole breaker when breaker_position is specified but breaker_pole_count is not
            if self.breaker_pole_count is None:
                self.breaker_pole_count = PowerFeedBreakerPoleChoices.POLE_1

            # Get occupied positions once for both validations
            occupied_positions = self.get_occupied_positions()

            # Ensure breaker positions fit within panel capacity
            if self.power_panel.breaker_position_count is not None:
                if occupied_positions:
                    max_occupied_position = max(occupied_positions)
                    if max_occupied_position > self.power_panel.breaker_position_count:
                        raise ValidationError(
                            {
                                "breaker_position": f"Breaker configuration starting at position {self.breaker_position} "
                                f"with {self.breaker_pole_count} poles would occupy positions {sorted(occupied_positions)}, "
                                f"but panel only has {self.power_panel.breaker_position_count} breaker positions"
                            }
                        )

            # Check for breaker position conflicts with other feeds
            conflicts = PowerFeed.objects.filter(
                power_panel=self.power_panel, breaker_position__isnull=False, breaker_pole_count__isnull=False
            ).exclude(pk=self.pk)

            for feed in conflicts:
                if occupied_positions.intersection(feed.get_occupied_positions()):
                    raise ValidationError(
                        {
                            "breaker_position": f"Breaker position {self.breaker_position} conflicts with "
                            f'feed "{feed.name}" (occupies {feed.occupied_positions})'
                        }
                    )

    def save(self, *args, **kwargs):
        # Enforce breaker pole count default
        if self.breaker_position is not None and self.breaker_pole_count is None:
            self.breaker_pole_count = PowerFeedBreakerPoleChoices.POLE_1

        # Enforce mutual exclusivity between cable connections and destination_panel
        if self.destination_panel and self.cable:
            raise ValidationError(
                "Cannot specify a destination panel when the power feed is connected via cable. "
                "Power feeds can either connect to a panel OR be cabled to an endpoint, but not both."
            )

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

    @property
    def occupied_positions(self) -> str:
        """All circuit positions occupied by this feed as comma-separated string."""
        positions = self.get_occupied_positions()
        return ", ".join(map(str, sorted(positions))) if positions else ""

    @property
    def phase_designation(self):
        """Calculate phase designation based on occupied circuit positions."""
        if not (self.breaker_position and self.breaker_pole_count):
            return None

        positions = self.get_occupied_positions()
        if not positions:
            return None

        # Positions 1,2=A, 3,4=B, 5,6=C, 7,8=A, 9,10=B, 11,12=C, etc.
        def position_to_phase(pos):
            # Calculate which phase this position is on
            cycle_position = ((pos - 1) // 2) % 3
            return ["A", "B", "C"][cycle_position]

        phases = {position_to_phase(pos) for pos in positions}

        # Return phase designation based on which phases are used
        if len(phases) == 1:
            return next(iter(phases))  # Single phase: "A", "B", or "C"
        elif len(phases) == 2:
            sorted_phases = sorted(phases)
            return f"{sorted_phases[0]}-{sorted_phases[1]}"  # "A-B", "B-C", etc.
        elif len(phases) == 3:
            return "A-B-C"  # Three-phase
        else:
            return None

    def get_occupied_positions(self) -> set[int]:
        """Get set of circuit breaker positions occupied by this feed."""
        if not (self.breaker_position and self.breaker_pole_count):
            return set()

        return set(self.breaker_position + (i * 2) for i in range(self.breaker_pole_count))

    def get_type_class(self):
        return PowerFeedTypeChoices.CSS_CLASSES.get(self.type)
