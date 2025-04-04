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
from nautobot.extras.utils import FeatureQuery
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
    # TODO: once SecretsGroupFactory is implemented:
    # has_secrets_group = NautobotBoolIterator()
    # secrets_group = factory.Maybe(
    #     "has_secrets_group",
    #     random_instance(SecretsGroup),
    # )


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


class CloudNetworkFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudNetwork
        exclude = ("has_description", "has_parent")

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudNetwork {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    cloud_resource_type = random_instance(
        lambda: models.CloudResourceType.objects.get_for_model(models.CloudNetwork), allow_null=False
    )
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
                # TODO Investigate https://github.com/nautobot/nautobot/actions/runs/11019738391/job/30603271529
                # to uncomment the line below.
                # self.prefixes.set(get_random_instances(Prefix))
                self.prefixes.set(get_random_instances(model_or_queryset_or_lambda=Prefix, maximum=1))


class CloudServiceFactory(PrimaryModelFactory):
    class Meta:
        model = models.CloudService
        exclude = ("has_cloudaccount", "has_description")

    name = factory.LazyAttributeSequence(lambda o, n: f"CloudService {n + 1}")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    has_cloudaccount = NautobotBoolIterator()
    cloud_account = factory.Maybe("has_cloudaccount", random_instance(models.CloudAccount, allow_null=False), None)
    cloud_resource_type = random_instance(
        lambda: models.CloudResourceType.objects.get_for_model(models.CloudService), allow_null=False
    )
    extra_config = factory.Faker("pydict", value_types=[str, bool, int])

    @factory.post_generation
    def cloud_networks(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.cloud_networks.set(extracted)
            else:
                self.cloud_networks.set(get_random_instances(models.CloudNetwork))
