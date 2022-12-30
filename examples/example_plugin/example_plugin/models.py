from django.db import models
from django.urls import reverse

from example_plugin.choices import FeatureChoices
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

    def get_absolute_url(self):
        return reverse("plugins:example_plugin:examplemodel", kwargs={"pk": self.pk})

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

    def get_absolute_url(self):
        return reverse("plugins:example_plugin:anotherexamplemodel", kwargs={"pk": self.pk})


@extras_features(
    "custom_fields",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class EasyModel(OrganizationalModel):
    name = models.CharField(max_length=20)
    description = models.TextField()

    class Meta:
        ordering = ["name"]


@extras_features(
    "custom_fields",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class CustomModel(OrganizationalModel):
    name = models.CharField(max_length=20)
    description = models.TextField()

    class Meta:
        ordering = ["name"]


@extras_features(
    "custom_fields",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class DynamicModel(OrganizationalModel):
    has_feature = models.CharField(max_length=20, choices=FeatureChoices)
    description = models.TextField()
