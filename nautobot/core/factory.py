from ipaddress import IPv6Address, IPV6LENGTH, IPv6Network

import factory
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider

from nautobot.extras.models import Tag
from nautobot.utilities.factory import get_random_instances


class BaseModelFactory(DjangoModelFactory):
    """Base class for all Nautobot model factories."""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override default DjangoModelFactory behavior to call validated_save() instead of just save()."""
        using = kwargs.pop("using", cls._meta.database)
        obj = model_class(*args, **kwargs)
        obj.validated_save(using=using)
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


class NautobotFakerProvider(BaseProvider):
    """Faker provider to generate fake data specific to Nautobot or network automation use cases."""

    def ipv6_network(self) -> str:
        """Produce a random IPv6 network with a valid CIDR greater than 0"""
        address = str(IPv6Address(self.generator.random.randint(0, (2**IPV6LENGTH) - 1)))
        address += "/" + str(self.generator.random.randint(1, IPV6LENGTH))
        address = str(IPv6Network(address, strict=False))
        return address


factory.Faker.add_provider(NautobotFakerProvider)
