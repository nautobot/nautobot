import factory

from nautobot.circuits.models import CircuitType, Circuit, Provider
from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory, UniqueFaker, random_instance
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant


class CircuitTypeFactory(OrganizationalModelFactory):
    class Meta:
        model = CircuitType
        exclude = ("has_description",)

    name = UniqueFaker("color")
    # Slug isn't defined here since it inherits from name.

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ProviderFactory(PrimaryModelFactory):
    class Meta:
        model = Provider
        exclude = ("has_asn", "has_account", "has_portal_url", "has_noc_contact", "has_admin_contact", "has_comments")

    name = UniqueFaker("company")
    # Slug isn't defined here since it inherits from name.

    has_asn = factory.Faker("pybool")
    asn = factory.Maybe("has_asn", factory.Faker("pyint", min_value=4200000000, max_value=4294967294), None)

    has_account = factory.Faker("pybool")
    account = factory.Maybe("has_account", factory.Faker("uuid4"), "")

    has_portal_url = factory.Faker("pybool")
    portal_url = factory.Maybe("has_portal_url", factory.Faker("url"), "")

    has_noc_contact = factory.Faker("pybool")
    noc_contact = factory.Maybe("has_noc_contact", factory.Faker("address"), "")

    has_admin_contact = factory.Faker("pybool")
    admin_contact = factory.Maybe("has_admin_contact", factory.Faker("address"), "")

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class CircuitFactory(PrimaryModelFactory):
    class Meta:
        model = Circuit
        exclude = ("has_tenant", "has_install_date", "has_commit_rate", "has_description", "has_comments")

    provider = random_instance(Provider, allow_null=False)
    type = random_instance(CircuitType, allow_null=False)
    cid = factory.LazyAttributeSequence(lambda o, n: f"{o.provider} {o.type} - {n:04}")
    status = random_instance(lambda: Status.objects.get_for_model(Circuit), allow_null=False)

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_install_date = factory.Faker("pybool")
    install_date = factory.Maybe("has_install_date", factory.Faker("date"), None)

    has_commit_rate = factory.Faker("pybool")
    commit_rate = factory.Maybe("has_commit_rate", factory.Faker("pyint"), None)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    # TODO: populate termination_a and termination_z


# TODO: CircuitTermination, ProviderNetwork
