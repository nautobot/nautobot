from django.db import models

from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import extras_features, OrganizationalModel


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ExampleModel(OrganizationalModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The name of this Example.", unique=True)
    number = models.IntegerField(default=100, help_text="The number of this Example.")

    job_log_entry = models.ForeignKey(
        to="extras.JobLogEntry", on_delete=models.CASCADE, related_name="example_models", null=True, blank=True
    )
    linked_example_models = models.ManyToManyField(
        to="self", symmetrical=False, related_name="linking_example_models", blank=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.number}"


@extras_features(
    "custom_validators",
    "export_templates",
    # "graphql", Not specified here as we have a custom type for this model, see example_app.graphql.types
    "webhooks",
    "relationships",  # Defined here to ensure no clobbering: https://github.com/nautobot/nautobot/issues/3592
)
class AnotherExampleModel(OrganizationalModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    number = models.IntegerField(default=100)

    job_log_entry = models.ForeignKey(
        to="extras.JobLogEntry", on_delete=models.RESTRICT, related_name="more_example_models", null=True, blank=True
    )
    example_model = models.ForeignKey(
        to=ExampleModel, on_delete=models.PROTECT, related_name="more_example_models", null=True, blank=True
    )

    # by default the natural key would just be "name" since it's a unique field. But we can override it:
    natural_key_field_names = ["name", "number"]

    class Meta:
        ordering = ["name"]
