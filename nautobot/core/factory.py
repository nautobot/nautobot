import factory
from factory.django import DjangoModelFactory

from nautobot.extras.models import Tag
from nautobot.utilities.factory import get_random_instances


class OrganizationalModelFactory(DjangoModelFactory):
    # TODO random created/last_updated values?
    # TODO random custom_field data?
    # TODO random relationships?
    # TODO random dynamic-groups?
    # TODO random notes?
    pass


class PrimaryModelFactory(DjangoModelFactory):
    # TODO random created/last_updated values?
    # TODO random custom_field data?
    # TODO random relationships?
    # TODO random dynamic-groups?
    # TODO random notes?

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.tags.set(extracted)
            else:
                self.tags.set(get_random_instances(Tag.objects.get_for_model(self._meta.model)))
