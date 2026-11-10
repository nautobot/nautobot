from nautobot.core.choices import ChoiceSet


class CloudStatusChoices(ChoiceSet):
    STATUS_PLANNED = "planned"
    STATUS_ACTIVE = "active"
    STATUS_DECOMMISSIONING = "decommissioning"

    CHOICES = (
        (STATUS_PLANNED, "Planned"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DECOMMISSIONING, "Decommissioning"),
    )
