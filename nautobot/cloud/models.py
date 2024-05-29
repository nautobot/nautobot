from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudAccount(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The name of this Cloud Account.", unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    account_number = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, help_text="The account identifier of this Cloud Account."
    )
    provider = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="cloud_accounts",
        help_text="Manufacturers are the recommended model to represent cloud providers.",
    )
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    @property
    def display(self):
        return f"{self.provider}: {self.name} - {self.account_number}"
