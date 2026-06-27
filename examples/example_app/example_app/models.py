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

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.number}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "relationships",
    "webhooks",
)
class ProxyExampleModel(ExampleModel):
    """Proxy of `ExampleModel` used to exercise proxy-model ContentType behavior.

    Setting `for_concrete_model = False` makes this proxy resolve to its own ContentType, so
    relationships (and, as future fixes land, other ContentType-keyed features) assigned to the
    proxy are distinct from those assigned to the concrete `ExampleModel`. A real app would
    typically also implement a manager that partitions the proxy's rows from the concrete model's
    rows; this example keeps the full row set visible for simplicity.
    """

    for_concrete_model = False

    class Meta:
        proxy = True
        verbose_name = "Proxy Example"
        verbose_name_plural = "Proxy Examples"


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

    # by default the natural key would just be "name" since it's a unique field. But we can override it:
    natural_key_field_names = ["name", "number"]

    class Meta:
        ordering = ["name"]
