from datetime import timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
import factory

from nautobot.core.factory import BaseModelFactory, NautobotBoolIterator, random_instance, UniqueFaker
from nautobot.users.models import SavedView

User = get_user_model()


def populate_saved_view_view_name():
    from nautobot.extras.utils import FeatureQuery

    VIEW_NAMES = []
    # Append all saved view supported view names
    for choice in FeatureQuery("saved_views").get_choices():
        app_label, model = choice[0].split(".")
        # Relevant list view name only
        if app_label in ["circuits", "dcim", "ipam", "extras", "tenancy", "virtualization"]:
            list_view_name = f"{app_label}:{model}_list"
            # make sure that list view exists
            reverse(list_view_name)
            VIEW_NAMES.append(list_view_name)

    return VIEW_NAMES


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
        elements=populate_saved_view_view_name(),
    )
    config = factory.Faker("pydict")
