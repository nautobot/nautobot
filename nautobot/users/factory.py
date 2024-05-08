from datetime import timezone

from django.contrib.auth import get_user_model
import factory

from nautobot.core.factory import BaseModelFactory, NautobotBoolIterator, random_instance, UniqueFaker
from nautobot.extras.utils import FeatureQuery
from nautobot.users.models import SavedView

User = get_user_model()

VIEW_NAMES = []
for choice in FeatureQuery("saved_views").get_choices():
    app_label, model = choice[0].split(".")
    # Relevant list view name only
    if app_label in ["circuits", "dcim", "ipam", "extras", "tenancy", "virtualization"]:
        VIEW_NAMES.append(f"{app_label}:{model}_list")


class UserFactory(BaseModelFactory):
    class Meta:
        model = User
        exclude = "has_email"

    first_name = UniqueFaker("first_name")

    last_name = UniqueFaker("last_name")

    username = factory.LazyAttribute(lambda u: f"{u.first_name[0].lower()}{u.last_name.lower()}")

    has_email = NautobotBoolIterator()
    email = factory.Maybe("has_email", factory.LazyAttribute(lambda u: f"{u.username}@example.com"), "")

    password = factory.Faker("password")

    is_staff = NautobotBoolIterator()
    is_active = NautobotBoolIterator()
    is_superuser = NautobotBoolIterator()

    last_login = factory.Faker("date_time", tzinfo=timezone.utc)

    # TODO config_data


class SavedViewFactory(BaseModelFactory):
    class Meta:
        model = SavedView

    name = factory.LazyAttributeSequence(lambda o, n: f"Sample {o.view} Saved View - {n + 1}")
    owner = random_instance(User, allow_null=False)
    view = factory.Faker(
        "random_element",
        elements=VIEW_NAMES,
    )
    # TODO config attribute
