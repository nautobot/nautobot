from django.utils.text import slugify

import factory

from nautobot.core.factory import OrganizationalModelFactory
from nautobot.extras.models import Tag
from nautobot.extras.utils import TaggableClassesQuery
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.factory import get_random_instances


# Tag isn't technically an OrganizationalModel, but it has all of its features **except** dynamic-groups
class TagFactory(OrganizationalModelFactory):
    class Meta:
        model = Tag
        exclude = ("has_description",)

    name = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[1])
    # Tag doesn't use our AutoSlugField, so we have to explicitly specify a slug
    slug = factory.LazyAttribute(lambda tag: slugify(tag.name))
    color = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[0])

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(get_random_instances(lambda: TaggableClassesQuery().as_queryset, minimum=1))
