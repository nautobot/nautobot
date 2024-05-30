from django.contrib.contenttypes.models import ContentType
import factory

from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.core.factory import (
    NautobotBoolIterator,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.models import Manufacturer


class CloudAccountFactory(PrimaryModelFactory):
    class Meta:
        model = CloudAccount
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
        model = CloudType
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
                self.content_types.add(ContentType.objects.get_for_model(CloudAccount))
