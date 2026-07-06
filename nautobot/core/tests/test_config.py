"""Test cases for nautobot.core.config module."""

from types import SimpleNamespace
from unittest import mock

from constance.test import override_config
from django.core.cache import cache
from django.test import override_settings, tag, TestCase

from nautobot.apps import config as app_config
from nautobot.core.choices import NautobotEditionChoices
from nautobot.core.utils import config
from nautobot.core.utils.cache import construct_cache_key
from nautobot.core.utils.config import get_nautobot_edition


class GetSettingsOrConfigTestCase(TestCase):
    """Test the get_settings_or_config() helper function."""

    @override_settings(BANNER_TOP="Hello, world!")
    def test_settings_if_no_config(self):
        self.assertEqual(config.get_settings_or_config("BANNER_TOP"), "Hello, world!")

    @override_settings(BANNER_TOP="Hello, world!")
    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_settings_override_config(self):
        self.assertEqual(config.get_settings_or_config("BANNER_TOP"), "Hello, world!")

    @override_settings(BANNER_TOP="")
    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_empty_settings_override_config(self):
        self.assertEqual(config.get_settings_or_config("BANNER_TOP"), "")

    @override_settings(BANNER_TOP=None)
    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_null_settings_override_config(self):
        self.assertEqual(config.get_settings_or_config("BANNER_TOP"), None)

    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_config_if_no_setting(self):
        self.assertEqual(config.get_settings_or_config("BANNER_TOP"), "¡Hola, mundo!")

    def test_no_settings_no_config(self):
        self.assertRaises(AttributeError, config.get_settings_or_config, "FAKE_SETTING")


class GetNautobotEditionTestCase(TestCase):
    """Test get_nautobot_edition(), which derives the active edition from the installed apps."""

    def setUp(self):
        cache.delete(construct_cache_key(get_nautobot_edition, branch_aware=False))

    def tearDown(self):
        cache.delete(construct_cache_key(get_nautobot_edition, branch_aware=False))

    @staticmethod
    def _apps_declaring(editions):
        """Patch the app registry with fake app configs declaring the given `nautobot_edition` values."""
        app_configs = [SimpleNamespace(nautobot_edition=edition) for edition in editions]
        return mock.patch("django.apps.apps.get_app_configs", return_value=app_configs)

    def test_defaults_to_community_when_no_app_declares_an_edition(self):
        with self._apps_declaring([None, None]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.COMMUNITY)

    def test_single_app_sets_the_edition(self):
        with self._apps_declaring([None, NautobotEditionChoices.PROFESSIONAL]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.PROFESSIONAL)

    def test_highest_weighted_edition_wins_regardless_of_order(self):
        with self._apps_declaring([NautobotEditionChoices.ENTERPRISE, NautobotEditionChoices.PROFESSIONAL]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)
        cache.delete(construct_cache_key(get_nautobot_edition, branch_aware=False))
        with self._apps_declaring([NautobotEditionChoices.PROFESSIONAL, NautobotEditionChoices.ENTERPRISE]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)

    def test_unrecognized_edition_value_is_ignored(self):
        with self._apps_declaring(["not_a_real_edition", NautobotEditionChoices.PROFESSIONAL]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.PROFESSIONAL)

    def test_result_is_cached(self):
        with self._apps_declaring([NautobotEditionChoices.ENTERPRISE]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)
        # The registry is no longer patched, but the cached value persists (apps don't change at runtime).
        self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)


@tag("example_app")
class GetAppSettingsOrConfigTestCase(TestCase):
    """Test the get_app_settings_or_config() helper function."""

    @override_settings(PLUGINS_CONFIG={"example_app": {"SAMPLE_VARIABLE": "Test Samples"}})
    def test_settings_if_no_config(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "SAMPLE_VARIABLE"), "Test Samples")

    @override_settings(PLUGINS_CONFIG={"example_app": {"lowercase_example": "Test Samples"}})
    def test_settings_if_no_config_lowercase(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "lowercase_example"), "Test Samples")

    @override_settings(PLUGINS_CONFIG={"example_app": {"SAMPLE_VARIABLE": "Test Samples"}})
    @override_config(example_app__SAMPLE_VARIABLE="Testing")
    def test_settings_override_config(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "SAMPLE_VARIABLE"), "Test Samples")

    @override_settings(PLUGINS_CONFIG={"example_app": {"lowercase_example": "Test Samples"}})
    @override_config(example_app__lowercase_example="Testing")
    def test_settings_override_config_lowercase(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "lowercase_example"), "Test Samples")

    @override_settings(PLUGINS_CONFIG={"example_app": {"SAMPLE_VARIABLE": ""}})
    @override_config(example_app__SAMPLE_VARIABLE="Testing")
    def test_empty_settings_override_config(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "SAMPLE_VARIABLE"), "")

    @override_settings(PLUGINS_CONFIG={"example_app": {"lowercase_example": ""}})
    @override_config(example_app__lowercase_example="Testing")
    def test_empty_settings_override_config_lowercase(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "lowercase_example"), "")

    @override_settings(PLUGINS_CONFIG={"example_app": {"SAMPLE_VARIABLE": None}})
    @override_config(example_app__SAMPLE_VARIABLE="Testing")
    def test_null_settings_override_config(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "SAMPLE_VARIABLE"), None)

    @override_settings(PLUGINS_CONFIG={"example_app": {"lowercase_example": None}})
    @override_config(example_app__lowercase_example="Testing")
    def test_null_settings_override_config_lowercase(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "lowercase_example"), None)

    @override_config(example_app__SAMPLE_VARIABLE="Testing")
    def test_config_if_no_setting(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "SAMPLE_VARIABLE"), "Testing")

    @override_config(example_app__lowercase_example="Testing")
    def test_config_if_no_setting_lowercase(self):
        self.assertEqual(app_config.get_app_settings_or_config("example_app", "lowercase_example"), "Testing")

    def test_config_default_value_(self):
        self.assertEqual(
            app_config.get_app_settings_or_config("example_app", "SAMPLE_VARIABLE"), "example_default_value"
        )

    def test_config_default_value_lowercase(self):
        self.assertEqual(
            app_config.get_app_settings_or_config("example_app", "lowercase_example"), "example_lowercase_variable"
        )
