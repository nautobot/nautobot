import factory
import faker

from django.db.models import Q

from nautobot.circuits import choices
from nautobot.circuits.models import CircuitTermination, CircuitType, Circuit, Provider, ProviderNetwork
from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory
from nautobot.dcim import models as dcim_models
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant
from nautobot.utilities.factory import random_instance, UniqueFaker


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


class ProviderNetworkFactory(PrimaryModelFactory):
    class Meta:
        model = ProviderNetwork
        exclude = ("has_description", "has_comments")

    name = factory.LazyAttribute(
        lambda o: f"{o.provider.name} Network {faker.Faker().word(part_of_speech='noun')}"[:100]
    )
    provider = random_instance(Provider, allow_null=False)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("sentence"), "")


class CircuitTerminationFactory(PrimaryModelFactory):
    class Meta:
        model = CircuitTermination
        exclude = (
            "has_site",
            "has_location",
            "has_port_speed",
            "has_upstream_speed",
            "has_xconnect_id",
            "has_pp_info",
            "has_description",
        )

    circuit = random_instance(
        lambda: Circuit.objects.filter(Q(termination_a__isnull=True) | Q(termination_z__isnull=True)), allow_null=False
    )

    @factory.lazy_attribute
    def term_side(self):
        side_choices = [c[0] for c in choices.CircuitTerminationSideChoices.CHOICES]
        tried = []
        for random_side in faker.Faker().random_elements(elements=side_choices, unique=True, length=len(side_choices)):
            tried.append(random_side)
            if getattr(self.circuit, f"termination_{random_side.lower()}") is None:
                return random_side

    has_site = factory.Faker("pybool")
    site = factory.Maybe("has_site", random_instance(dcim_models.Site, allow_null=False))

    has_location = factory.Maybe("has_site", factory.Faker("pybool"), False)
    location = factory.Maybe(
        "has_location",
        factory.LazyAttribute(
            lambda o: dcim_models.Location.objects.get_for_model(CircuitTermination).filter(site=o.site).first()
        ),
        None,
    )

    @factory.lazy_attribute
    def provider_network(self):
        # site and provider_network are mutually exclusive but if site is null provider_network is required
        if self.has_site:
            return None
        if ProviderNetwork.objects.filter(provider=self.circuit.provider).exists():
            return ProviderNetwork.objects.filter(provider=self.circuit.provider).first()
        return ProviderNetworkFactory(provider=self.circuit.provider)

    has_port_speed = factory.Faker("pybool")
    port_speed = factory.Maybe("has_port_speed", factory.Faker("pyint", max_value=100000000), None)

    has_upstream_speed = factory.Faker("pybool")
    upstream_speed = factory.Maybe("has_upstream_speed", factory.Faker("pyint", max_value=100000000), None)

    has_xconnect_id = factory.Faker("pybool")
    xconnect_id = factory.Maybe("has_xconnect_id", factory.Faker("word"), "")

    has_pp_info = factory.Faker("pybool")
    pp_info = factory.Maybe("has_pp_info", factory.Faker("word"), "")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")
