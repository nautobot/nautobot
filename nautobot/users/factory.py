from datetime import timezone

from django.contrib.auth import get_user_model

import factory

from nautobot.core.factory import NautobotBoolIterator, BaseModelFactory


User = get_user_model()


class UserFactory(BaseModelFactory):
    class Meta:
        model = User
        exclude = ("has_first_name", "has_last_name", "has_email")

    has_first_name = NautobotBoolIterator()
    first_name = factory.Maybe("has_first_name", factory.Faker("first_name"), "")

    has_last_name = NautobotBoolIterator()
    last_name = factory.Maybe("has_last_name", factory.Faker("last_name"), "")

    username = factory.Maybe(
        "has_first_name",
        factory.Maybe(
            "has_last_name",
            factory.LazyAttribute(lambda u: f"{u.first_name[0].lower()}{u.last_name.lower()}"),
            factory.LazyAttribute(lambda u: u.first_name.lower()),
        ),
        factory.Maybe(
            "has_last_name",
            factory.LazyAttribute(lambda u: u.last_name.lower()),
            factory.Faker("user_name"),
        ),
    )

    has_email = NautobotBoolIterator()
    email = factory.Maybe("has_email", factory.LazyAttribute(lambda u: f"{u.username}@example.com"), "")

    password = factory.Faker("password")

    is_staff = NautobotBoolIterator()
    is_active = NautobotBoolIterator()
    is_superuser = NautobotBoolIterator()

    last_login = factory.Faker("date_time", tzinfo=timezone.utc)

    # TODO config_data
