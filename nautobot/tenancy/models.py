from django.db import models
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey

from nautobot.extras.models import ObjectChange
from nautobot.extras.utils import extras_features
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.utilities.mptt import TreeManager
from nautobot.utilities.utils import serialize_object


__all__ = (
    "Tenant",
    "TenantGroup",
)


@extras_features(
    "custom_fields",
    "custom_validators",
    "graphql",
    "relationships",
)
class TenantGroup(MPTTModel, OrganizationalModel):
    """
    An arbitrary collection of Tenants.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent = TreeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
        db_index=True,
    )
    description = models.CharField(max_length=200, blank=True)

    objects = TreeManager()

    csv_headers = ["name", "slug", "parent", "description"]

    class Meta:
        ordering = ["name"]

    class MPTTMeta:
        order_insertion_by = ["name"]

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

    def to_objectchange(self, action):
        # Remove MPTT-internal fields
        return ObjectChange(
            changed_object=self,
            object_repr=str(self),
            action=action,
            object_data=serialize_object(self, exclude=["level", "lft", "rght", "tree_id"]),
        )


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Tenant(PrimaryModel):
    """
    A Tenant represents an organization served by the Nautobot owner. This is typically a customer or an internal
    department.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    group = models.ForeignKey(
        to="tenancy.TenantGroup",
        on_delete=models.SET_NULL,
        related_name="tenants",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    csv_headers = ["name", "slug", "group", "description", "comments"]
    clone_fields = [
        "group",
        "description",
    ]

    class Meta:
        ordering = ["group", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tenancy:tenant", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.group.name if self.group else None,
            self.description,
            self.comments,
        )
