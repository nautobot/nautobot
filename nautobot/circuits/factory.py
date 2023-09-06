import factory
import faker

from nautobot.circuits import choices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.core.factory import (
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    UniqueFaker,
    random_instance,
)
from nautobot.dcim import models as dcim_models
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant


class CircuitTypeFactory(OrganizationalModelFactory):
    class Meta:
        model = CircuitType
        exclude = ("has_description",)

    name = UniqueFaker("color")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ProviderFactory(PrimaryModelFactory):
    class Meta:
        model = Provider
        exclude = ("has_asn", "has_account", "has_portal_url", "has_noc_contact", "has_admin_contact", "has_comments")

    name = UniqueFaker("company")

    has_asn = NautobotBoolIterator()
    asn = factory.Maybe("has_asn", factory.Faker("pyint", min_value=4200000000, max_value=4294967294), None)

    has_account = NautobotBoolIterator()
    account = factory.Maybe("has_account", factory.Faker("uuid4"), "")

    has_portal_url = NautobotBoolIterator()
    portal_url = factory.Maybe("has_portal_url", factory.Faker("url"), "")

    has_noc_contact = NautobotBoolIterator()
    noc_contact = factory.Maybe("has_noc_contact", factory.Faker("address"), "")

    has_admin_contact = NautobotBoolIterator()
    admin_contact = factory.Maybe("has_admin_contact", factory.Faker("address"), "")

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class CircuitFactory(PrimaryModelFactory):
    class Meta:
        model = Circuit
        exclude = ("has_tenant", "has_install_date", "has_commit_rate", "has_description", "has_comments")

    provider = random_instance(Provider, allow_null=False)
    circuit_type = random_instance(CircuitType, allow_null=False)
    cid = factory.LazyAttributeSequence(lambda o, n: f"{o.provider} {o.circuit_type} - {n:04}")
    status = random_instance(lambda: Status.objects.get_for_model(Circuit), allow_null=False)

    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_install_date = NautobotBoolIterator()
    install_date = factory.Maybe("has_install_date", factory.Faker("date"), None)

    has_commit_rate = NautobotBoolIterator()
    commit_rate = factory.Maybe("has_commit_rate", factory.Faker("pyint"), None)

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class ProviderNetworkFactory(PrimaryModelFactory):
    class Meta:
        model = ProviderNetwork
        exclude = ("has_description", "has_comments")

    name = factory.LazyAttribute(
        lambda o: f"{o.provider.name} Network {faker.Faker().word(part_of_speech='noun')}"[:100]
    )
    provider = random_instance(Provider, allow_null=False)

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class CircuitTerminationFactory(PrimaryModelFactory):
    class Meta:
        model = CircuitTermination
        exclude = (
            "has_location",
            "has_port_speed",
            "has_upstream_speed",
            "has_xconnect_id",
            "has_pp_info",
            "has_description",
        )

    circuit = factory.LazyAttribute(
        lambda o: faker.Faker().random_element(
            elements=Circuit.objects.filter(**{f"circuit_termination_{o.term_side.lower()}__isnull": True})
        )
    )

    term_side = factory.Faker("random_element", elements=choices.CircuitTerminationSideChoices.values())

    has_location = factory.Faker("pybool")
    location = factory.Maybe(
        "has_location",
        factory.LazyAttribute(lambda o: dcim_models.Location.objects.get_for_model(CircuitTermination).first()),
        None,
    )

    @factory.lazy_attribute
    def provider_network(self):
        # location and provider_network are mutually exclusive but cannot both be null
        if self.has_location:
            return None
        if ProviderNetwork.objects.filter(provider=self.circuit.provider).exists():
            return faker.Faker().random_element(elements=ProviderNetwork.objects.filter(provider=self.circuit.provider))
        return ProviderNetworkFactory(provider=self.circuit.provider)

    has_port_speed = NautobotBoolIterator()
    port_speed = factory.Maybe("has_port_speed", factory.Faker("pyint", max_value=100000000), None)

    has_upstream_speed = NautobotBoolIterator()
    upstream_speed = factory.Maybe("has_upstream_speed", factory.Faker("pyint", max_value=100000000), None)

    has_xconnect_id = NautobotBoolIterator()
    xconnect_id = factory.Maybe("has_xconnect_id", factory.Faker("word"), "")

    has_pp_info = NautobotBoolIterator()
    pp_info = factory.Maybe("has_pp_info", factory.Faker("word"), "")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
