from datetime import timezone

from django.contrib.auth import get_user_model
import factory

from nautobot.core.factory import BaseModelFactory, NautobotBoolIterator

User = get_user_model()


class UserFactory(BaseModelFactory):
    class Meta:
        model = User
        exclude = "has_email"

    first_name = factory.Faker("first_name")

    last_name = factory.Faker("last_name")

    username = factory.LazyAttribute(lambda u: f"{u.first_name[0].lower()}{u.last_name.lower()}")

    has_email = NautobotBoolIterator()
    email = factory.Maybe("has_email", factory.LazyAttribute(lambda u: f"{u.username}@example.com"), "")

    password = factory.Faker("password")

    is_staff = NautobotBoolIterator()
    is_active = NautobotBoolIterator()
    is_superuser = NautobotBoolIterator()

    last_login = factory.Faker("date_time", tzinfo=timezone.utc)

    # TODO config_data
