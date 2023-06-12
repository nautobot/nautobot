import datetime
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import make_aware

from nautobot.core.testing import FilterTestCases
from nautobot.dcim.factory import RackFactory, RackReservationFactory
from nautobot.dcim.models import Location
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import ObjectChange
from nautobot.users.filters import (
    GroupFilterSet,
    ObjectPermissionFilterSet,
    TokenFilterSet,
    UserFilterSet,
)
from nautobot.users.models import ObjectPermission, Token


# Use the proper swappable User model
User = get_user_model()


class UserTestCase(FilterTestCases.FilterTestCase):
    queryset = User.objects.all()
    filterset = UserFilterSet

    generic_filter_tests = (
        ["username"],
        ["first_name"],
        ["last_name"],
        ["email"],
        ["groups_id", "groups__id"],
        ["groups", "groups__name"],
        ["rack_reservations_id", "rack_reservations__id"],
        ["object_changes", "object_changes__id"],
        ["object_permissions", "object_permissions__id"],
        ["object_permissions", "object_permissions__name"],
    )

    @classmethod
    def setUpTestData(cls):
        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        cls.users = (
            User.objects.create(
                username="User1",
                first_name="Hank",
                last_name="Hill",
                email="hank@stricklandpropane.com",
                is_staff=True,
            ),
            User.objects.create(
                username="User2",
                first_name="Dale",
                last_name="Gribble",
                email="dale@dalesdeadbug.com",
            ),
            User.objects.create(
                username="User3",
                first_name="Bill",
                last_name="Dauterive",
                email="bill.dauterive@army.mil",
            ),
            User.objects.create(
                username="User4",
                first_name="Jeff",
                last_name="Boomhauer",
                email="boomhauer@dangolemail.com",
            ),
            User.objects.create(
                username="User5",
                first_name="Debbie",
                last_name="Grund",
                is_active=False,
            ),
        )

        cls.users[0].groups.set([groups[0]])
        cls.users[1].groups.set([groups[1]])
        cls.users[2].groups.set([groups[2]])

        location = Location.objects.first()
        cls.object_changes = [
            ObjectChange.objects.create(
                user=cls.users[num],
                user_name=cls.users[num].username,
                request_id=uuid.uuid4(),
                action=ObjectChangeActionChoices.ACTION_CREATE,
                changed_object=location,
                object_repr=str(location),
                object_data={"name": location.name},
            )
            for num in range(3)
        ]

        cls.permissions = [
            ObjectPermission.objects.create(name=f"Permission {num}", actions=["change"], enabled=False)
            for num in range(3)
        ]
        cls.permissions[0].users.add(cls.users[0])
        cls.permissions[1].users.add(cls.users[1])

        RackFactory.create_batch(10)
        RackReservationFactory.create_batch(5)

    def test_is_staff(self):
        params = {"is_staff": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_is_active(self):
        params = {"is_active": True}
        # 4 created active users in setUpTestData, plus one created active user in TestCase.setUp
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class GroupTestCase(FilterTestCases.FilterTestCase):
    queryset = Group.objects.all()
    filterset = GroupFilterSet

    @classmethod
    def setUpTestData(cls):
        Group.objects.create(name="Group 1")
        Group.objects.create(name="Group 2")
        Group.objects.create(name="Group 3")

    def test_name(self):
        params = {"name": ["Group 1", "Group 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class ObjectPermissionTestCase(FilterTestCases.FilterTestCase):
    queryset = ObjectPermission.objects.all()
    filterset = ObjectPermissionFilterSet

    generic_filter_tests = (
        ["users", "users__id"],
        ["users", "users__username"],
        ["groups_id", "groups__id"],
        ["groups", "groups__name"],
        ["description"],
        ["name"],
    )

    @classmethod
    def setUpTestData(cls):
        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        users = (
            User.objects.create(username="User1"),
            User.objects.create(username="User2"),
            User.objects.create(username="User3"),
        )

        object_types = (
            ContentType.objects.get(app_label="dcim", model="location"),
            ContentType.objects.get(app_label="dcim", model="rack"),
            ContentType.objects.get(app_label="dcim", model="device"),
        )

        permissions = (
            ObjectPermission.objects.create(
                name="Permission 1", actions=["view", "add", "change", "delete"], description="Description 1"
            ),
            ObjectPermission.objects.create(
                name="Permission 2", actions=["view", "add", "change", "delete"], description="Description 2"
            ),
            ObjectPermission.objects.create(name="Permission 3", actions=["view", "add", "change", "delete"]),
            ObjectPermission.objects.create(name="Permission 4", actions=["view"], enabled=False),
            ObjectPermission.objects.create(name="Permission 5", actions=["add"], enabled=False),
            ObjectPermission.objects.create(name="Permission 6", actions=["change"], enabled=False),
            ObjectPermission.objects.create(name="Permission 7", actions=["delete"], enabled=False),
        )
        for i in range(0, 3):
            permissions[i].groups.set([groups[i]])
            permissions[i].users.set([users[i]])
            permissions[i].object_types.set([object_types[i]])

    def test_enabled(self):
        params = {"enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_object_types(self):
        object_types = ContentType.objects.filter(model__in=["location", "rack"])
        params = {"object_types": [object_types[0].pk, object_types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class TokenTestCase(FilterTestCases.FilterTestCase):
    queryset = Token.objects.all()
    filterset = TokenFilterSet

    generic_filter_tests = (
        ["description"],
        ["key"],
    )

    @classmethod
    def setUpTestData(cls):
        users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
        )
        User.objects.bulk_create(users)

        future_date = make_aware(datetime.datetime(3000, 1, 1))
        past_date = make_aware(datetime.datetime(2000, 1, 1))
        tokens = (
            Token(
                user=users[0],
                key=Token.generate_key(),
                expires=future_date,
                write_enabled=True,
                description="Description 1",
            ),
            Token(
                user=users[1],
                key=Token.generate_key(),
                expires=future_date,
                write_enabled=True,
                description="Description 2",
            ),
            Token(user=users[2], key=Token.generate_key(), expires=past_date, write_enabled=False),
        )
        Token.objects.bulk_create(tokens)

    def test_expires(self):
        params = {"expires": ["3000-01-01 00:00:00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"expires__gte": ["2021-01-01 00:00:00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"expires__lte": ["2021-01-01 00:00:00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_write_enabled(self):
        params = {"write_enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"write_enabled": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)
