from django.contrib.contenttypes.models import ContentType
import factory

from nautobot.cloud import models
from nautobot.core.factory import (
    get_random_instances,
    NautobotBoolIterator,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.models import Manufacturer
from nautobot.ipam.models import Prefix


class CloudAccountFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudAccount
        exclude = ("has_description",)

    name = UniqueFaker("company")
    account_number = factory.Faker("pyint", min_value=4200000000, max_value=4294967294)
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    provider = random_instance(Manufacturer, allow_null=False)
    # has_secrets_group = NautobotBoolIterator()
    # secrets_group = factory.Maybe(
    #     "has_secrets_group",
    #     random_instance(SecretsGroup),
    # )


class CloudTypeFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudType
        exclude = ("has_description",)

    provider = random_instance(Manufacturer)
    name = factory.LazyAttributeSequence(lambda o, n: f"{o.provider.name} CloudType {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.add(ContentType.objects.get_for_model(models.CloudNetwork))


class CloudNetworkFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudNetwork
        exclude = ("has_description", "has_parent")

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudNetwork {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    cloud_type = random_instance(models.CloudType, allow_null=False)
    cloud_account = random_instance(models.CloudAccount, allow_null=False)
    has_parent = NautobotBoolIterator()
    extra_config = factory.Faker("pydict", value_types=[str, bool, int])

    @factory.lazy_attribute
    def parent(self):
        if not self.has_parent:
            return None
        candidate_parents = models.CloudNetwork.objects.filter(parent__isnull=True).exclude(pk=self.id)
        if candidate_parents.exists():
            return factory.random.randgen.choice(candidate_parents)
        return None

    @factory.post_generation
    def prefixes(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.prefixes.set(extracted)
            else:
                self.prefixes.set(get_random_instances(Prefix))


class CloudServiceFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudService
        exclude = ("has_cloudaccount",)

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudService {n + 1}")
    has_cloudaccount = NautobotBoolIterator()
    cloud_account = factory.Maybe("has_cloudaccount", random_instance(models.CloudAccount, allow_null=False), None)
    cloud_network = random_instance(models.CloudNetwork, allow_null=False)
    cloud_type = random_instance(models.CloudType, allow_null=False)
    extra_config = factory.Faker("pydict", value_types=[str, bool, int])
