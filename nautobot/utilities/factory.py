import factory
import factory.random


def random_instance(model):
    """
    Factory helper - construct a lambda function that retrieves a random instance of the given model.

    Example:
        class ObjectFactory(DjangoModelFactory):
            class Meta:
                model = Object
                exclude = ("has_group,")

            # Required foreign key
            user = random_instance(User)

            # Optional foreign key
            has_group = factory.Faker("pybool")
            group = factory.Maybe("has_group", random_instance(Group), None)
    """
    return factory.LazyFunction(
        lambda: factory.random.randgen.choice(model.objects.all()) if model.objects.count() else None
    )


class UniqueFaker(factory.Faker):
    """https://github.com/FactoryBoy/factory_boy/pull/820#issuecomment-1004802669"""

    @classmethod
    def _get_faker(cls, locale=None):
        return super()._get_faker(locale=locale).unique
