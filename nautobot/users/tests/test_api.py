from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.users.models import ObjectPermission
from nautobot.utilities.testing import APIViewTestCases, APITestCase
from nautobot.utilities.utils import deepmerge


# Use the proper swappable User model
User = get_user_model()


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("users-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class UserTest(APIViewTestCases.APIViewTestCase):
    model = User
    view_namespace = "users"
    brief_fields = ["display", "id", "url", "username"]
    validation_excluded_fields = ["password"]
    create_data = [
        {
            "username": "User_4",
            "password": "password4",
        },
        {
            "username": "User_5",
            "password": "password5",
        },
        {
            "username": "User_6",
            "password": "password6",
        },
    ]

    @classmethod
    def setUpTestData(cls):

        User.objects.create(username="User_1")
        User.objects.create(username="User_2")
        User.objects.create(username="User_3")


class GroupTest(APIViewTestCases.APIViewTestCase):
    model = Group
    view_namespace = "users"
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "name": "Group 4",
        },
        {
            "name": "Group 5",
        },
        {
            "name": "Group 6",
        },
    ]

    @classmethod
    def setUpTestData(cls):

        Group.objects.create(name="Group 1")
        Group.objects.create(name="Group 2")
        Group.objects.create(name="Group 3")


class ObjectPermissionTest(APIViewTestCases.APIViewTestCase):
    model = ObjectPermission
    brief_fields = [
        "actions",
        "display",
        "enabled",
        "groups",
        "id",
        "name",
        "object_types",
        "url",
        "users",
    ]

    @classmethod
    def setUpTestData(cls):

        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        users = (
            User.objects.create(username="User 1", is_active=True),
            User.objects.create(username="User 2", is_active=True),
            User.objects.create(username="User 3", is_active=True),
        )

        object_type = ContentType.objects.get(app_label="dcim", model="device")

        for i in range(3):
            objectpermission = ObjectPermission.objects.create(
                name=f"Permission {i+1}",
                actions=["view", "add", "change", "delete"],
                constraints={"name": f"TEST{i+1}"},
            )
            objectpermission.object_types.add(object_type)
            objectpermission.groups.add(groups[i])
            objectpermission.users.add(users[i])

        cls.create_data = [
            {
                "name": "Permission 4",
                "object_types": ["dcim.site"],
                "groups": [groups[0].pk],
                "users": [users[0].pk],
                "actions": ["view", "add", "change", "delete"],
                "constraints": {"name": "TEST4"},
            },
            {
                "name": "Permission 5",
                "object_types": ["dcim.site"],
                "groups": [groups[1].pk],
                "users": [users[1].pk],
                "actions": ["view", "add", "change", "delete"],
                "constraints": {"name": "TEST5"},
            },
            {
                "name": "Permission 6",
                "object_types": ["dcim.site"],
                "groups": [groups[2].pk],
                "users": [users[2].pk],
                "actions": ["view", "add", "change", "delete"],
                "constraints": {"name": "TEST6"},
            },
        ]

        cls.bulk_update_data = {
            "description": "New description",
        }


class UserConfigTest(APITestCase):
    def test_get(self):
        """
        Retrieve user configuration via GET request.
        """
        url = reverse("users-api:userconfig-list")

        response = self.client.get(url, **self.header)
        self.assertEqual(response.data, {})

        data = {
            "a": 123,
            "b": 456,
            "c": 789,
        }
        self.user.config_data = data
        self.user.save()
        response = self.client.get(url, **self.header)
        self.assertEqual(response.data, data)

    def test_patch(self):
        """
        Set user config via PATCH requests.
        """
        url = reverse("users-api:userconfig-list")

        data = {
            "a": {
                "a1": "X",
                "a2": "Y",
            },
            "b": {
                "b1": "Z",
            },
        }
        response = self.client.patch(url, data=data, format="json", **self.header)
        self.assertDictEqual(response.data, data)
        self.user.refresh_from_db()
        self.assertDictEqual(self.user.config_data, data)

        update_data = {"c": 123}
        response = self.client.patch(url, data=update_data, format="json", **self.header)
        new_data = deepmerge(data, update_data)
        self.assertDictEqual(response.data, new_data)
        self.user.refresh_from_db()
        self.assertDictEqual(self.user.config_data, new_data)
