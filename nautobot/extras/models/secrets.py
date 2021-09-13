import logging

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

import pkg_resources

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.registry import registry
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
    description = models.CharField(max_length=200, blank=True)
    provider = models.CharField(max_length=100)
    parameters = models.JSONField(encoder=DjangoJSONEncoder, default=dict)

    csv_headers = [
        "name",
        "slug",
        "description",
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
            self.description,
            self.provider,
            self.parameters,
        )

    @property
    def value(self):
        """Retrieve the secret value that this Secret is a representation of."""
        provider = registry["secrets_providers"].get(self.provider)
        if not provider:
            logger.error('No registered provider "%s" is available', self.provider)
            return None

        value = provider.get_value_for_secret(self)
        if value:
            return value

        logger.error(
            'No secret value was retrieved for provider "%s" with parameters %s',
            self.provider,
            self.parameters,
        )
        return None

    def clean(self):
        provider = registry["secrets_providers"].get(self.provider)
        if not provider:
            raise ValidationError({"provider": f'No registered provider "{self.provider}" is available'})

        # Apply any provider-specific validation of the parameters
        form = provider.ParametersForm(self.parameters)
        form.is_valid()
        form.clean()
