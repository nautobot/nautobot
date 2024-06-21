from django.contrib.auth import get_user_model

from nautobot.core.testing.models import ModelTestCases
from nautobot.users.models import ObjectPermission, SavedView, Token

# Use the proper swappable User model
User = get_user_model()


class ObjectPermissionTest(ModelTestCases.BaseModelTestCase):
    model = ObjectPermission

    def setUp(self):
        ObjectPermission.objects.create(name="Test Permission", actions=["view", "add", "change", "delete"])


class SavedViewTest(ModelTestCases.BaseModelTestCase):
    model = SavedView

    def setUp(self):
        self.user = User.objects.create_user(username="Saved View test user")
        self.sv = SavedView.objects.create(name="Saved View", owner=self.user, view="dcim:location_list")

    def test_is_global_default_saved_view_is_shared_automatically(self):
        self.sv.is_global_default = True
        self.sv.save()
        self.assertEqual(self.sv.is_shared, True)

    def test_setting_new_global_default_saved_view_unset_old_global_default_saved_view(self):
        self.old_global_sv = SavedView.objects.create(
            name="Old Global Saved View", owner=self.user, view="dcim:location_list", is_global_default=True
        )

        self.new_global_sv = SavedView.objects.create(
            name="New Global Saved View", owner=self.user, view="dcim:location_list"
        )
        self.new_global_sv.is_global_default = True
        self.new_global_sv.save()
        self.old_global_sv.refresh_from_db()
        self.assertEqual(self.new_global_sv.is_shared, True)
        self.assertEqual(self.old_global_sv.is_global_default, False)

    def test_multiple_global_default_saved_views_can_exist_for_different_views(self):
        self.device_global_sv = SavedView.objects.create(
            name="Device Global Saved View", owner=self.user, view="dcim:device_list", is_global_default=True
        )
        self.device_global_sv.save()
        self.location_global_sv = SavedView.objects.create(
            name="Location Global Saved View", owner=self.user, view="dcim:location_list", is_global_default=True
        )
        self.location_global_sv.save()
        self.ipaddress_global_sv = SavedView.objects.create(
            name="IP Address Global Saved View", owner=self.user, view="ipam:ipaddress_list", is_global_default=True
        )
        self.ipaddress_global_sv.save()
        self.assertEqual(self.device_global_sv.is_shared, True)
        self.assertEqual(self.location_global_sv.is_shared, True)
        self.assertEqual(self.ipaddress_global_sv.is_shared, True)


class TokenTest(ModelTestCases.BaseModelTestCase):
    model = Token

    def setUp(self):
        user = User.objects.create_user(username="testuser")
        self.token = Token.objects.create(user=user)

    def test_natural_key_does_not_expose_token_key(self):
        self.assertNotEqual(self.token.key, "")
        self.assertNotIn(self.token.key, self.token.natural_key())


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
