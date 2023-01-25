import factory

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory, UniqueFaker, random_instance
from nautobot.dcim.models import Site, Location, Platform
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType, VirtualMachine


class ClusterTypeFactory(OrganizationalModelFactory):
    class Meta:
        model = ClusterType
        exclude = ("has_description",)

    name = UniqueFaker("color")
    # Slug isn't defined here since it inherits from name.

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ClusterGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = ClusterGroup
        exclude = ("has_description",)

    name = UniqueFaker("color")
    # Slug isn't defined here since it inherits from name.

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ClusterFactory(PrimaryModelFactory):
    class Meta:
        model = Cluster
        exclude = (
            "has_comments",
            "has_cluster_group",
            "has_location",
            "has_site",
            "has_tenant",
        )

    name = UniqueFaker("color")
    cluster_type = random_instance(ClusterType, allow_null=False)

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    has_cluster_group = factory.Faker("pybool")
    cluster_group = factory.Maybe("has_cluster_group", random_instance(ClusterGroup), None)

    has_location = factory.Faker("pybool")
    location = factory.Maybe(
        "has_location", random_instance(lambda: Location.objects.get_for_model(Cluster), allow_null=False), None
    )

    has_site = factory.Faker("pybool")
    site = factory.Maybe(
        "has_location",
        factory.LazyAttribute(lambda l: l.location.site or l.location.base_site),
        factory.Maybe(
            "has_site",
            random_instance(Site),
            None,
        ),
    )

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VirtualMachineFactory(PrimaryModelFactory):
    class Meta:
        model = VirtualMachine
        exclude = (
            "has_comments",
            "has_disk",
            "has_memory",
            "has_platform",
            # TODO
            # "has_primary_ip4",
            # "has_primary_ip6",
            "has_role",
            "has_tenant",
            "has_vcpus",
        )

    name = UniqueFaker("word")
    cluster = random_instance(Cluster, allow_null=False)
    status = random_instance(lambda: Status.objects.get_for_model(VirtualMachine), allow_null=False)

    has_role = factory.Faker("pybool")
    role = factory.Maybe("has_role", random_instance(lambda: Role.objects.get_for_model(VirtualMachine)), None)

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_platform = factory.Faker("pybool")
    platform = factory.Maybe("has_platform", random_instance(Platform), None)

    # TODO: Need to have associated VMInterfaces that these IPs belong to.
    # has_primary_ip4 = factory.Faker("pybool")
    # primary_ip4 = factory.Maybe("has_primary_ip4", random_instance(IPAddress), None)
    # has_primary_ip6 = factory.Faker("pybool")
    # primary_ip6 = factory.Maybe("has_primary_ip6", random_instance(IPAddress), None)

    has_vcpus = factory.Faker("pybool")
    vcpus = factory.Maybe("has_vcpus", factory.Faker("pyint", min_value=2, max_value=256, step=2), None)

    has_memory = factory.Faker("pybool")
    memory = factory.Maybe("has_memory", factory.Faker("pyint", min_value=1024, max_value=1024 * 1024, step=1024), None)

    has_disk = factory.Faker("pybool")
    disk = factory.Maybe("has_disk", factory.Faker("pyint"), None)

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


# TODO: add factories for VMInterface
