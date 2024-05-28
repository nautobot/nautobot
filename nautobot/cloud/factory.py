import factory

from nautobot.cloud.models import CloudAccount
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
