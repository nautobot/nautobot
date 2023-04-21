from django.db import models

from nautobot.apps.models import extras_features, OrganizationalModel


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
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

    def to_csv(self):
        return (
            self.name,
            self.number,
        )


@extras_features(
    "custom_fields",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    # "graphql", Not specified here as we have a custom type for this model, see example_plugin.graphql.types
    "relationships",
    "webhooks",
)
class AnotherExampleModel(OrganizationalModel):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]
