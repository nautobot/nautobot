import factory
import factory.random


def random_instance(model_or_queryset):
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
    if hasattr(model_or_queryset, "objects"):
        queryset = model_or_queryset.objects.all()
    else:
        queryset = model_or_queryset
    return factory.LazyFunction(lambda: factory.random.randgen.choice(queryset) if queryset.count() else None)


def get_random_instances(model_or_queryset, minimum=0, maximum=None):
    """
    Factory helper - retrieve a random number of instances of the given model.

    This is different from random_instance() in that it's not itself a lazy function generator, but should instead be
    called only from within a @lazy_attribute or @post_generation function.

    This is not an evenly weighted distribution (all counts equally likely), because in most of our code,
    the relevant code paths distinguish between 0, 1, or >1 instances - there's not a functional difference between
    "2 instances" and "10 instances" in most cases. Therefore, this implementation provides:
        - 1/3 chance of no instances
        - 1/3 chance of 1 instance
        - 1/3 chance of (2 to n) instances, where each possibility is equally likely within this range
    """
    branch = factory.random.randgen.randint(0, 2)
    if hasattr(model_or_queryset, "objects"):
        queryset = model_or_queryset.objects.all()
    else:
        queryset = model_or_queryset
    count = queryset.count()
    if maximum is None:
        maximum = count
    if branch == 0 or count == 0 or maximum == 0:
        return []
    if branch == 1 or count == 1 or maximum == 1:
        # Because random_instance returns a LazyFunction, we need to evaluate it now to get an actual instance
        # The official stance of factory-boy maintainers is that evaluate() is a private method, but there doesn't
        # seem to be any convenient alternative way to do this at present.
        return [random_instance(queryset).evaluate(None, None, {"locale": None})]
    return factory.random.randgen.sample(
        population=list(queryset),
        k=factory.random.randgen.randint(2, min(maximum, count)),
    )


class UniqueFaker(factory.Faker):
    """https://github.com/FactoryBoy/factory_boy/pull/820#issuecomment-1004802669"""

    @classmethod
    def _get_faker(cls, locale=None):
        return super()._get_faker(locale=locale).unique
