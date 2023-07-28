from django.db import models
from django.urls import reverse
from django.db.models import Q

from nautobot.apps.models import extras_features, OrganizationalModel, PrimaryModel
from nautobot.utilities.choices import ChoiceSet


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


class ValueTypeChoices(ChoiceSet):

    TYPE_ENV = "env"
    TYPE_ASSET_TAG = "asset_tag"
    TYPE_NETWORK = "network"

    CHOICES = (
        (TYPE_ENV, "Environment"),
        (TYPE_ASSET_TAG, "Asset Tag"),
        (TYPE_NETWORK, "Network"),
    )


@extras_features(
    "custom_fields",
    "relationships",
)
class ValueModel(PrimaryModel):
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    value_type = models.CharField(
        max_length=250,
        choices=ValueTypeChoices,
    )

    csv_headers = ["name", "value", "value_type"]

    def get_absolute_url(self):
        return reverse("plugins:example_plugin:valuemodel", kwargs={"pk": self.pk})


@extras_features(
    "custom_fields",
    "relationships",
)
class ClassificationGroupsModel(PrimaryModel):
    name = models.CharField(max_length=200)
    environment = models.ForeignKey(
        to="example_plugin.ValueModel",
        on_delete=models.CASCADE,
        related_name="environment_bundles",
        limit_choices_to=Q(value_type=ValueTypeChoices.TYPE_ENV),
    )
    asset_tag = models.ForeignKey(
        to="example_plugin.ValueModel",
        on_delete=models.CASCADE,
        related_name="asset_tag_bundles",
        limit_choices_to=Q(value_type=ValueTypeChoices.TYPE_ASSET_TAG),
    )
    network = models.ForeignKey(
        to="example_plugin.ValueModel",
        on_delete=models.CASCADE,
        related_name="network_bundles",
        limit_choices_to=Q(value_type=ValueTypeChoices.TYPE_NETWORK),
    )

    csv_headers = ["name", "environment", "asset_tag", "network"]

    def get_absolute_url(self):
        return reverse("plugins:example_plugin:classificationgroupsmodel", kwargs={"pk": self.pk})
