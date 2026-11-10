from django.db import models  # noqa: I001
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.validators import Draft7Validator

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel, ContentTypeRelatedQuerySet
from nautobot.core.models.fields import ForeignKeyLimitedByContentTypes
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.tree_queries import TreeModel
from nautobot.extras.models import RoleField, StatusField
from nautobot.extras.utils import FeatureQuery, extras_features

# Long enough for an Azure resource ID of a nested resource (subscription, resource group, parent and child names),
# while staying within the MySQL index size limit for a unique utf8mb4 column.
PROVIDER_RESOURCE_ID_MAX_LENGTH = 512


def validate_name_unique_in_scope(instance, scope_fields, message):
    """Reject a duplicate name within a scope where some scope fields are empty.

    The database enforces `unique_together` on the scope, but SQL treats NULL values as distinct, so two objects with
    the same name and the same empty scope field would otherwise both be accepted.
    """
    scope = {field: getattr(instance, f"{field}_id") for field in scope_fields}
    if all(value is not None for value in scope.values()):
        return
    lookups = {"name": instance.name}
    for field, value in scope.items():
        if value is None:
            lookups[f"{field}__isnull"] = True
        else:
            lookups[f"{field}_id"] = value
    if type(instance).objects.exclude(pk=instance.pk).filter(**lookups).exists():
        raise ValidationError({"name": message})


def validate_location_content_type(instance):
    """Reject a location whose location type does not permit this model's content type."""
    if instance.location is not None:
        if ContentType.objects.get_for_model(instance) not in instance.location.location_type.content_types.all():
            raise ValidationError(
                {
                    "location": f"{instance._meta.verbose_name_plural.capitalize()} may not associate to locations "
                    f'of type "{instance.location.location_type}".'
                }
            )


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class CloudAccount(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The name of this Cloud Account.")
    status = StatusField(blank=False, null=False)
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
    cloud_account_group = models.ForeignKey(
        to="cloud.CloudAccountGroup",
        on_delete=models.SET_NULL,
        related_name="cloud_accounts",
        blank=True,
        null=True,
        help_text="The organisation container (management group, organizational unit or folder) of this account.",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="cloud_accounts",
        blank=True,
        null=True,
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
        "cloud_account_group",
        "status",
        "tenant",
        "secrets_group",
    ]

    class Meta:
        ordering = ["name"]
        unique_together = [["provider", "name"]]

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


class ProviderResourceIdMixin(models.Model):
    """Mixin that adds the identifier assigned to a resource by its cloud provider."""

    provider_resource_id = models.CharField(  # django-char-field-with-null -- unique when set
        max_length=PROVIDER_RESOURCE_ID_MAX_LENGTH,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Provider resource ID",
        help_text="The identifier assigned by the cloud provider, such as an Azure resource ID, an AWS ARN "
        "or a GCP resource name.",
    )

    class Meta:
        abstract = True


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CloudAccountGroup(TreeModel, CloudResourceTypeMixin, PrimaryModel):
    """An organisation container above cloud accounts, such as an Azure management group, an AWS organizational unit
    or a GCP folder."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    clone_fields = [
        "cloud_resource_type",
        "parent",
    ]
    natural_key_field_names = ["parent__name", "name"]

    class Meta:
        ordering = ["name"]
        unique_together = [["parent", "name"]]

    def __str__(self):
        return self.name

    def validate_unique(self, exclude=None):
        validate_name_unique_in_scope(
            self, ["parent"], "A top-level cloud account group with this name already exists."
        )
        super().validate_unique(exclude=exclude)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "webhooks",
)
class CloudResourceGroup(ProviderResourceIdMixin, CloudResourceTypeMixin, PrimaryModel):
    """A container of cloud resources inside a cloud account, such as an Azure resource group."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    cloud_account = models.ForeignKey(
        to=CloudAccount,
        on_delete=models.PROTECT,
        related_name="cloud_resource_groups",
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="cloud_resource_groups",
        blank=True,
        null=True,
    )
    clone_fields = [
        "cloud_resource_type",
        "cloud_account",
        "location",
    ]

    class Meta:
        ordering = ["name"]
        unique_together = [["cloud_account", "name"]]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        validate_location_content_type(self)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class CloudNetwork(ProviderResourceIdMixin, CloudResourceTypeMixin, PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    status = StatusField(blank=False, null=False)
    role = RoleField(blank=True, null=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    cloud_account = models.ForeignKey(to=CloudAccount, on_delete=models.PROTECT, related_name="cloud_networks")
    cloud_resource_group = models.ForeignKey(
        to=CloudResourceGroup,
        on_delete=models.PROTECT,
        related_name="cloud_networks",
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        to="cloud.CloudNetwork", on_delete=models.PROTECT, blank=True, null=True, related_name="children"
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="cloud_networks",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="cloud_networks",
        blank=True,
        null=True,
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
        "cloud_resource_group",
        "parent",
        "location",
        "status",
        "role",
        "tenant",
    ]
    natural_key_field_names = ["cloud_account", "cloud_resource_group__name", "parent__name", "name"]

    class Meta:
        ordering = ["name"]
        unique_together = [["cloud_account", "cloud_resource_group", "parent", "name"]]

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

        if (
            self.cloud_resource_group is not None
            and self.cloud_resource_group.cloud_account_id != self.cloud_account_id
        ):
            raise ValidationError(
                {"cloud_resource_group": "The cloud resource group must belong to the same cloud account."}
            )

        if (
            self.cloud_resource_type_id is not None
            and self.cloud_account_id is not None
            and self.cloud_resource_type.provider_id != self.cloud_account.provider_id
        ):
            raise ValidationError(
                {"cloud_resource_type": "The cloud resource type must have the same provider as the cloud account."}
            )

        if self.parent is not None and self.parent.cloud_account_id != self.cloud_account_id:
            raise ValidationError({"parent": "The parent cloud network must belong to the same cloud account."})

        validate_location_content_type(self)

    def validate_unique(self, exclude=None):
        validate_name_unique_in_scope(
            self,
            ["cloud_account", "cloud_resource_group", "parent"],
            "A cloud network with this name already exists in this cloud account, resource group and parent.",
        )
        super().validate_unique(exclude=exclude)


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
    "locations",
    "statuses",
    "webhooks",
)
class CloudService(ProviderResourceIdMixin, CloudResourceTypeMixin, PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    status = StatusField(blank=False, null=False)
    role = RoleField(blank=True, null=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    cloud_account = models.ForeignKey(
        to=CloudAccount,
        related_name="cloud_services",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )
    cloud_resource_group = models.ForeignKey(
        to=CloudResourceGroup,
        on_delete=models.PROTECT,
        related_name="cloud_services",
        blank=True,
        null=True,
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="cloud_services",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="cloud_services",
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
    ip_addresses = models.ManyToManyField(
        to="ipam.IPAddress",
        through="cloud.CloudServiceIPAddressAssignment",
        related_name="cloud_services",
        through_fields=("cloud_service", "ip_address"),
        blank=True,
        verbose_name="IP addresses",
    )
    clone_fields = [
        "cloud_account",
        "cloud_resource_group",
        "cloud_networks",
        "cloud_resource_type",
        "location",
        "status",
        "role",
        "tenant",
    ]
    natural_key_field_names = ["cloud_account", "cloud_resource_group__name", "name"]

    class Meta:
        ordering = ["name"]
        unique_together = [["cloud_account", "cloud_resource_group", "name"]]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if (
            self.cloud_resource_group is not None
            and self.cloud_resource_group.cloud_account_id != self.cloud_account_id
        ):
            raise ValidationError(
                {"cloud_resource_group": "The cloud resource group must belong to the same cloud account."}
            )

        validate_location_content_type(self)

    def validate_unique(self, exclude=None):
        validate_name_unique_in_scope(
            self,
            ["cloud_account", "cloud_resource_group"],
            "A cloud service with this name already exists in this cloud account and resource group.",
        )
        super().validate_unique(exclude=exclude)


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


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class CloudServiceIPAddressAssignment(BaseModel):
    cloud_service = models.ForeignKey(CloudService, on_delete=models.CASCADE, related_name="ip_address_assignments")
    ip_address = models.ForeignKey("ipam.IPAddress", on_delete=models.CASCADE, related_name="cloud_service_assignments")
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["cloud_service", "ip_address"]
        ordering = ["cloud_service", "ip_address"]
        verbose_name = "cloud service IP address assignment"

    def __str__(self):
        return f"{self.cloud_service}: {self.ip_address}"
