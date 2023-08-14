import logging

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from jinja2.exceptions import UndefinedError, TemplateSyntaxError

from nautobot.core.models import BaseModel
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.utils.data import render_jinja2
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.registry import registry
from nautobot.extras.secrets.exceptions import SecretError, SecretParametersError, SecretProviderError
from nautobot.extras.utils import extras_features


logger = logging.getLogger(__name__)


@extras_features(
    "custom_links",
    "custom_validators",
    "graphql",
    "webhooks",
)
class Secret(PrimaryModel):
    """
    Data model providing access to a "secret" such as a device credential or a systems-integration token.

    Note that this model **does not** STORE the actual secret data, rather it provides ACCESS to the secret for other
    Nautobot models and APIs to make use of as needed and appropriate.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)
    provider = models.CharField(max_length=100)
    parameters = models.JSONField(encoder=DjangoJSONEncoder, default=dict)

    clone_fields = [
        "provider",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def rendered_parameters(self, obj=None):
        """Render self.parameters as a Jinja2 template with the given object as context."""
        try:
            return {key: render_jinja2(value, {"obj": obj}) for key, value in self.parameters.items()}
        except (TemplateSyntaxError, UndefinedError) as exc:
            raise SecretParametersError(self, registry["secrets_providers"].get(self.provider), str(exc)) from exc

    def get_value(self, obj=None):
        """Retrieve the secret value that this Secret is a representation of.

        May raise a SecretError on failure.

        Args:
            obj (object): Object (Django model or similar) that may provide additional context for this secret.
        """
        provider = registry["secrets_providers"].get(self.provider)
        if not provider:
            raise SecretProviderError(self, self.provider, f'No registered provider "{self.provider}" is available')

        try:
            return provider.get_value_for_secret(self, obj=obj)
        except SecretError:
            raise
        except Exception as exc:
            raise SecretError(self, provider, str(exc)) from exc

    def clean(self):
        provider = registry["secrets_providers"].get(self.provider)
        if not provider:
            raise ValidationError({"provider": f'No registered provider "{self.provider}" is available'})

        # Apply any provider-specific validation of the parameters
        form = provider.ParametersForm(self.parameters)
        form.is_valid()
        form.clean()


@extras_features(
    "custom_links",
    "custom_validators",
    "graphql",
    "webhooks",
)
class SecretsGroup(OrganizationalModel):
    """A group of related Secrets."""

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)
    secrets = models.ManyToManyField(
        to=Secret, related_name="secrets_groups", through="extras.SecretsGroupAssociation", blank=True
    )

    documentation_static_path = "docs/user-guide/platform-functionality/secret.html"

    def __str__(self):
        return self.name

    def get_secret_value(self, access_type, secret_type, obj=None, **kwargs):
        """Helper method to retrieve a specific secret from this group.

        May raise SecretError and/or Django ObjectDoesNotExist exceptions; it's up to the caller to handle those.
        """
        secret = self.secrets.through.objects.get(
            secrets_group=self, access_type=access_type, secret_type=secret_type
        ).secret
        return secret.get_value(obj=obj, **kwargs)


@extras_features(
    "graphql",
)
class SecretsGroupAssociation(BaseModel):
    """The intermediary model for associating Secret(s) to SecretsGroup(s)."""

    secrets_group = models.ForeignKey(SecretsGroup, on_delete=models.CASCADE, related_name="secrets_group_associations")
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE, related_name="secrets_group_associations")

    access_type = models.CharField(max_length=32, choices=SecretsGroupAccessTypeChoices)
    secret_type = models.CharField(max_length=32, choices=SecretsGroupSecretTypeChoices)

    natural_key_field_names = ["secrets_group", "access_type", "secret_type", "secret"]

    documentation_static_path = "docs/user-guide/platform-functionality/secret.html"

    class Meta:
        unique_together = (
            # Don't allow the same access-type/secret-type combination to be used more than once in the same group
            ("secrets_group", "access_type", "secret_type"),
        )
        ordering = ("secrets_group", "access_type", "secret_type")

    def __str__(self):
        return f"{self.secrets_group}: {self.access_type} {self.secret_type}: {self.secret}"
