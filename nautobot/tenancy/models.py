from django.db import models
from django.urls import reverse

from nautobot.core.models.fields import AutoSlugField
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

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "parent", "description"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tenancy:tenantgroup", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.parent.name if self.parent else "",
            self.description,
        )


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

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    tenant_group = models.ForeignKey(
        to="tenancy.TenantGroup",
        on_delete=models.SET_NULL,
        related_name="tenants",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    csv_headers = ["name", "slug", "tenant_group", "description", "comments"]
    clone_fields = [
        "tenant_group",
        "description",
    ]

    class Meta:
        ordering = ["tenant_group", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tenancy:tenant", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.tenant_group.name if self.tenant_group else None,
            self.description,
            self.comments,
        )
