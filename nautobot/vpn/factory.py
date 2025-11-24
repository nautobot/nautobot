from django.contrib.contenttypes.models import ContentType
import factory
import faker

from nautobot.core.factory import (
    get_random_instances,
    NautobotBoolIterator,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.models import Interface
from nautobot.extras.models import DynamicGroup, Role, SecretsGroup, Status
from nautobot.ipam.models import Prefix
from nautobot.tenancy.models import Tenant
from nautobot.vpn import choices, models


class VPNPhase1PolicyFactory(PrimaryModelFactory):
    class Meta:
        model = models.VPNPhase1Policy
        exclude = ("has_description", "has_tenant")

    name = UniqueFaker("word")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    ike_version = factory.Faker("random_element", elements=choices.IkeVersionChoices.values())
    encryption_algorithm = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(choices.EncryptionAlgorithmChoices.values(), unique=True))
    )
    integrity_algorithm = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(choices.IntegrityAlgorithmChoices.values(), unique=True))
    )
    dh_group = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(choices.DhGroupChoices.values(), unique=True))
    )
    lifetime_seconds = factory.Faker("pyint", min_value=0, max_value=3600, step=15)
    lifetime_kb = factory.Faker("pyint", min_value=0, max_value=1024)
    authentication_method = factory.Faker("random_element", elements=choices.AuthenticationMethodChoices.values())
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VPNPhase2PolicyFactory(PrimaryModelFactory):
    class Meta:
        model = models.VPNPhase2Policy
        exclude = ("has_description", "has_tenant")

    name = UniqueFaker("word")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    encryption_algorithm = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(choices.EncryptionAlgorithmChoices.values(), unique=True))
    )
    integrity_algorithm = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(choices.IntegrityAlgorithmChoices.values(), unique=True))
    )
    pfs_group = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(choices.DhGroupChoices.values(), unique=True))
    )
    lifetime = factory.Faker("pyint", min_value=0, max_value=3600, step=15)
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VPNProfileFactory(PrimaryModelFactory):
    class Meta:
        model = models.VPNProfile
        exclude = ("has_description", "has_role", "has_secrets_group", "has_extra_options", "has_tenant")

    name = UniqueFaker("word")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(models.VPNProfile), allow_null=True),
        None,
    )
    has_secrets_group = NautobotBoolIterator()
    secrets_group = factory.Maybe(
        "has_secrets_group",
        random_instance(SecretsGroup),
    )
    keepalive_enabled = NautobotBoolIterator()
    keepalive_interval = factory.Faker("pyint", min_value=0, max_value=3600, step=3)
    keepalive_retries = factory.Faker("pyint", min_value=0, max_value=180, step=3)
    nat_traversal = NautobotBoolIterator()
    has_extra_options = NautobotBoolIterator()
    extra_options = factory.Maybe(
        "has_extra_options", factory.Faker("pydict", nb_elements=2, value_types=[str, bool, int]), None
    )
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    @factory.post_generation
    def vpn_phase1_policies(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.vpn_phase1_policies.set(extracted)
            else:
                self.vpn_phase1_policies.set(get_random_instances(models.VPNPhase1Policy, minimum=1))

    @factory.post_generation
    def vpn_phase2_policies(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.vpn_phase2_policies.set(extracted)
            else:
                self.vpn_phase2_policies.set(get_random_instances(models.VPNPhase2Policy, minimum=1))


class VPNFactory(PrimaryModelFactory):
    class Meta:
        model = models.VPN
        exclude = ("has_description", "has_profile", "has_role", "has_tenant")

    name = UniqueFaker("word")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    vpn_id = factory.Faker("word")
    has_profile = NautobotBoolIterator()
    vpn_profile = factory.Maybe("has_profile", random_instance(models.VPNProfile), None)
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(models.VPN), allow_null=True),
        None,
    )
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VPNTunnelFactory(PrimaryModelFactory):
    class Meta:
        model = models.VPNTunnel
        exclude = ("has_description", "has_profile", "has_vpn", "has_role", "has_tenant")

    name = UniqueFaker("word")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    tunnel_id = factory.Faker("word")
    has_profile = NautobotBoolIterator()
    vpn_profile = factory.Maybe("has_profile", random_instance(models.VPNProfile), None)
    has_vpn = NautobotBoolIterator()
    vpn = factory.Maybe("has_vpn", random_instance(models.VPN), None)
    status = random_instance(
        lambda: Status.objects.get_for_model(models.VPNTunnel),
        allow_null=False,
    )
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(models.VPNTunnel), allow_null=True),
        None,
    )
    encapsulation = factory.Faker("random_element", elements=choices.EncapsulationChoices.values())
    endpoint_a = factory.Sequence(lambda n: models.VPNTunnelEndpoint.objects.all()[n])
    endpoint_z = factory.Sequence(lambda n: models.VPNTunnelEndpoint.objects.all()[n + 10])
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VPNTunnelEndpointFactory(PrimaryModelFactory):
    class Meta:
        model = models.VPNTunnelEndpoint
        exclude = ("has_source_interface", "has_profile", "has_role", "has_tenant")

    has_source_interface = NautobotBoolIterator()
    source_interface = factory.Maybe(
        "has_source_interface",
        random_instance(
            lambda: Interface.objects.filter(vpn_tunnel_endpoints_src_int__isnull=True, device__isnull=False)
        ),
        None,
    )
    source_fqdn = factory.Maybe("has_source_interface", "", factory.Faker("hostname"))

    @factory.lazy_attribute
    def tunnel_interface(self):
        """Filter tunnel interfaces on the same device as source_interface."""
        if self.has_source_interface:
            qs = Interface.objects.filter(type="tunnel", device=self.source_interface.device)
            return factory.random.randgen.choice(qs) if qs.exists() else None
        return None

    has_profile = NautobotBoolIterator()
    vpn_profile = factory.Maybe("has_profile", random_instance(models.VPNProfile), None)
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(models.VPNTunnelEndpoint), allow_null=True),
        None,
    )
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    @factory.post_generation
    def protected_prefixes(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.protected_prefixes.set(extracted)
            else:
                # TODO Investigate https://github.com/nautobot/nautobot/actions/runs/11019738391/job/30603271529
                # to uncomment the line below.
                # self.protected_prefixes.set(get_random_instances(Prefix))
                self.protected_prefixes.set(get_random_instances(model_or_queryset_or_lambda=Prefix, maximum=1))

    @factory.post_generation
    def protected_prefixes_dg(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.protected_prefixes_dg.set(extracted)
            else:
                self.protected_prefixes_dg.set(
                    get_random_instances(
                        DynamicGroup.objects.filter(content_type=ContentType.objects.get_for_model(Prefix)), minimum=0
                    )
                )
