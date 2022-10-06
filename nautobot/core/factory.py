import factory
from factory.django import DjangoModelFactory

from nautobot.extras.models import Tag
from nautobot.utilities.factory import get_random_instances


class BaseModelFactory(DjangoModelFactory):
    """Base class for all Nautobot model factories."""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override default DjangoModelFactory behavior to call validated_save() instead of just save()."""
        obj = model_class(*args, **kwargs)
        obj.validated_save()
        return obj


class OrganizationalModelFactory(BaseModelFactory):
    """Factory base class for OrganizationalModel subclasses."""

    # TODO random created/last_updated values?
    # TODO random custom_field data?
    # TODO random relationships?
    # TODO random dynamic-groups?
    # TODO random notes?


class PrimaryModelFactory(BaseModelFactory):
    """Factory base class for PrimaryModel subclasses."""

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
