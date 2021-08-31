import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

import pkg_resources

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features


logger = logging.getLogger(__name__)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "graphql",
    "relationships",
    "webhooks",
)
class Secret(PrimaryModel):
    """
    Data model providing access to a "secret" such as a device credential or a systems-integration token.

    Note that this model **does not** STORE the actual secret data, rather it provides ACCESS to the secret for other
    Nautobot models and APIs to make use of as needed and appropriate.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    provider = models.CharField(max_length=100)
    parameters = models.JSONField(encoder=DjangoJSONEncoder)

    csv_headers = [
        "name",
        "slug",
        "provider",
        "parameters",
    ]
    clone_fields = [
        "provider",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("extras:secret", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.provider,
            self.parameters,
        )

    @property
    def value(self):
        """Retrieve the secret value that this Secret is a representation of."""
        provider = None
        value = None
        # Should only be one matching entry point but in theory multiple plugins could register the same name...
        for entry_point in pkg_resources.iter_entry_points("nautobot.secrets.providers", name=self.provider):
            provider = entry_point.load()
            value = provider.get_value_for_secret(self)
            if value:
                return value
            # else, continue to the next entry point with this same provider, if any, just in case...

        if not provider:
            logger.error('No registered provider "%s" is available', self.provider)
        else:
            logger.error(
                'No secret value retrievable for provider "%s" with parameters %s', self.provider, self.parameters
            )
        return None
