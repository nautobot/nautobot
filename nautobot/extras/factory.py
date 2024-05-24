from datetime import timedelta, timezone

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
import factory
import faker

from nautobot.core.choices import ColorChoices
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.factory import (
    BaseModelFactory,
    get_random_instances,
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.core.templatetags.helpers import bettertitle
from nautobot.extras.choices import (
    JobResultStatusChoices,
    LogLevelChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
    WebhookHttpMethodChoices,
)
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, CHANGELOG_MAX_OBJECT_REPR
from nautobot.extras.models import (
    Contact,
    ExternalIntegration,
    Job,
    JobLogEntry,
    JobResult,
    ObjectChange,
    Role,
    StaticGroup,
    StaticGroupAssociation,
    Status,
    Tag,
    Team,
)
from nautobot.extras.utils import (
    change_logged_models_queryset,
    FeatureQuery,
    RoleModelsQuery,
    TaggableClassesQuery,
)
from nautobot.tenancy.models import Tenant


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
    comments = factory.Maybe("has_comments", factory.Faker("text"), "")


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


class JobLogEntryFactory(BaseModelFactory):
    """JobLogEntry model factory."""

    class Meta:
        model = JobLogEntry

    class Params:
        has_message = NautobotBoolIterator(chance_of_getting_true=90)
        has_log_object = NautobotBoolIterator()
        has_absolute_url = NautobotBoolIterator()

    job_result = random_instance(JobResult, allow_null=False)
    log_level = factory.Iterator(LogLevelChoices.CHOICES, getter=lambda choice: choice[0])
    grouping = factory.Faker("word")
    message = factory.Maybe("has_message", factory.Faker("sentence"), "")
    log_object = factory.Maybe("has_log_object", factory.Faker("word"), "")
    absolute_url = factory.Maybe("has_absolute_url", factory.Faker("uri_path"), "")

    @factory.lazy_attribute
    def created(self):
        if self.job_result.date_done:
            return faker.Faker().date_time_between_dates(
                datetime_start=self.job_result.date_created, datetime_end=self.job_result.date_done, tzinfo=timezone.utc
            )
        return faker.Faker().past_datetime(start_date=self.job_result.date_created, tzinfo=timezone.utc)


class JobResultFactory(BaseModelFactory):
    """JobResult model factory."""

    class Meta:
        model = JobResult

    class Params:
        has_job_model = NautobotBoolIterator(chance_of_getting_true=90)
        has_user = NautobotBoolIterator(chance_of_getting_true=80)
        has_task_args = NautobotBoolIterator(chance_of_getting_true=10)
        has_task_kwargs = NautobotBoolIterator(chance_of_getting_true=90)
        # TODO has_scheduled_job? has_meta? has_celery_kwargs?

    job_model = factory.Maybe("has_job_model", random_instance(Job), None)
    name = factory.Faker("word")
    task_name = factory.Faker("word")
    # date_created and date_done are handled below
    user = factory.Maybe("has_user", random_instance(get_user_model()), None)
    status = factory.Iterator(
        [
            JobResultStatusChoices.STATUS_FAILURE,
            JobResultStatusChoices.STATUS_SUCCESS,
        ],
    )
    worker = factory.LazyAttribute(lambda obj: f"celery@{faker.Faker().hostname()}")
    task_args = factory.Maybe("has_task_args", factory.Faker("pyiterable"), "")
    task_kwargs = factory.Maybe("has_task_kwargs", factory.Faker("pydict"), {})
    # TODO celery_kwargs?
    # TODO meta?

    @factory.lazy_attribute
    def result(self):
        if self.status != JobResultStatusChoices.STATUS_SUCCESS:
            return None
        return faker.Faker().pyobject(faker.Faker().random_element([bool, str, float, int, list, dict]))

    @factory.lazy_attribute
    def traceback(self):
        if self.status == JobResultStatusChoices.STATUS_FAILURE:
            return faker.Faker().paragraph()
        return None

    @factory.post_generation
    def date_created(self, created, extracted, **kwargs):  # pylint: disable=method-hidden
        if created:
            if extracted:
                self.date_created = extracted
            else:
                self.date_created = faker.Faker().date_time_between(
                    start_date="-1y", end_date="now", tzinfo=timezone.utc
                )

    @factory.post_generation
    def date_done(self, created, extracted, **kwargs):  # pylint: disable=method-hidden
        if created:
            if extracted:
                self.date_done = extracted
            else:
                # TODO, should we create "in progress" job results without a date_done value as well?
                self.date_done = self.date_created + timedelta(minutes=faker.Faker().random_int())


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
    changed_object_type = random_instance(change_logged_models_queryset, allow_null=False)
    change_context = factory.Iterator(ObjectChangeEventContextChoices.CHOICES, getter=lambda choice: choice[0])
    change_context_detail = factory.Maybe(
        "has_change_context_detail", factory.Faker("text", max_nb_chars=CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL), ""
    )
    related_object_type = factory.Maybe(
        "has_related_object_type",
        random_instance(change_logged_models_queryset, allow_null=False),
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
    def object_repr(self, created, extracted, **kwargs):  # pylint: disable=method-hidden
        if created:
            if extracted:
                self.object_repr = extracted
            else:
                if self.changed_object is None:
                    self.object_repr = faker.Faker().sentence()[:CHANGELOG_MAX_OBJECT_REPR]

    @factory.post_generation
    def time(self, created, extracted, **kwargs):  # pylint: disable=method-hidden
        if created:
            if extracted:
                self.time = extracted
            else:
                self.time = faker.Faker().date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc)


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
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(get_random_instances(lambda: RoleModelsQuery().as_queryset(), minimum=1))


class StaticGroupFactory(PrimaryModelFactory):
    """StaticGroup model factory."""

    class Meta:
        model = StaticGroup
        exclude = ("color", "has_description", "has_tenant")

    color = UniqueFaker("color_name")
    name = factory.LazyAttribute(
        lambda o: f"{o.color} {bettertitle(o.content_type.model_class()._meta.verbose_name_plural)}"
    )
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))
    hidden = NautobotBoolIterator(chance_of_getting_true=40)

    @factory.post_generation
    def members(self, created, extracted, **kwargs):
        if extracted:
            return
        if not created:
            return
        for member in get_random_instances(self.content_type.model_class().objects.all()):
            StaticGroupAssociationFactory.create(static_group=self, associated_object_id=member.pk)

    @factory.lazy_attribute
    def content_type(self):
        while True:
            content_type = factory.random.randgen.choice(
                ContentType.objects.filter(FeatureQuery("static_groups").get_query())
            )
            if content_type.model_class().objects.exists():
                return content_type


class StaticGroupAssociationFactory(OrganizationalModelFactory):
    """StaticGroupAssociation model factory."""

    class Meta:
        model = StaticGroupAssociation

    static_group = random_instance(StaticGroup, allow_null=False)
    associated_object_type = factory.LazyAttribute(lambda o: o.static_group.content_type)

    @factory.lazy_attribute
    def associated_object_id(self):
        queryset = self.associated_object_type.model_class().objects.all()
        if queryset.exists():
            return factory.random.randgen.choice(queryset).pk
        return faker.Faker().uuid4()


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
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

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
    comments = factory.Maybe("has_comments", factory.Faker("text"), "")

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
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.content_types.set(extracted)
            else:
                self.content_types.set(get_random_instances(lambda: TaggableClassesQuery().as_queryset(), minimum=2))
