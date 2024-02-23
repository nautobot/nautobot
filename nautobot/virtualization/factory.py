import factory

from nautobot.core.factory import (
    get_random_instances,
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.models import Location, Platform, SoftwareImageFile, SoftwareVersion
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType, VirtualMachine


class ClusterTypeFactory(OrganizationalModelFactory):
    class Meta:
        model = ClusterType
        exclude = ("has_description",)

    name = UniqueFaker("color")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ClusterGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = ClusterGroup
        exclude = ("has_description",)

    name = UniqueFaker("color")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ClusterFactory(PrimaryModelFactory):
    class Meta:
        model = Cluster
        exclude = (
            "has_comments",
            "has_cluster_group",
            "has_location",
            "has_tenant",
        )

    name = UniqueFaker("color")
    cluster_type = random_instance(ClusterType, allow_null=False)

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    has_cluster_group = NautobotBoolIterator()
    cluster_group = factory.Maybe("has_cluster_group", random_instance(ClusterGroup), None)

    has_location = NautobotBoolIterator()
    location = factory.Maybe(
        "has_location", random_instance(lambda: Location.objects.get_for_model(Cluster), allow_null=False), None
    )

    has_tenant = NautobotBoolIterator()
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
            "has_software_version",
            "has_tenant",
            "has_vcpus",
        )

    name = UniqueFaker("word")
    cluster = random_instance(Cluster, allow_null=False)
    status = random_instance(lambda: Status.objects.get_for_model(VirtualMachine), allow_null=False)

    has_role = NautobotBoolIterator()
    role = factory.Maybe("has_role", random_instance(lambda: Role.objects.get_for_model(VirtualMachine)), None)

    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_platform = NautobotBoolIterator()
    platform = factory.Maybe("has_platform", random_instance(Platform), None)

    # TODO: Need to have associated VMInterfaces that these IPs belong to.
    # has_primary_ip4 = NautobotBoolIterator()
    # primary_ip4 = factory.Maybe("has_primary_ip4", random_instance(IPAddress), None)
    # has_primary_ip6 = NautobotBoolIterator()
    # primary_ip6 = factory.Maybe("has_primary_ip6", random_instance(IPAddress), None)

    has_vcpus = NautobotBoolIterator()
    vcpus = factory.Maybe("has_vcpus", factory.Faker("pyint", min_value=2, max_value=256, step=2), None)

    has_memory = NautobotBoolIterator()
    memory = factory.Maybe("has_memory", factory.Faker("pyint", min_value=1024, max_value=1024 * 1024, step=1024), None)

    has_disk = NautobotBoolIterator()
    disk = factory.Maybe("has_disk", factory.Faker("pyint"), None)

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    has_software_version = NautobotBoolIterator()
    software_version = factory.Maybe(
        "has_software_version",
        random_instance(SoftwareVersion),
        None,
    )

    @factory.post_generation
    def software_image_files(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.software_image_files.set(extracted)
        else:
            self.software_image_files.set(get_random_instances(SoftwareImageFile))


# TODO: add factories for VMInterface
