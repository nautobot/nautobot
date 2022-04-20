from django.db import models
from django.urls import reverse

from nautobot.core.models.generics import OrganizationalModel
from nautobot.extras.utils import extras_features


@extras_features(
    "custom_links",
    "dynamic_groups",
    "graphql",
    "webhooks",
)
class ExampleModel(OrganizationalModel):
    name = models.CharField(max_length=20, help_text="The name of this Example.")
    number = models.IntegerField(default=100, help_text="The number of this Example.")

    csv_headers = ["name", "number"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.number}"

    def get_absolute_url(self):
        return reverse("plugins:example_plugin:examplemodel", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.name,
            self.number,
        )


@extras_features(
    "custom_fields",
    "dynamic_groups",
)
class AnotherExampleModel(OrganizationalModel):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]
