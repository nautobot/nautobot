import factory
from factory.django import DjangoModelFactory

from nautobot.extras.factory import get_random_tags_for_model
from nautobot.tenancy.models import TenantGroup, Tenant
from nautobot.utilities.factory import random_instance, UniqueFaker


class TenantGroupFactory(DjangoModelFactory):
    class Meta:
        model = TenantGroup
        exclude = (
            "has_description",
            "has_parent",
        )

    name = UniqueFaker("company")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_parent = factory.Faker("pybool")
    parent = factory.Maybe("has_parent", random_instance(TenantGroup), None)

    # TODO custom field data?


class TenantFactory(DjangoModelFactory):
    class Meta:
        model = Tenant
        exclude = (
            "has_comments",
            "has_description",
            "has_group",
        )

    name = UniqueFaker("company")

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_group = factory.Faker("pybool")
    group = factory.Maybe("has_group", random_instance(TenantGroup), None)

    # TODO custom field data?

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.tags.set(extracted)
            else:
                self.tags.set(get_random_tags_for_model(self._meta.model))
