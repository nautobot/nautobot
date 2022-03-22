"""Test cases for nautobot.utilities.config module."""

from constance.test import override_config
from django.test import TestCase, override_settings

from nautobot.utilities.config import get_settings_or_config


class GetSettingsOrConfigTestCase(TestCase):
    """Test the get_settings_or_config() helper function."""

    @override_settings(BANNER_TOP="Hello, world!")
    def test_settings_if_no_config(self):
        self.assertEqual(get_settings_or_config("BANNER_TOP"), "Hello, world!")

    @override_settings(BANNER_TOP="Hello, world!")
    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_settings_override_config(self):
        self.assertEqual(get_settings_or_config("BANNER_TOP"), "Hello, world!")

    @override_settings(BANNER_TOP="")
    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_empty_settings_override_config(self):
        self.assertEqual(get_settings_or_config("BANNER_TOP"), "")

    @override_settings(BANNER_TOP=None)
    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_null_settings_override_config(self):
        self.assertEqual(get_settings_or_config("BANNER_TOP"), None)

    @override_config(BANNER_TOP="¡Hola, mundo!")
    def test_config_if_no_setting(self):
        self.assertEqual(get_settings_or_config("BANNER_TOP"), "¡Hola, mundo!")

    def test_no_settings_no_config(self):
        self.assertRaises(AttributeError, get_settings_or_config, "FAKE_SETTING")
