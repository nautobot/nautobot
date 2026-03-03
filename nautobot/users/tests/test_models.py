from datetime import date, timedelta
from unittest import mock

from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse

from nautobot.core.testing import TestCase
from nautobot.core.testing.models import ModelTestCases
from nautobot.users.models import LogEntry, ObjectPermission, Token

# Use the proper swappable User model
User = get_user_model()


class ObjectPermissionTest(ModelTestCases.BaseModelTestCase):
    model = ObjectPermission

    def setUp(self):
        ObjectPermission.objects.create(name="Test Permission", actions=["view", "add", "change", "delete"])


class TokenTest(ModelTestCases.BaseModelTestCase):
    model = Token

    def setUp(self):
        user = User.objects.create_user(username="testuser")
        self.token = Token.objects.create(user=user)

    def test_natural_key_does_not_expose_token_key(self):
        self.assertNotEqual(self.token.key, "")
        self.assertNotIn(self.token.key, self.token.natural_key())


class LogEntryTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="logentry-user")
        self.content_type = ContentType.objects.get_for_model(User)
        self.logentry = LogEntry.objects.create(
            user=self.user,
            content_type=self.content_type,
            object_id=str(self.user.pk),
            object_repr=self.user.username,
            action_flag=ADDITION,
            change_message="Created user",
        )

    def test_get_absolute_url(self):
        self.assertEqual(self.logentry.get_absolute_url(), reverse("user:logentry", kwargs={"pk": self.logentry.pk}))

    def test_get_absolute_url_api_unsupported(self):
        with self.assertRaisesRegex(AttributeError, "No API URL route exists"):
            self.logentry.get_absolute_url(api=True)

    def test_get_action_flag_class(self):
        expected = {
            ADDITION: "success",
            CHANGE: "warning",
            DELETION: "danger",
        }
        for action_flag, css_class in expected.items():
            self.logentry.action_flag = action_flag
            self.assertEqual(self.logentry.get_action_flag_class(), css_class)

        self.logentry.action_flag = 999
        self.assertEqual(self.logentry.get_action_flag_class(), "secondary")

    def test_created_and_last_updated_aliases(self):
        self.assertEqual(self.logentry.created, self.logentry.action_time)
        self.assertEqual(self.logentry.last_updated, self.logentry.action_time)


class UserConfigTest(ModelTestCases.BaseModelTestCase):
    model = User

    def setUp(self):
        user = User.objects.create_user(username="testuser")
        user.config_data = {
            "a": True,
            "b": {
                "foo": 101,
                "bar": 102,
            },
            "c": {
                "foo": {
                    "x": 201,
                },
                "bar": {
                    "y": 202,
                },
                "baz": {
                    "z": 203,
                },
            },
        }
        user.save()

        self.user = user

    def test_get(self):
        # Retrieve root and nested values
        self.assertEqual(self.user.get_config("a"), True)
        self.assertEqual(self.user.get_config("b.foo"), 101)
        self.assertEqual(self.user.get_config("c.baz.z"), 203)

        # Invalid values should return None
        self.assertIsNone(self.user.get_config("invalid"))
        self.assertIsNone(self.user.get_config("a.invalid"))
        self.assertIsNone(self.user.get_config("b.foo.invalid"))
        self.assertIsNone(self.user.get_config("b.foo.x.invalid"))

        # Invalid values with a provided default should return the default
        self.assertEqual(self.user.get_config("invalid", "DEFAULT"), "DEFAULT")
        self.assertEqual(self.user.get_config("a.invalid", "DEFAULT"), "DEFAULT")
        self.assertEqual(self.user.get_config("b.foo.invalid", "DEFAULT"), "DEFAULT")
        self.assertEqual(self.user.get_config("b.foo.x.invalid", "DEFAULT"), "DEFAULT")

    def test_all(self):
        flattened_data = {
            "a": True,
            "b.foo": 101,
            "b.bar": 102,
            "c.foo.x": 201,
            "c.bar.y": 202,
            "c.baz.z": 203,
        }

        # Retrieve a flattened dictionary containing all config data
        self.assertEqual(self.user.all_config(), flattened_data)

    def test_set(self):
        # Overwrite existing values
        self.user.set_config("a", "abc")
        self.user.set_config("c.foo.x", "abc")
        self.assertEqual(self.user.config_data["a"], "abc")
        self.assertEqual(self.user.config_data["c"]["foo"]["x"], "abc")

        # Create new values
        self.user.set_config("d", "abc")
        self.user.set_config("b.baz", "abc")
        self.assertEqual(self.user.config_data["d"], "abc")
        self.assertEqual(self.user.config_data["b"]["baz"], "abc")

        # Set a value and commit to the database
        self.user.set_config("a", "def", commit=True)

        self.user.refresh_from_db()
        self.assertEqual(self.user.config_data["a"], "def")

        # Attempt to change a branch node to a leaf node
        with self.assertRaises(TypeError):
            self.user.set_config("b", 1)

        # Attempt to change a leaf node to a branch node
        with self.assertRaises(TypeError):
            self.user.set_config("a.x", 1)

    def test_clear(self):
        # Clear existing values
        self.user.clear_config("a")
        self.user.clear_config("b.foo")
        self.assertTrue("a" not in self.user.config_data)
        self.assertTrue("foo" not in self.user.config_data["b"])
        self.assertEqual(self.user.config_data["b"]["bar"], 102)

        # Clear a non-existing value; should fail silently
        self.user.clear_config("invalid")


@override_settings(PLUGINS=["nautobot_version_control"])
class UserHasPermTest(ModelTestCases.BaseModelTestCase):
    model = User

    def setUp(self):
        self.user = User.objects.create_user(username="testuser")
        self.add_permissions("dcim.add_device", "dcim.view_device")

    @mock.patch("django.contrib.auth.models.AbstractUser.has_perm")
    def test_time_travel_blocks_non_view_permission(self, mock_super_has_perm):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.utils import get_time_travel_datetime  # pylint: disable=import-error

            get_time_travel_datetime.return_value = (date.today() + timedelta(days=1)).isoformat()

            perm = "dcim.add_device"
            result = self.user.has_perm(perm)
            self.assertFalse(result)
            mock_super_has_perm.assert_not_called()

    @mock.patch("django.contrib.auth.models.AbstractUser.has_perm")
    def test_time_travel_blocks_non_view_permission_for_superuser(self, mock_super_has_perm):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.utils import get_time_travel_datetime  # pylint: disable=import-error

            get_time_travel_datetime.return_value = date.today() + timedelta(days=1)
            perm = "dcim.add_device"
            self.user.is_superuser = True
            self.user.save()

            self.assertTrue(self.user.is_superuser)

            result = self.user.has_perm(perm)
            self.assertFalse(result)
            mock_super_has_perm.assert_not_called()

    @mock.patch("django.contrib.auth.models.AbstractUser.has_perm")
    def test_time_travel_allows_view_permission(self, mock_super_has_perm):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.utils import get_time_travel_datetime  # pylint: disable=import-error

            get_time_travel_datetime.return_value = date.today() + timedelta(days=1)
            perm = "dcim.view_device"
            result = self.user.has_perm(perm)
            self.assertTrue(result)
            mock_super_has_perm.assert_called_once_with(perm, None)

    @mock.patch("django.contrib.auth.models.AbstractUser.has_perm")
    def test_no_time_travel_does_not_block_permissions(self, mock_super_has_perm):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.utils import get_time_travel_datetime  # pylint: disable=import-error

            get_time_travel_datetime.return_value = None
            perm = "dcim.add_device"
            result = self.user.has_perm(perm)
            self.assertTrue(result)
            mock_super_has_perm.assert_called_once_with(perm, None)
