from datetime import timezone

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
import factory
import faker

from nautobot.core.choices import ColorChoices
from nautobot.core.factory import (
    BaseModelFactory,
    get_random_instances,
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices, WebhookHttpMethodChoices
from nautobot.extras.models import Contact, ExternalIntegration, ObjectChange, Role, Status, Tag, Team
from nautobot.extras.utils import change_logged_models_queryset, FeatureQuery, RoleModelsQuery, TaggableClassesQuery


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


class ObjectChangeFactory(BaseModelFactory):
    """ObjectChange model factory."""

    class Meta:
        model = ObjectChange

    class Params:
        has_user = NautobotBoolIterator(chance_of_getting_true=80)
        has_changed_object = NautobotBoolIterator(chance_of_getting_true=91)
        has_change_context_detail = NautobotBoolIterator()
        has_related_object_type = NautobotBoolIterator(chance_of_getting_true=11)
        has_related_object = NautobotBoolIterator()  # conditional on has_related_object_type

    user = factory.Maybe("has_user", random_instance(get_user_model()), None)
    request_id = factory.Faker("uuid4")
    # more updates than creates or deletes
    action = factory.Iterator(
        [
            ObjectChangeActionChoices.ACTION_CREATE,
            ObjectChangeActionChoices.ACTION_CREATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_DELETE,
        ]
    )
    changed_object_type = random_instance(lambda: change_logged_models_queryset(), allow_null=False)
    change_context = factory.Iterator(ObjectChangeEventContextChoices.CHOICES, getter=lambda choice: choice[0])
    change_context_detail = factory.Maybe("has_change_context_detail", factory.Faker("word"), "")
    related_object_type = factory.Maybe(
        "has_related_object_type",
        random_instance(lambda: change_logged_models_queryset(), allow_null=False),
        None,
    )
    object_data = factory.Faker("pydict")
    object_data_v2 = factory.Faker("pydict")

    @factory.lazy_attribute
    def user_name(self):
        if self.user:
            return self.user.username
        return faker.Faker().user_name()

    @factory.lazy_attribute
    def changed_object_id(self):
        if self.has_changed_object:
            queryset = self.changed_object_type.model_class().objects.all()
            if queryset.exists():
                return factory.random.randgen.choice(queryset).pk
        return faker.Faker().uuid4()

    @factory.lazy_attribute
    def related_object_id(self):
        if self.has_related_object_type:
            if self.has_related_object:
                queryset = self.related_object_type.model_class().objects.all()
                if queryset.exists():
                    return factory.random.randgen.choice(queryset).pk
            return faker.Faker().uuid4()
        return None

    @factory.post_generation
    def time(self, created, extracted, **kwargs):
        if created:
            if extracted:
                self.time = extracted
            else:
                self.time = faker.Faker().date_time(tzinfo=timezone.utc)

    @factory.post_generation
    def object_repr(self, created, extracted, **kwargs):
        if created:
            if extracted:
                self.object_repr = extracted
            elif self.changed_object is not None:
                self.object_repr = str(self.changed_object)
            else:
                self.object_repr = faker.Faker().word()


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
