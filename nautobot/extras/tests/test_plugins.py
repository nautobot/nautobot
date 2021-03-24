from unittest import skipIf

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from nautobot.dcim.models import Site
from nautobot.extras.jobs import get_job, get_job_classpaths, get_jobs
from nautobot.extras.plugins.exceptions import PluginImproperlyConfigured
from nautobot.extras.plugins.utils import load_plugin
from nautobot.extras.plugins.validators import wrap_model_clean_methods
from nautobot.extras.registry import registry, DatasourceContent
from nautobot.extras.tests.dummy_plugin import config as dummy_config
from nautobot.extras.tests.dummy_plugin.datasources import refresh_git_text_files
from nautobot.utilities.testing import APITestCase


@skipIf(
    "nautobot.extras.tests.dummy_plugin" not in settings.PLUGINS,
    "dummy_plugin not in settings.PLUGINS",
)
class PluginTest(TestCase):
    def test_config(self):

        self.assertIn(
            "nautobot.extras.tests.dummy_plugin.DummyPluginConfig",
            settings.INSTALLED_APPS,
        )

    def test_models(self):
        from nautobot.extras.tests.dummy_plugin.models import DummyModel

        # Test saving an instance
        instance = DummyModel(name="Instance 1", number=100)
        instance.save()
        self.assertIsNotNone(instance.pk)

        # Test deleting an instance
        instance.delete()
        self.assertIsNone(instance.pk)

    def test_admin(self):

        # Test admin view URL resolution
        url = reverse("admin:dummy_plugin_dummymodel_add")
        self.assertEqual(url, "/admin/dummy_plugin/dummymodel/add/")

    def test_views(self):

        # Test URL resolution
        url = reverse("plugins:dummy_plugin:dummy_models")
        self.assertEqual(url, "/plugins/dummy-plugin/models/")

        # Test GET request
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_menu_items(self):
        """
        Check that plugin MenuItems and MenuButtons are registered.
        """
        self.assertIn("Dummy plugin", registry["plugin_menu_items"])
        menu_items = registry["plugin_menu_items"]["Dummy plugin"]
        self.assertEqual(len(menu_items), 2)
        self.assertEqual(len(menu_items[0].buttons), 2)

    def test_template_extensions(self):
        """
        Check that plugin TemplateExtensions are registered.
        """
        from nautobot.extras.tests.dummy_plugin.template_content import SiteContent

        self.assertIn(SiteContent, registry["plugin_template_extensions"]["dcim.site"])

    def test_custom_validators_registration(self):
        """
        Check that plugin custom validators are registered correctly.
        """
        from nautobot.extras.tests.dummy_plugin.custom_validators import (
            SiteCustomValidator,
        )

        self.assertIn(SiteCustomValidator, registry["plugin_custom_validators"]["dcim.site"])

    def test_graphql_types(self):
        """
        Check that plugin GraphQL Types are registered.
        """
        from nautobot.extras.tests.dummy_plugin.graphql.types import AnotherDummyType

        self.assertIn(AnotherDummyType, registry["plugin_graphql_types"])

    def test_extras_features_graphql(self):
        """
        Check that plugin GraphQL Types are registered.
        """
        registered_models = registry.get("model_features", {}).get("graphql", {})

        self.assertIn("dummy_plugin", registered_models.keys())
        self.assertIn("dummymodel", registered_models["dummy_plugin"])

    def test_jobs_registration(self):
        """
        Check that plugin jobs are registered correctly and discoverable.
        """
        from nautobot.extras.tests.dummy_plugin.jobs import DummyJob

        self.assertIn(DummyJob, registry.get("plugin_jobs", []))

        self.assertEqual(
            DummyJob,
            get_job("plugins/nautobot.extras.tests.dummy_plugin.jobs/DummyJob"),
        )
        self.assertIn(
            "plugins/nautobot.extras.tests.dummy_plugin.jobs/DummyJob",
            get_job_classpaths(),
        )
        jobs_dict = get_jobs()
        self.assertIn("plugins", jobs_dict)
        self.assertIn("nautobot.extras.tests.dummy_plugin.jobs", jobs_dict["plugins"])
        self.assertEqual(
            "DummyPlugin jobs",
            jobs_dict["plugins"]["nautobot.extras.tests.dummy_plugin.jobs"].get("name"),
        )
        self.assertIn("jobs", jobs_dict["plugins"]["nautobot.extras.tests.dummy_plugin.jobs"])
        self.assertIn(
            "DummyJob",
            jobs_dict["plugins"]["nautobot.extras.tests.dummy_plugin.jobs"]["jobs"],
        )
        self.assertEqual(
            DummyJob,
            jobs_dict["plugins"]["nautobot.extras.tests.dummy_plugin.jobs"]["jobs"]["DummyJob"],
        )

    def test_git_datasource_contents(self):
        """
        Check that plugin DatasourceContents are registered.
        """
        registered_datasources = registry.get("datasource_contents", {}).get("extras.gitrepository", [])

        self.assertIn(
            DatasourceContent(
                name="text files",
                content_identifier="dummy_plugin.textfile",
                icon="mdi-note-text",
                callback=refresh_git_text_files,
            ),
            registered_datasources,
        )

    def test_middleware(self):
        """
        Check that plugin middleware is registered.
        """
        self.assertIn(
            "nautobot.extras.tests.dummy_plugin.middleware.DummyMiddleware",
            settings.MIDDLEWARE,
        )

        # Establish dummy config to have invalid middleware (tuple)
        class DummyConfigWithMiddleware(dummy_config):
            middleware = ()

        # Validation should fail when a middleware is not a list
        with self.assertRaises(PluginImproperlyConfigured):
            DummyConfigWithMiddleware.validate({}, settings.VERSION)

    def test_caching_config(self):
        """
        Check that plugin caching configuration is registered and valid.
        """
        self.assertIn("nautobot.extras.tests.dummy_plugin.*", settings.CACHEOPS)

        # Establish dummy config to have invalid cache_config (list)
        class DummyConfigWithBadCacheConfig(dummy_config):
            caching_config = []

        # Validation should fail when a caching_config is not a dict
        with self.assertRaises(PluginImproperlyConfigured):
            DummyConfigWithBadCacheConfig.validate({}, settings.VERSION)

    def test_min_version(self):
        """
        Check enforcement of minimum Nautobot version.
        """
        with self.assertRaises(PluginImproperlyConfigured):
            dummy_config.validate({}, "0.8")

    def test_max_version(self):
        """
        Check enforcement of maximum Nautobot version.
        """
        with self.assertRaises(PluginImproperlyConfigured):
            dummy_config.validate({}, "10.0")

    def test_required_settings(self):
        """
        Validate enforcement of required settings.
        """

        class DummyConfigWithRequiredSettings(dummy_config):
            required_settings = ["foo"]

        # Validation should pass when all required settings are present
        DummyConfigWithRequiredSettings.validate({"foo": True}, settings.VERSION)

        # Validation should fail when a required setting is missing
        with self.assertRaises(PluginImproperlyConfigured):
            DummyConfigWithRequiredSettings.validate({}, settings.VERSION)

        # Overload dummy config to have invalid required_settings (dict) and
        # assert that it should fail validation.
        DummyConfigWithRequiredSettings.required_settings = {"foo": "bar"}
        with self.assertRaises(PluginImproperlyConfigured):
            DummyConfigWithRequiredSettings.validate({}, settings.VERSION)

    def test_default_settings(self):
        """
        Validate population of default config settings.
        """

        class DummyConfigWithDefaultSettings(dummy_config):
            default_settings = {
                "bar": 123,
            }

        # Populate the default value if setting has not been specified
        user_config = {}
        DummyConfigWithDefaultSettings.validate(user_config, settings.VERSION)
        self.assertEqual(user_config["bar"], 123)

        # Don't overwrite specified values
        user_config = {"bar": 456}
        DummyConfigWithDefaultSettings.validate(user_config, settings.VERSION)
        self.assertEqual(user_config["bar"], 456)

        # Overload dummy config to have invalid default_settings (list) and
        # assert that it should fail validation.
        DummyConfigWithDefaultSettings.required_settings = ["foo"]
        with self.assertRaises(PluginImproperlyConfigured):
            DummyConfigWithDefaultSettings.validate({}, settings.VERSION)

    def test_installed_apps(self):
        """
        Validate that plugin installed apps and dependencies are are registerd.
        """
        self.assertIn(
            "nautobot.extras.tests.dummy_plugin.DummyPluginConfig",
            settings.INSTALLED_APPS,
        )
        self.assertIn("nautobot.extras.tests.dummy_plugin_dependency", settings.INSTALLED_APPS)

        # Establish dummy config to have invalid installed_apps (tuple)
        class DummyConfigWithInstalledApps(dummy_config):
            installed_apps = ("foo", "bar")

        # Validation should fail when a installed_apps is not a list
        with self.assertRaises(PluginImproperlyConfigured):
            DummyConfigWithInstalledApps.validate({}, settings.VERSION)


@skipIf(
    "nautobot.extras.tests.dummy_plugin" not in settings.PLUGINS,
    "dummy_plugin not in settings.PLUGINS",
)
class PluginAPITestCase(APITestCase):
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_api_views(self):

        # Test URL resolution
        url = reverse("plugins-api:dummy_plugin-api:dummymodel-list")
        self.assertEqual(url, "/api/plugins/dummy-plugin/dummy-models/")

        # Test GET request
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)


@skipIf(
    "nautobot.extras.tests.dummy_plugin" not in settings.PLUGINS,
    "dummy_plugin not in settings.PLUGINS",
)
class PluginCustomValidationTest(TestCase):
    def setUp(self):
        # When creating a fresh test DB, wrapping model clean methods fails, which is normal.
        # This always occurs during the first run of migrations, however, During testing we
        # must manually call the method again to actually perform the action, now that the
        # ContentType table has been created.
        wrap_model_clean_methods()

    def test_custom_validator_raises_exception(self):

        site = Site(name="this site has a matching name", slug="site1")

        with self.assertRaises(ValidationError):
            site.clean()


class LoadPluginTest(TestCase):
    """
    Validate that plugin helpers work as intended.

    Only `load_plugin` is tested, because that is called once for each plugin by
    `load_plugins`.
    """

    def test_load_plugin(self):
        """Test `load_plugin`."""

        plugin_name = "bad.plugin"  # Start with a bogus plugin name

        # FIXME(jathan): We're expecting a PluginNotFound to be raised, but
        # unittest doesn't appear to let that happen and we only see the
        # original ModuleNotFoundError, so this will have to do for now.
        with self.assertRaises(ModuleNotFoundError):
            load_plugin(plugin_name, settings)

        # Move to the dummy plugin. No errors should be raised (which is good).
        plugin_name = "nautobot.extras.tests.dummy_plugin"
        load_plugin(plugin_name, settings)
