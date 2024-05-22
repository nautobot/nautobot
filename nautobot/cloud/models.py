from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.generics import OrganizationalModel


class CloudAccount(OrganizationalModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The name of this Cloud Account.")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    account_number = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The number of this Cloud Account.")
    provider = models.ForeignKey(to="dcim.Manufacturer", on_delete=models.PROTECT, related_name="cloud_accounts")
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["provider", "name", "account_number"]
        unique_together = ["provider", "name", "account_number"]

    def __str__(self):
        return f"{self.provider}: {self.name} - {self.account_number}"

    @property
    def display(self):
        return f"{self.provider}: {self.name} - {self.account_number}"
