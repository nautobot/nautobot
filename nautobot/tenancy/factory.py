import factory

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory, UniqueFaker, random_instance
from nautobot.tenancy.models import TenantGroup, Tenant


class TenantGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = TenantGroup
        exclude = (
            "has_description",
            "has_parent",
        )

    name = UniqueFaker("company")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_parent = factory.Faker("pybool")
    parent = factory.Maybe("has_parent", random_instance(TenantGroup), None)


class TenantFactory(PrimaryModelFactory):
    class Meta:
        model = Tenant
        exclude = (
            "has_comments",
            "has_description",
            "has_tenant_group",
        )

    name = UniqueFaker("company")

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_tenant_group = factory.Faker("pybool")
    tenant_group = factory.Maybe("has_tenant_group", random_instance(TenantGroup), None)
