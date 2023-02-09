import factory

from nautobot.core.factory import (
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    UniqueFaker,
    random_instance,
)
from nautobot.tenancy.models import TenantGroup, Tenant


class TenantGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = TenantGroup
        exclude = (
            "has_description",
            "has_parent",
        )

    name = UniqueFaker("company")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_parent = NautobotBoolIterator()
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

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_tenant_group = NautobotBoolIterator()
    tenant_group = factory.Maybe("has_tenant_group", random_instance(TenantGroup), None)
