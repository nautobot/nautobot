from django.contrib.contenttypes.models import ContentType
import factory
import faker

from nautobot.core.choices import ColorChoices
from nautobot.core.factory import (
    get_random_instances,
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    UniqueFaker,
)
from nautobot.extras.choices import WebhookHttpMethodChoices
from nautobot.extras.models import Contact, ExternalIntegration, Role, Status, Tag, Team
from nautobot.extras.utils import FeatureQuery, RoleModelsQuery, TaggableClassesQuery


class ContactFactory(PrimaryModelFactory):
    class Meta:
        model = Contact

    class Params:
        has_phone = NautobotBoolIterator()
        has_email = NautobotBoolIterator()
        has_address = NautobotBoolIterator()
        has_comments = NautobotBoolIterator()

    name = factory.Faker("name")
    phone = factory.Maybe("has_phone", factory.Faker("phone_number"), "")
    email = factory.Maybe("has_email", factory.Faker("email"), "")
    address = factory.Maybe("has_address", factory.Faker("address"), "")
    comments = factory.Maybe("has_comments", factory.Faker("text", max_nb_chars=200), "")


class ExternalIntegrationFactory(PrimaryModelFactory):
    """ExternalIntegration model factory."""

    class Meta:
        model = ExternalIntegration

    class Params:
        has_extra_config = NautobotBoolIterator()
        has_http_method = NautobotBoolIterator()
        has_headers = NautobotBoolIterator()
        has_ca_file_path = NautobotBoolIterator()

    name = UniqueFaker("bs")
    remote_url = factory.Faker("url", schemes=["http", "https", "ssh"])
    verify_ssl = factory.Faker("boolean")
    timeout = factory.Faker("pyint", min_value=0, max_value=300)
    extra_config = factory.Maybe(
        "has_extra_config",
        factory.Faker("pydict", allowed_types=[bool, int, str]),
        None,
    )

    http_method = factory.Maybe(
        "has_http_method",
        factory.Iterator(WebhookHttpMethodChoices.CHOICES, getter=lambda choice: choice[0]),
        "",
    )
    headers = factory.Maybe(
        "has_headers",
        factory.Faker("pydict", allowed_types=[bool, int, str]),
        None,
    )
    ca_file_path = factory.Maybe(
        "has_ca_file_path",
        factory.LazyAttributeSequence(lambda o, n: f"{o.name}/file/path/{n + 1}"),
        "",
    )


class RoleFactory(OrganizationalModelFactory):
    """Role model factory."""

    class Meta:
        model = Role
        exclude = (
            "has_description",
            "has_weight",
        )

    name = factory.LazyFunction(
        lambda: "".join(word.title() for word in faker.Faker().words(nb=2, part_of_speech="adjective", unique=True))
    )
    color = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[0])
    has_weight = NautobotBoolIterator()
    weight = factory.Maybe("has_weight", factory.Faker("pyint"), None)

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(get_random_instances(lambda: RoleModelsQuery().as_queryset(), minimum=1))


class StatusFactory(OrganizationalModelFactory):
    """Status isn't technically an OrganizationalModel, but it has all of its features **except** dynamic-groups."""

    class Meta:
        model = Status
        exclude = ("has_description",)

    name = factory.LazyFunction(
        lambda: "".join(word.title() for word in faker.Faker().words(nb=2, part_of_speech="adjective", unique=True))
    )
    color = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[0])

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(
                    get_random_instances(
                        lambda: ContentType.objects.filter(FeatureQuery("statuses").get_query()), minimum=1
                    )
                )


class TeamFactory(PrimaryModelFactory):
    class Meta:
        model = Team

    class Params:
        has_phone = NautobotBoolIterator()
        has_email = NautobotBoolIterator()
        has_address = NautobotBoolIterator()
        has_comments = NautobotBoolIterator()

    name = factory.Faker("job")
    phone = factory.Maybe("has_phone", factory.Faker("phone_number"), "")
    email = factory.Maybe("has_email", factory.Faker("email"), "")
    address = factory.Maybe("has_address", factory.Faker("address"), "")
    comments = factory.Maybe("has_comments", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def contacts(self, create, extract, **kwargs):
        """Assign some contacts to a team after generation"""
        self.contacts.set(get_random_instances(Contact))


class TagFactory(OrganizationalModelFactory):
    """Tag isn't technically an OrganizationalModel, but it has all of its features **except** dynamic-groups."""

    class Meta:
        model = Tag
        exclude = ("has_description",)

    name = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[1])
    color = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[0])

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(get_random_instances(lambda: TaggableClassesQuery().as_queryset(), minimum=2))
