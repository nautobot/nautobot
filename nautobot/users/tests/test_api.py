import base64
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.users.filters import GroupFilterSet
from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.testing import APIViewTestCases, APITestCase
from nautobot.utilities.utils import deepmerge

from rest_framework import HTTP_HEADER_ENCODING


# Use the proper swappable User model
User = get_user_model()


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("users-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class UserTest(APIViewTestCases.APIViewTestCase):
    model = User
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
    filterset = GroupFilterSet
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

    def _get_detail_url(self, instance):
        """Can't use get_route_for_model because this is not a Nautobot core model."""
        return reverse("users-api:group-detail", kwargs={"pk": instance.pk})

    def _get_list_url(self):
        """Can't use get_route_for_model because this is not a Nautobot core model."""
        return reverse("users-api:group-list")

    @classmethod
    def setUpTestData(cls):

        Group.objects.create(name="Group 1")
        Group.objects.create(name="Group 2")
        Group.objects.create(name="Group 3")


class TokenTest(APIViewTestCases.APIViewTestCase):
    model = Token
    brief_fields = ["display", "id", "key", "url", "write_enabled"]
    bulk_update_data = {
        "description": "New description",
    }

    def setUp(self):
        super().setUp()

        tokens = [
            # We already start with one Token, created by the test class
            Token.objects.create(user=self.user),
            Token.objects.create(user=self.user),
        ]

        self.tokens = tokens + [self.token]

        self.basic_auth_user_password = "abc123"
        self.basic_auth_user_granted = User.objects.create_user(
            username="basicusergranted", password=self.basic_auth_user_password
        )

        obj_perm = ObjectPermission(name="Test permission", actions=["add", "change", "view", "delete"])
        obj_perm.save()
        obj_perm.users.add(self.basic_auth_user_granted)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        self.basic_auth_user_permissionless = User.objects.create_user(
            username="basicuserpermissionless", password=self.basic_auth_user_password
        )

        self.create_data = [
            {
                "description": "token1",
            },
            {
                "description": "token2",
            },
            {
                "description": "token3",
            },
        ]

    def _create_basic_authentication_header(self, username, password):
        """
        Given username, password create a valid Basic authenticaition header string.

        Same procedure used to test DRF.
        """
        credentials = f"{username}:{password}"
        base64_credentials = base64.b64encode(credentials.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)
        return f"Basic {base64_credentials}"

    def test_create_token_basic_authentication(self):
        """
        Test the provisioning of a new REST API token given a valid username and password.
        """
        auth = self._create_basic_authentication_header(
            username=self.basic_auth_user_granted.username, password=self.basic_auth_user_password
        )
        response = self.client.post(self._get_list_url(), HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, 201)
        self.assertIn("key", response.data)
        self.assertEqual(len(response.data["key"]), 40)
        token = Token.objects.get(user=self.basic_auth_user_granted)
        self.assertEqual(token.key, response.data["key"])

    def test_create_token_basic_authentication_permissionless_user(self):
        """
        Test the behavior of the token create view when a user cannot create tokens
        """
        auth = self._create_basic_authentication_header(
            username=self.basic_auth_user_permissionless.username, password=self.basic_auth_user_password
        )
        response = self.client.post(self._get_list_url(), HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, 403)

    def test_create_token_basic_authentication_invalid_password(self):
        """
        Test the behavior of the token create view when an invalid password is supplied
        """
        auth = self._create_basic_authentication_header(
            username=self.basic_auth_user_granted.username, password="hunter2"
        )
        response = self.client.post(self._get_list_url(), HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, 403)

    def test_create_token_basic_authentication_invalid_user(self):
        """
        Test the behavior of the token create view when the user supplied is not a valid user
        """
        auth = self._create_basic_authentication_header(username="iamnotreal", password="P1n0cc#10")
        response = self.client.post(self._get_list_url(), HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, 403)

    def test_create_other_user_token_restriction(self):
        """
        Test to ensure that a user cannot create a token belonging to a different user.
        """
        # List all tokens available to user1
        self.add_permissions("users.add_token")
        self.add_permissions("users.change_token")
        self.add_permissions("users.view_token")
        previous_token_count = len(Token.objects.filter(user=self.basic_auth_user_granted))
        self.client.post(self._get_list_url(), data={"user": self.basic_auth_user_granted.id}, **self.header)
        self.assertEqual(len(Token.objects.filter(user=self.basic_auth_user_granted)), previous_token_count)

    def test_edit_other_user_token_restriction(self):
        """
        Tests to ensure that a user cannot modify tokens belonging to other users.
        """
        other_user_token = Token.objects.create(user=self.basic_auth_user_granted)

        # Check to make sure user1 can't modify another user's token, without permissions
        response = self.client.patch(
            self._get_detail_url(other_user_token), data={"description": "Meep."}, format="json", **self.header
        )
        self.assertEqual(response.status_code, 403)

        self.add_permissions("users.add_token")
        self.add_permissions("users.change_token")
        self.add_permissions("users.view_token")
        # Check to make sure user1 can't modify another user's token, with permissions
        response = self.client.patch(
            self._get_detail_url(other_user_token), data={"description": "Meep."}, format="json", **self.header
        )
        self.assertEqual(response.status_code, 404)

        # Check to make sure user1 can't take over another user's token, with permissions
        previous_token_count = len(Token.objects.filter(user=self.user))
        response = self.client.patch(
            self._get_detail_url(other_user_token), data={"user": self.user.id}, format="json", **self.header
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(Token.objects.filter(user=self.user)), previous_token_count)

        self.user.is_superuser = True
        self.user.save()
        # Check to make sure user1 can't modify another user's token, even as superuser
        response = self.client.patch(
            self._get_detail_url(other_user_token), data={"description": "Meep."}, format="json", **self.header
        )
        self.assertEqual(response.status_code, 404)

        # Check to make sure user1 can't take over another user's token, even as superuser
        previous_token_count = len(Token.objects.filter(user=self.user))
        response = self.client.patch(
            self._get_detail_url(other_user_token), data={"user": self.user.id}, format="json", **self.header
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(Token.objects.filter(user=self.user)), previous_token_count)

    def test_list_tokens_restrictions(self):
        """
        Test that the tokens API can only access tokens belonging to the authenticated user.
        """
        # Create users and tokens
        other_user_token = Token.objects.create(user=self.basic_auth_user_granted)

        # List all tokens available to user1
        self.add_permissions("users.view_token")
        response = self.client.get(self._get_list_url(), **self.header)
        # Assert that only the user1_token appears in the results
        self.assertEqual(len(response.data["results"]), len(self.tokens))

        token_ids_sot = sorted(map(lambda t: str(t.id), self.tokens))
        token_ids_response = sorted(map(lambda t: t["id"], response.data["results"]))

        self.assertEqual(token_ids_sot, token_ids_response)

        # Check to make sure user1 can't search for another user's tokens
        response = self.client.get(self._get_list_url(), data={"id": other_user_token.id}, **self.header)
        self.assertEqual(len(response.data["results"]), 0)

        # Check to make sure user1 can't access another user's tokens
        response = self.client.get(self._get_detail_url(other_user_token), **self.header)
        self.assertEqual(response.status_code, 404)


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
