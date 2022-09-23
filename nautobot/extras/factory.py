import factory.random

from nautobot.extras.models import Tag


def get_random_tags_for_model(model):
    """Return between 0 and n tags applicable to the given model, where n is the total number of applicable tags.

    This is not an evenly weighted distribution (all tag counts equally likely), because in most of our code,
    the relevant code paths distinguish between 0 tags, 1 tag, or >1 tags - there's not a functional difference between
    "2 tags" and "10 tags" in most cases. Therefore, this implementation provides:
        - 1/3 chance of no tags
        - 1/3 chance of 1 tag
        - 1/3 chance of (2 to n) tags, where each possibility is equally likely within this range
    """
    branch = factory.random.randgen.randrange(0, 3)
    tag_count = Tag.objects.get_for_model(model).count()
    if branch == 0 or tag_count == 0:
        # No tags
        return []
    if branch == 1 or tag_count < 2:
        # Exactly one tag
        return [factory.random.randgen.choice(Tag.objects.get_for_model(model))]
    # Between 2 and n tags
    return factory.random.randgen.sample(
        population=list(Tag.objects.get_for_model(model)),
        k=factory.random.randgen.randint(2, Tag.objects.get_for_model(model).count()),
    )
