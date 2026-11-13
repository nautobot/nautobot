from django.contrib.contenttypes.models import ContentType
import factory

from nautobot.cloud import models
from nautobot.core.factory import (
    BaseModelFactory,
    get_random_instances,
    NautobotBoolIterator,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.models import Location, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.tenancy.models import Tenant


def resource_types_for(model, provider=None):
    """Cloud resource types applicable to the given model, optionally limited to one provider."""
    queryset = models.CloudResourceType.objects.get_for_model(model)
    if provider is not None:
        queryset = queryset.filter(provider=provider)
    return queryset


def accounts_with_resource_types_for(model):
    """Cloud accounts whose provider has at least one cloud resource type applicable to the given model."""
    return models.CloudAccount.objects.filter(
        provider__cloud_resource_types__content_types=ContentType.objects.get_for_model(model)
    ).distinct()


def random_choice_or_none(queryset):
    return factory.random.randgen.choice(queryset) if queryset.exists() else None


class CloudAccountFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudAccount
        exclude = ("has_cloud_account_group", "has_description", "has_tenant")

    name = UniqueFaker("company")
    account_number = factory.Faker("pyint", min_value=4200000000, max_value=4294967294)
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    status = random_instance(lambda: Status.objects.get_for_model(models.CloudAccount), allow_null=False)
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)
    has_cloud_account_group = NautobotBoolIterator()
    # TODO: once SecretsGroupFactory is implemented:
    # has_secrets_group = NautobotBoolIterator()
    # secrets_group = factory.Maybe(
    #     "has_secrets_group",
    #     random_instance(SecretsGroup),
    # )

    @factory.lazy_attribute
    def provider(self):
        """Prefer providers that have cloud resource types, so that networks and services can be created for them."""
        candidates = Manufacturer.objects.filter(cloud_resource_types__isnull=False).distinct()
        if not candidates.exists():
            candidates = Manufacturer.objects.all()
        return factory.random.randgen.choice(candidates)

    @factory.lazy_attribute
    def cloud_account_group(self):
        if not self.has_cloud_account_group:
            return None
        return random_choice_or_none(
            models.CloudAccountGroup.objects.filter(cloud_resource_type__provider=self.provider)
        )


class CloudAccountGroupFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudAccountGroup
        exclude = ("has_description", "has_parent")

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudAccountGroup {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    cloud_resource_type = random_instance(lambda: resource_types_for(models.CloudAccountGroup), allow_null=False)
    has_parent = NautobotBoolIterator()

    @factory.lazy_attribute
    def parent(self):
        if not self.has_parent:
            return None
        return random_choice_or_none(
            models.CloudAccountGroup.objects.filter(cloud_resource_type__provider=self.cloud_resource_type.provider)
        )


class CloudResourceTypeFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudResourceType
        exclude = ("has_description",)

    provider = random_instance(Manufacturer)
    name = factory.LazyAttributeSequence(lambda o, n: f"{o.provider.name} CloudResourceType {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    # TODO: if we add a `config_schema` here, then CloudNetworkFactory and CloudServiceFactory have to follow it...

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(
                    get_random_instances(
                        lambda: ContentType.objects.filter(FeatureQuery("cloud_resource_types").get_query()), minimum=1
                    )
                )


class CloudResourceGroupFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudResourceGroup
        exclude = ("has_description", "has_location", "has_provider_resource_id")

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudResourceGroup {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    cloud_account = random_instance(
        lambda: accounts_with_resource_types_for(models.CloudResourceGroup), allow_null=False
    )
    has_location = NautobotBoolIterator()
    location = factory.Maybe(
        "has_location",
        random_instance(
            lambda: Location.objects.filter(
                location_type__content_types=ContentType.objects.get_for_model(models.CloudResourceGroup)
            )
        ),
        None,
    )
    has_provider_resource_id = NautobotBoolIterator()
    provider_resource_id = factory.Maybe(
        "has_provider_resource_id",
        factory.Sequence(lambda n: f"/subscriptions/{n:08d}/resourceGroups/resource-group-{n}"),
        None,
    )
    extra_config = factory.Faker("pydict", value_types=[str, bool, int])

    @factory.lazy_attribute
    def cloud_resource_type(self):
        return factory.random.randgen.choice(
            resource_types_for(models.CloudResourceGroup, provider=self.cloud_account.provider)
        )


class CloudNetworkFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudNetwork
        exclude = (
            "has_cloud_resource_group",
            "has_description",
            "has_location",
            "has_parent",
            "has_provider_resource_id",
            "has_role",
            "has_tenant",
        )

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudNetwork {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    cloud_account = random_instance(lambda: accounts_with_resource_types_for(models.CloudNetwork), allow_null=False)
    has_cloud_resource_group = NautobotBoolIterator()
    has_parent = NautobotBoolIterator()
    status = random_instance(lambda: Status.objects.get_for_model(models.CloudNetwork), allow_null=False)
    has_role = NautobotBoolIterator()
    role = factory.Maybe("has_role", random_instance(lambda: Role.objects.get_for_model(models.CloudNetwork)), None)
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)
    has_location = NautobotBoolIterator()
    location = factory.Maybe(
        "has_location",
        random_instance(
            lambda: Location.objects.filter(
                location_type__content_types=ContentType.objects.get_for_model(models.CloudNetwork)
            )
        ),
        None,
    )
    has_provider_resource_id = NautobotBoolIterator()
    provider_resource_id = factory.Maybe(
        "has_provider_resource_id",
        factory.Sequence(lambda n: f"arn:aws:ec2:us-east-1:000000000000:vpc/vpc-{n:017x}"),
        None,
    )
    extra_config = factory.Faker("pydict", value_types=[str, bool, int])

    @factory.lazy_attribute
    def cloud_resource_type(self):
        return factory.random.randgen.choice(
            resource_types_for(models.CloudNetwork, provider=self.cloud_account.provider)
        )

    @factory.lazy_attribute
    def cloud_resource_group(self):
        if not self.has_cloud_resource_group:
            return None
        return random_choice_or_none(models.CloudResourceGroup.objects.filter(cloud_account=self.cloud_account))

    @factory.lazy_attribute
    def parent(self):
        if not self.has_parent:
            return None
        return random_choice_or_none(
            models.CloudNetwork.objects.filter(parent__isnull=True, cloud_account=self.cloud_account).exclude(
                pk=self.id
            )
        )

    @factory.post_generation
    def prefixes(self, create, extracted, **kwargs):
        if create:
            if not extracted:
                extracted = get_random_instances(Prefix)
            for prefix in extracted:
                CloudNetworkPrefixAssignmentFactory.create(cloud_network=self, prefix=prefix)


class CloudNetworkPrefixAssignmentFactory(BaseModelFactory):
    class Meta:
        model = models.CloudNetworkPrefixAssignment


class CloudServiceFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudService
        exclude = (
            "has_cloudaccount",
            "has_cloud_resource_group",
            "has_description",
            "has_location",
            "has_provider_resource_id",
            "has_role",
            "has_tenant",
        )

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudService {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    has_cloudaccount = NautobotBoolIterator()
    cloud_account = factory.Maybe(
        "has_cloudaccount",
        random_instance(lambda: accounts_with_resource_types_for(models.CloudService), allow_null=False),
        None,
    )
    has_cloud_resource_group = NautobotBoolIterator()
    status = random_instance(lambda: Status.objects.get_for_model(models.CloudService), allow_null=False)
    has_role = NautobotBoolIterator()
    role = factory.Maybe("has_role", random_instance(lambda: Role.objects.get_for_model(models.CloudService)), None)
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)
    has_location = NautobotBoolIterator()
    location = factory.Maybe(
        "has_location",
        random_instance(
            lambda: Location.objects.filter(
                location_type__content_types=ContentType.objects.get_for_model(models.CloudService)
            )
        ),
        None,
    )
    has_provider_resource_id = NautobotBoolIterator()
    provider_resource_id = factory.Maybe(
        "has_provider_resource_id",
        factory.Sequence(lambda n: f"//compute.googleapis.com/projects/project-{n}/regions/region/services/service"),
        None,
    )
    extra_config = factory.Faker("pydict", value_types=[str, bool, int])

    @factory.lazy_attribute
    def cloud_resource_type(self):
        provider = self.cloud_account.provider if self.cloud_account else None
        return factory.random.randgen.choice(resource_types_for(models.CloudService, provider=provider))

    @factory.lazy_attribute
    def cloud_resource_group(self):
        if not self.has_cloud_resource_group or self.cloud_account is None:
            return None
        return random_choice_or_none(models.CloudResourceGroup.objects.filter(cloud_account=self.cloud_account))

    @factory.post_generation
    def cloud_networks(self, create, extracted, **kwargs):
        if create:
            if not extracted:
                extracted = get_random_instances(models.CloudNetwork)
            for cloud_network in extracted:
                CloudServiceNetworkAssignmentFactory.create(cloud_service=self, cloud_network=cloud_network)

    @factory.post_generation
    def ip_addresses(self, create, extracted, **kwargs):
        if create:
            if not extracted:
                extracted = get_random_instances(IPAddress, maximum=3)
            for ip_address in extracted:
                CloudServiceIPAddressAssignmentFactory.create(cloud_service=self, ip_address=ip_address)


class CloudServiceNetworkAssignmentFactory(BaseModelFactory):
    class Meta:
        model = models.CloudServiceNetworkAssignment


class CloudServiceIPAddressAssignmentFactory(BaseModelFactory):
    class Meta:
        model = models.CloudServiceIPAddressAssignment
