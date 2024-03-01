from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.tree_queries import TreeModel
from nautobot.extras.utils import extras_features

__all__ = (
    "Tenant",
    "TenantGroup",
)


@extras_features(
    "custom_validators",
    "graphql",
)
class TenantGroup(TreeModel, OrganizationalModel):
    """
    An arbitrary collection of Tenants.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class Tenant(PrimaryModel):
    """
    A Tenant represents an organization served by the Nautobot owner. This is typically a customer or an internal
    department.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    tenant_group = models.ForeignKey(
        to="tenancy.TenantGroup",
        on_delete=models.SET_NULL,
        related_name="tenants",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    comments = models.TextField(blank=True)

    clone_fields = [
        "tenant_group",
        "description",
    ]

    class Meta:
        ordering = ["tenant_group", "name"]

    def __str__(self):
        return self.name
