import factory

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.factory import (
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.tenancy.models import Tenant, TenantGroup


class TenantGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = TenantGroup
        exclude = (
            "has_description",
            "has_parent",
        )

    name = UniqueFaker("company")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

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
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    has_tenant_group = NautobotBoolIterator(chance_of_getting_true=90)
    tenant_group = factory.Maybe("has_tenant_group", random_instance(TenantGroup), None)
