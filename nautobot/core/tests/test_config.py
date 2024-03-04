"""Test cases for nautobot.core.config module."""

from constance.test import override_config
from django.test import override_settings, TestCase

from nautobot.apps import config as app_config
from nautobot.core.utils import config


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
