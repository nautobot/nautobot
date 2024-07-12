from django.db import models  # noqa: I001
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.validators import Draft7Validator

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import FeatureQuery, extras_features


class CloudTypeMixin:
    """Mixin that designates a model as compatible with CloudType content_types selections."""

    is_cloud_type_model = True


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudAccount(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The name of this Cloud Account.", unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    account_number = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, help_text="The account identifier of this Cloud Account."
    )
    provider = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="cloud_accounts",
        help_text="Manufacturers are the recommended model to represent cloud providers.",
    )
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )
    clone_fields = [
        "provider",
        "secrets_group",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    @property
    def display(self):
        return f"{self.provider}: {self.name} - {self.account_number}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudType(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="Type of cloud objects", unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    provider = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="cloud_types",
    )
    config_schema = models.JSONField(null=True, blank=True)
    content_types = models.ManyToManyField(
        to=ContentType,
        help_text="The content type(s) to which this model applies.",
        related_name="cloud_types",
        limit_choices_to=FeatureQuery("cloud_types"),
    )
    clone_fields = [
        "provider",
        "content_types",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display(self):
        return f"{self.provider}: {self.name}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudNetwork(CloudTypeMixin, PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    cloud_type = models.ForeignKey(to=CloudType, on_delete=models.PROTECT, related_name="cloud_networks")
    cloud_account = models.ForeignKey(to=CloudAccount, on_delete=models.PROTECT, related_name="cloud_networks")
    parent = models.ForeignKey(
        to="cloud.CloudNetwork", on_delete=models.SET_NULL, blank=True, null=True, related_name="children"
    )
    prefixes = models.ManyToManyField(
        blank=True,
        related_name="cloud_networks",
        to="ipam.Prefix",
        through="cloud.CloudNetworkPrefixAssignment",
    )
    extra_config = models.JSONField(null=True, blank=True)
    clone_fields = [
        "cloud_type",
        "cloud_account",
        "parent",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.parent is not None:
            if self.parent.parent is not None:
                raise ValidationError(
                    {"parent": "A CloudNetwork may not be the child of a CloudNetwork that itself has a parent."}
                )
            if self.parent == self:
                raise ValidationError({"parent": "A CloudNetwork may not be its own parent."})

        # TODO: should we enforce that self.cloud_type.provider == self.cloud_account.provider?

        # Copied from nautobot.extras.models.models.ConfigContextSchemaValidationMixin
        schema = self.cloud_type.config_schema
        if schema:
            try:
                Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER).validate(self.extra_config)
            except JSONSchemaValidationError as e:
                raise ValidationError(
                    {
                        "extra_config": [
                            f"Validation according to CloudType {self.cloud_type} config_schema failed.",
                            e.message,
                        ]
                    }
                )


@extras_features("graphql")
class CloudNetworkPrefixAssignment(BaseModel):
    cloud_network = models.ForeignKey(CloudNetwork, on_delete=models.CASCADE, related_name="prefix_assignments")
    prefix = models.ForeignKey("ipam.Prefix", on_delete=models.CASCADE, related_name="cloud_network_assignments")
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["cloud_network", "prefix"]
        ordering = ["cloud_network", "prefix"]

    def __str__(self):
        return f"{self.cloud_network}: {self.prefix}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudService(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    cloud_account = models.ForeignKey(
        to=CloudAccount,
        related_name="cloud_services",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )
    cloud_network = models.ForeignKey(to=CloudNetwork, on_delete=models.PROTECT, related_name="cloud_services")
    cloud_type = models.ForeignKey(to=CloudType, on_delete=models.PROTECT, related_name="cloud_services")
    extra_config = models.JSONField(null=True, blank=True)
    clone_fields = [
        "cloud_account",
        "cloud_network",
        "cloud_type",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
