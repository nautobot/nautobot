from django.db import models

from nautobot.apps.models import extras_features, OrganizationalModel


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "webhooks",
)
class ExampleModel(OrganizationalModel):
    name = models.CharField(max_length=20, help_text="The name of this Example.", unique=True)
    number = models.IntegerField(default=100, help_text="The number of this Example.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.number}"


@extras_features(
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    # "graphql", Not specified here as we have a custom type for this model, see example_app.graphql.types
    "webhooks",
    "relationships",  # Defined here to ensure no clobbering: https://github.com/nautobot/nautobot/issues/3592
)
class AnotherExampleModel(OrganizationalModel):
    name = models.CharField(max_length=20, unique=True)
    number = models.IntegerField(default=100)

    # by default the natural key would just be "name" since it's a unique field. But we can override it:
    natural_key_field_names = ["name", "number"]

    class Meta:
        ordering = ["name"]
