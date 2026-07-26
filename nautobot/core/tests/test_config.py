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


class TemplateExposableSettingsTestCase(TestCase):
    """Test the settings allowlisting used at the template boundaries (GHSA-6jmc-h6f2-46j4)."""

    def test_constance_config_keys_are_exposable(self):
        self.assertTrue(config.is_template_exposable_setting("BANNER_TOP"))
        self.assertTrue(config.is_template_exposable_setting("PAGINATE_COUNT"))

    def test_allowlisted_settings_are_exposable(self):
        self.assertTrue(config.is_template_exposable_setting("VERSION"))
        self.assertTrue(config.is_template_exposable_setting("BRANDING_TITLE"))

    def test_settings_read_via_filter_from_python_are_exposable(self):
        """Non-Constance settings that nautobot itself reads through the settings_or_config filter (e.g. from
        nautobot.extras.jobs_ui) must be allowlisted so those reads don't raise."""
        self.assertTrue(config.is_template_exposable_setting("CELERY_TASK_SOFT_TIME_LIMIT"))
        self.assertTrue(config.is_template_exposable_setting("CELERY_TASK_TIME_LIMIT"))

    def test_secrets_are_not_exposable(self):
        for name in ("SECRET_KEY", "DATABASES", "CELERY_BROKER_URL", "FAKE_SETTING"):
            with self.subTest(name=name):
                self.assertFalse(config.is_template_exposable_setting(name))

    @override_settings(VERSION="1.2.3")
    def test_exposed_settings_proxy(self):
        proxy = config.ExposedSettings()
        # Allowlisted settings are readable through the proxy.
        self.assertEqual(proxy.VERSION, "1.2.3")
        # Non-allowlisted settings raise AttributeError (rendered as empty by the template engines).
        with self.assertRaises(AttributeError):
            _ = proxy.SECRET_KEY

    def test_settings_context_processor_uses_proxy(self):
        """The template `settings` context must be the allowlisting proxy, not the raw settings module."""
        from nautobot.core.context_processors import settings as settings_context_processor

        self.assertIsInstance(settings_context_processor(None)["settings"], config.ExposedSettings)


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
