from django.db import models  # noqa: I001
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.validators import Draft7Validator

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel, ContentTypeRelatedQuerySet
from nautobot.core.models.fields import ForeignKeyLimitedByContentTypes
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import FeatureQuery, extras_features


@extras_features(
    "custom_links",
    "custom_validators",
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
        help_text="The Manufacturer instance which represents the Cloud Provider",
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
class CloudResourceType(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="Type of cloud objects", unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    provider = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="cloud_resource_types",
        help_text="The Manufacturer instance which represents the Cloud Provider",
    )
    config_schema = models.JSONField(null=True, blank=True)
    content_types = models.ManyToManyField(
        to=ContentType,
        help_text="The content type(s) to which this model applies.",
        related_name="cloud_resource_types",
        limit_choices_to=FeatureQuery("cloud_resource_types"),
    )
    clone_fields = [
        "provider",
        "content_types",
    ]

    objects = BaseManager.from_queryset(ContentTypeRelatedQuerySet)()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display(self):
        return f"{self.provider}: {self.name}"


class CloudResourceTypeMixin(models.Model):
    """Mixin that designates a model as compatible with CloudResourceType content_types selections."""

    cloud_resource_type = ForeignKeyLimitedByContentTypes(to=CloudResourceType, on_delete=models.PROTECT)
    extra_config = models.JSONField(null=True, blank=True)

    is_cloud_resource_type_model = True

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        # Copied from nautobot.extras.models.models.ConfigContextSchemaValidationMixin
        schema = self.cloud_resource_type.config_schema  # pylint: disable=no-member
        if schema:
            try:
                Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER).validate(self.extra_config)
            except JSONSchemaValidationError as e:
                raise ValidationError(
                    {
                        "extra_config": [
                            f"Validation according to CloudResourceType {self.cloud_resource_type} config_schema failed.",
                            e.message,
                        ]
                    }
                )


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudNetwork(CloudResourceTypeMixin, PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    cloud_account = models.ForeignKey(to=CloudAccount, on_delete=models.PROTECT, related_name="cloud_networks")
    parent = models.ForeignKey(
        to="cloud.CloudNetwork", on_delete=models.PROTECT, blank=True, null=True, related_name="children"
    )
    prefixes = models.ManyToManyField(
        blank=True,
        related_name="cloud_networks",
        to="ipam.Prefix",
        through="cloud.CloudNetworkPrefixAssignment",
    )
    clone_fields = [
        "cloud_resource_type",
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

        # TODO: should we enforce that self.cloud_resource_type.provider == self.cloud_account.provider?


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
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
class CloudService(CloudResourceTypeMixin, PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    cloud_account = models.ForeignKey(
        to=CloudAccount,
        related_name="cloud_services",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )
    cloud_networks = models.ManyToManyField(
        to=CloudNetwork,
        through="cloud.CloudServiceNetworkAssignment",
        related_name="cloud_services",
        through_fields=("cloud_service", "cloud_network"),
        blank=True,
    )
    clone_fields = [
        "cloud_account",
        "cloud_networks",
        "cloud_resource_type",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class CloudServiceNetworkAssignment(BaseModel):
    cloud_network = models.ForeignKey(CloudNetwork, on_delete=models.CASCADE, related_name="cloud_service_assignments")
    cloud_service = models.ForeignKey(CloudService, on_delete=models.CASCADE, related_name="cloud_network_assignments")
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["cloud_network", "cloud_service"]
        ordering = ["cloud_network", "cloud_service"]

    def __str__(self):
        return f"{self.cloud_network}: {self.cloud_service}"
