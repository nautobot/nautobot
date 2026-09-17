"""Test cases for nautobot.core.config module."""

from types import SimpleNamespace
from unittest import mock

from constance.test import override_config
from django.test import override_settings, tag, TestCase

from nautobot.apps import config as app_config
from nautobot.core.choices import NautobotEditionChoices
from nautobot.core.utils import config
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
        get_nautobot_edition.cache_clear()

    def tearDown(self):
        get_nautobot_edition.cache_clear()

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
        get_nautobot_edition.cache_clear()
        with self._apps_declaring([NautobotEditionChoices.PROFESSIONAL, NautobotEditionChoices.ENTERPRISE]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)

    def test_unrecognized_edition_value_is_ignored(self):
        with self._apps_declaring(["not_a_real_edition", NautobotEditionChoices.PROFESSIONAL]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.PROFESSIONAL)

    def test_app_declaring_cloud_outweighs_other_editions(self):
        with self._apps_declaring([NautobotEditionChoices.ENTERPRISE, NautobotEditionChoices.CLOUD]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.CLOUD)

    def test_result_is_cached(self):
        with self._apps_declaring([NautobotEditionChoices.ENTERPRISE]):
            self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)
        # The registry is no longer patched, but the cached value persists (apps don't change at runtime).
        self.assertEqual(get_nautobot_edition(), NautobotEditionChoices.ENTERPRISE)


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
