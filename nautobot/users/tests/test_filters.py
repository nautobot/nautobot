import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import make_aware

from nautobot.users.filters import (
    GroupFilterSet,
    ObjectPermissionFilterSet,
    TokenFilterSet,
    UserFilterSet,
)
from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.testing import FilterTestCases


# Use the proper swappable User model
User = get_user_model()


class UserTestCase(FilterTestCases.FilterTestCase):
    queryset = User.objects.all()
    filterset = UserFilterSet

    @classmethod
    def setUpTestData(cls):
        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        users = (
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

        users[0].groups.set([groups[0]])
        users[1].groups.set([groups[1]])
        users[2].groups.set([groups[2]])

    def test_username(self):
        params = {"username": ["User1", "User2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_first_name(self):
        params = {"first_name": ["Hank", "Dale"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_last_name(self):
        params = {"last_name": ["Hill", "Gribble"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_email(self):
        params = {"email": ["hank@stricklandpropane.com", "dale@dalesdeadbug.com"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_is_staff(self):
        params = {"is_staff": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_is_active(self):
        params = {"is_active": True}
        # 4 created active users in setUpTestData, plus one created active user in TestCase.setUp
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_group(self):
        groups = list(Group.objects.all()[:2])
        filter_params = [
            {"group_id": [groups[0].pk, groups[1].pk]},
            {"group": [groups[0].name, groups[1].name]},
        ]

        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs.order_by("id"),
                self.queryset.filter(groups__in=groups).order_by("id"),
            )

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
            ContentType.objects.get(app_label="dcim", model="site"),
            ContentType.objects.get(app_label="dcim", model="rack"),
            ContentType.objects.get(app_label="dcim", model="device"),
        )

        permissions = (
            ObjectPermission.objects.create(name="Permission 1", actions=["view", "add", "change", "delete"]),
            ObjectPermission.objects.create(name="Permission 2", actions=["view", "add", "change", "delete"]),
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

    def test_name(self):
        params = {"name": ["Permission 1", "Permission 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_enabled(self):
        params = {"enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_group(self):
        groups = list(Group.objects.filter(name__in=["Group 1", "Group 2"])[:2])
        filter_params = [{"group_id": [groups[0].pk, groups[1].pk]}, {"group": [groups[0].name, groups[1].name]}]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(groups__in=groups).distinct()
            )

    def test_user(self):
        users = list(User.objects.filter(username__in=["User1", "User2"])[:2])
        filter_params = [{"user_id": [users[0].pk, users[1].pk]}, {"user": [users[0].pk, users[1].username]}]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(users__in=users)
            )

    def test_object_types(self):
        object_types = ContentType.objects.filter(model__in=["site", "rack"])
        params = {"object_types": [object_types[0].pk, object_types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class TokenTestCase(FilterTestCases.FilterTestCase):
    queryset = Token.objects.all()
    filterset = TokenFilterSet

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
            Token(user=users[0], key=Token.generate_key(), expires=future_date, write_enabled=True),
            Token(user=users[1], key=Token.generate_key(), expires=future_date, write_enabled=True),
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

    def test_key(self):
        tokens = Token.objects.all()[:2]
        params = {"key": [tokens[0].key, tokens[1].key]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_write_enabled(self):
        params = {"write_enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"write_enabled": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)
