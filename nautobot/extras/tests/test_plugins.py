from decimal import Decimal
from unittest import mock, skip

from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.http import QueryDict
from django.template import engines
from django.test import override_settings, tag
from django.urls import NoReverseMatch, reverse
import django_filters
import django_tables2 as tables
import netaddr

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core.filters import MultiValueCharFilter, MultiValueNumberFilter
from nautobot.core.testing import APIViewTestCases, disable_warnings, extract_page_body, TestCase, ViewTestCases
from nautobot.core.utils.lookup import get_table_for_model
from nautobot.data_validation.custom_validators import BaseValidator
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.extras import plugins
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipTypeChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.jobs import get_job
from nautobot.extras.models import CustomField, Relationship, RelationshipAssociation, Role, Secret, Status
from nautobot.extras.plugins.exceptions import PluginImproperlyConfigured
from nautobot.extras.plugins.utils import load_plugin
from nautobot.extras.plugins.validators import CustomValidator, wrap_model_clean_methods
from nautobot.extras.plugins.views import extract_app_data
from nautobot.extras.registry import DatasourceContent, registry
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.tenancy.filters import TenantFilterSet
from nautobot.tenancy.forms import TenantFilterForm
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.models import ObjectPermission


@tag("example_app")
class AppTest(TestCase):
    def test_config(self):
        self.assertIn(
            "example_app.ExampleAppConfig",
            settings.INSTALLED_APPS,
        )

    def test_models(self):
        # Test saving an instance
        from example_app.models import ExampleModel

        instance = ExampleModel(name="Instance 1", number=100)
        instance.save()
        self.assertIsNotNone(instance.pk)

        # Test deleting an instance
        instance.delete()
        self.assertIsNone(instance.pk)

    def test_admin(self):
        # Test admin view URL resolution
        url = reverse("admin:example_app_examplemodel_add")
        self.assertEqual(url, "/admin/example_app/examplemodel/add/")

    def test_banner_registration(self):
        """
        Check that App Banner is registered.
        """
        from example_app.banner import banner

        self.assertIn(banner, registry["plugin_banners"])

    def test_template_extensions_registration(self):
        """
        Check that App TemplateExtensions are registered.
        """
        from example_app.template_content import LocationContent

        self.assertIn(LocationContent, registry["plugin_template_extensions"]["dcim.location"])

    @skip("TODO: Idempotency issue. Skipped in favor of fixing API structlog exception logs.")
    def test_custom_validators_registration(self):
        """
        Check that App CustomValidators are registered correctly.
        """
        from example_app.custom_validators import LocationCustomValidator, RelationshipAssociationCustomValidator

        self.assertIn(LocationCustomValidator, registry["plugin_custom_validators"]["dcim.location"])
        self.assertIn(
            RelationshipAssociationCustomValidator,
            registry["plugin_custom_validators"]["extras.relationshipassociation"],
        )

        # Assert data-validation engine added one and only one validator for a given model.
        # https://github.com/nautobot/nautobot/pull/7180
        data_validation_validators = [
            v for v in registry["plugin_custom_validators"]["dcim.location"] if issubclass(v, BaseValidator)
        ]
        self.assertEqual(1, len(data_validation_validators))

    def test_jinja_filter_registration(self):
        """
        Check that App custom Jinja filters are registered correctly.
        """
        from example_app.jinja_filters import leet_speak

        rendering_engine = engines["jinja"]

        self.assertEqual(leet_speak, rendering_engine.env.filters[leet_speak.__name__])

    def test_graphql_types_registration(self):
        """
        Check that App GraphQL Types are registered.
        """
        from example_app.graphql.types import AnotherExampleModelType

        self.assertIn(AnotherExampleModelType, registry["plugin_graphql_types"])

    def test_extras_features_graphql(self):
        """
        Check that App GraphQL Types are registered.
        """
        registered_models = registry.get("model_features", {}).get("graphql", {})

        self.assertIn("example_app", registered_models.keys())
        self.assertIn("examplemodel", registered_models["example_app"])

    def test_jobs_registration(self):
        """
        Check that App Jobs are registered correctly and discoverable.
        """
        from example_app.jobs import ExampleJob

        self.assertIn(ExampleJob.class_path, registry.get("jobs", {}))
        self.assertEqual(ExampleJob, get_job("example_app.jobs.ExampleJob"))

    def test_git_datasource_contents_registration(self):
        """
        Check that App DatasourceContents are registered.
        """
        from example_app.datasources import refresh_git_text_files

        registered_datasources = registry.get("datasource_contents", {}).get("extras.gitrepository", [])

        app_datasource = DatasourceContent(
            name="text files",
            content_identifier="example_app.textfile",
            icon="mdi-note-text",
            weight=1000,
            callback=refresh_git_text_files,
        )

        for datasource in registered_datasources:
            if datasource.name == app_datasource.name:
                self.assertEqual(datasource.content_identifier, app_datasource.content_identifier)
                self.assertEqual(datasource.icon, app_datasource.icon)
                self.assertEqual(datasource.weight, app_datasource.weight)
                self.assertEqual(datasource.callback, app_datasource.callback)
                break
        else:
            self.fail(f"Datasource {app_datasource.name} not found in registered_datasources!")

    def test_middleware(self):
        """
        Check that App middleware is registered.
        """
        from example_app import config as example_config

        self.assertIn(
            "example_app.middleware.ExampleMiddleware",
            settings.MIDDLEWARE,
        )

        # Establish example config to have invalid middleware (tuple)
        class ExampleConfigWithMiddleware(example_config):
            middleware = ()

        # Validation should fail when a middleware is not a list
        with self.assertRaises(PluginImproperlyConfigured):
            ExampleConfigWithMiddleware.validate({}, settings.VERSION)

    def test_min_version(self):
        """
        Check enforcement of minimum Nautobot version.
        """
        from example_app import config as example_config

        with self.assertRaises(PluginImproperlyConfigured):
            example_config.validate({}, "0.8")

    def test_max_version(self):
        """
        Check enforcement of maximum Nautobot version.
        """
        from example_app import config as example_config

        with self.assertRaises(PluginImproperlyConfigured):
            example_config.validate({}, "10.0")

    def test_required_settings(self):
        """
        Validate enforcement of required settings.
        """
        from example_app import config as example_config

        class ExampleConfigWithRequiredSettings(example_config):
            required_settings = ["foo"]

        # Validation should pass when all required settings are present
        ExampleConfigWithRequiredSettings.validate({"foo": True}, settings.VERSION)

        # Validation should fail when a required setting is missing
        with self.assertRaises(PluginImproperlyConfigured):
            ExampleConfigWithRequiredSettings.validate({}, settings.VERSION)

        # Overload example config to have invalid required_settings (dict) and
        # assert that it should fail validation.
        ExampleConfigWithRequiredSettings.required_settings = {"foo": "bar"}
        with self.assertRaises(PluginImproperlyConfigured):
            ExampleConfigWithRequiredSettings.validate({}, settings.VERSION)

    def test_default_settings(self):
        """
        Validate population of default config settings.
        """
        from example_app import config as example_config

        class ExampleConfigWithDefaultSettings(example_config):
            default_settings = {
                "bar": 123,
                "SAMPLE_VARIABLE": "Testing",
            }

        # Populate the default value if setting has not been specified
        user_config = {}
        ExampleConfigWithDefaultSettings.validate(user_config, settings.VERSION)
        self.assertEqual(user_config["bar"], 123)
        # Don't overwrite constance_config Keys.
        self.assertNotIn("SAMPLE_VARIABLE", user_config)

        # Don't overwrite specified values
        user_config = {"bar": 456}
        ExampleConfigWithDefaultSettings.validate(user_config, settings.VERSION)
        self.assertEqual(user_config["bar"], 456)

        # Overload example config to have invalid default_settings (list) and
        # assert that it should fail validation.
        ExampleConfigWithDefaultSettings.required_settings = ["foo"]
        with self.assertRaises(PluginImproperlyConfigured):
            ExampleConfigWithDefaultSettings.validate({}, settings.VERSION)

    def test_installed_apps(self):
        """
        Validate that App installed Django apps and dependencies are are registered.
        """
        from example_app import config as example_config

        self.assertIn(
            "example_app.ExampleAppConfig",
            settings.INSTALLED_APPS,
        )
        self.assertIn("nautobot.extras.tests.example_app_dependency", settings.INSTALLED_APPS)

        # Establish example config to have invalid installed_apps (tuple)
        class ExampleConfigWithInstalledApps(example_config):
            installed_apps = ("foo", "bar")

        # Validation should fail when a installed_apps is not a list
        with self.assertRaises(PluginImproperlyConfigured):
            ExampleConfigWithInstalledApps.validate({}, settings.VERSION)

    def test_registry_nav_menu_dict(self):
        """
        Validate that Example App is adding new items to `registry["nav_menu"]`.
        """
        self.assertIn("Example Group 1", registry["nav_menu"]["tabs"]["Example Menu"]["groups"])

    def test_nautobot_database_ready_signal(self):
        """
        Validate that the App's registered callback for the `nautobot_database_ready` signal got called,
        creating a custom field definition in the database.
        """
        cf = CustomField.objects.get(key="example_app_auto_custom_field")
        self.assertEqual(cf.type, CustomFieldTypeChoices.TYPE_TEXT)
        self.assertEqual(cf.label, "Example App Automatically Added Custom Field")
        self.assertEqual(list(cf.content_types.all()), [ContentType.objects.get_for_model(Location)])

    def test_secrets_provider(self):
        """
        Validate that an App can provide a custom Secret provider and it will be used.
        """
        # The "constant-value" provider is implemented by the Example App
        secret = Secret.objects.create(
            name="Constant Secret",
            provider="constant-value",
            parameters={"constant": "It's a secret to everybody"},
        )
        self.assertEqual(secret.get_value(), secret.parameters["constant"])
        self.assertEqual(secret.get_value(obj=secret), secret.parameters["constant"])


@tag("example_app")
class AppGenericViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    @classmethod
    def setUpTestData(cls):
        from example_app.models import ExampleModel

        cls.model = ExampleModel
        # Example objects to test.
        ExampleModel.objects.create(name="Example 1", number=1)
        ExampleModel.objects.create(name="Example 2", number=2)
        ExampleModel.objects.create(name="Example 3", number=3)

        cls.form_data = {
            "name": "Example 4",
            "number": 42,
        }

        cls.csv_data = (
            "name,number",
            "Bob,16",
            "Alice,32",
            "Joe,0",
            "Horse,13",
        )

        cls.bulk_edit_data = {
            "number": 31337,
        }


@tag("example_app")
class AppListViewTest(TestCase):
    def test_list_plugins_anonymous(self):
        # Make the request as an unauthenticated user
        self.client.logout()
        response = self.client.get(reverse("plugins:plugins_list"))
        # Redirects to the login page
        self.assertHttpStatus(response, 302)

    def test_list_plugins_authenticated(self):
        response = self.client.get(reverse("plugins:plugins_list"))
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset)).lower()
        self.assertIn("example app", response_body, msg=response_body)

    def test_extract_app_data(self):
        app_config = apps.get_app_config("example_app")
        # Without a corresponding entry in marketplace_data
        self.assertEqual(
            extract_app_data(app_config, {"apps": []}),
            {
                "name": "Example Nautobot App",
                "package": "example_app",
                "app_label": "example_app",
                "author": "Nautobot development team",
                "author_email": "nautobot@example.com",
                "headline": "For testing purposes only",
                "description": "For testing purposes only",
                "version": "1.0.0",
                "home_url": "plugins:example_app:home",
                "config_url": "plugins:example_app:config",
                "docs_url": "plugins:example_app:docs",
            },
        )

        # With a corresponding entry in marketplace_data
        mock_marketplace_data = {
            "apps": [
                {
                    "name": "Nautobot Example App",
                    "use_cases": ["Example", "Development"],
                    "requires": [],
                    "docs": "https://example.com/docs/example_app/",
                    "headline": "Demonstrate and test various parts of Nautobot App APIs and functionality.",
                    "description": "An example of the kinds of things a Nautobot App can do, including ...",
                    "package_name": "example_app",
                    "author": "Network to Code (NTC)",
                    "availability": "Open Source",
                    "icon": "...",
                },
            ],
        }
        self.assertEqual(
            extract_app_data(app_config, mock_marketplace_data),
            {
                "name": "Nautobot Example App",
                "package": "example_app",
                "app_label": "example_app",
                "author": "Network to Code (NTC)",
                "author_email": "nautobot@example.com",
                "availability": "Open Source",
                "headline": "Demonstrate and test various parts of Nautobot App APIs and functionality.",
                "description": "An example of the kinds of things a Nautobot App can do, including ...",
                "version": "1.0.0",
                "home_url": "plugins:example_app:home",
                "config_url": "plugins:example_app:config",
                "docs_url": "plugins:example_app:docs",
            },
        )


@tag("example_app")
class PluginDetailViewTest(TestCase):
    def test_view_detail_anonymous(self):
        # Make the request as an unauthenticated user
        self.client.logout()
        response = self.client.get(reverse("plugins:plugin_detail", kwargs={"plugin": "example_app"}))
        # Redirects to the login page
        self.assertHttpStatus(response, 302)

    def test_view_detail_authenticated(self):
        response = self.client.get(reverse("plugins:plugin_detail", kwargs={"plugin": "example_app"}))
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))
        # App verbose name
        self.assertIn("Example Nautobot App", response_body, msg=response_body)
        # App description
        self.assertIn("For testing purposes only", response_body, msg=response_body)


class MarketplaceViewTest(TestCase):
    def test_view_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse("apps:apps_marketplace"))
        # Redirects to the login page
        self.assertHttpStatus(response, 302)

    def test_view_authenticated(self):
        response = self.client.get(reverse("apps:apps_marketplace"))
        self.assertHttpStatus(response, 200)


@tag("example_app")
class AppAPITest(APIViewTestCases.APIViewTestCase):
    bulk_update_data = {
        "number": 2600,
    }

    create_data = [
        {
            "name": "Pizza",
            "number": 10,
        },
        {
            "name": "Oysters",
            "number": 20,
        },
        {
            "name": "Bad combinations",
            "number": 30,
        },
    ]

    @classmethod
    def setUpTestData(cls):
        from example_app.models import ExampleModel

        cls.model = ExampleModel
        # Example objects to test.
        ExampleModel.objects.create(name="Example 1", number=1)
        ExampleModel.objects.create(name="Example 2", number=2)
        ExampleModel.objects.create(name="Example 3", number=3)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_api_urls(self):
        from example_app.models import ExampleModel

        # Test list URL resolution
        list_url = reverse("plugins-api:example_app-api:examplemodel-list")
        self.assertEqual(list_url, self._get_list_url())

        # Test detail URL resolution
        instance = ExampleModel.objects.first()
        detail_url = reverse("plugins-api:example_app-api:examplemodel-detail", kwargs={"pk": instance.pk})
        self.assertEqual(detail_url, self._get_detail_url(instance))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.core.api.serializers.reverse")
    def test_get_notes_url_on_object_raise_no_reverse_match(self, mock_reverse):
        # This test is to check the error handling when the user implemented a model without NotesMixin
        # But include the NotesSerializerMixin in the Model APIViewSet with NautobotModelViewSet

        # Raise NoReverseMatch in get_notes_url()
        mock_reverse.side_effect = mock.Mock(side_effect=NoReverseMatch())
        instance = self._get_queryset().first()
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))
        url = self._get_detail_url(instance)

        # Check if log messages and API data is properly rendered
        with self.assertLogs(logger="nautobot.core.api", level="WARNING") as cm:
            response = self.client.get(url, **self.header)
            self.assertHttpStatus(response, 200)
            self.assertIn("notes_url", response.data)
            self.assertIsNone(response.data["notes_url"])
            model_name = type(instance).__name__
            self.assertIn(
                (
                    f"Notes feature is not available for model {model_name}. "
                    "Please make sure to: "
                    f"1. Include NotesMixin from nautobot.extras.model.mixins in the {model_name} class definition "
                    f"2. Include NotesViewSetMixin from nautobot.extras.api.views in the {model_name}ViewSet "
                    "before including NotesSerializerMixin in the model serializer"
                ),
                cm.output[0],
            )

    # TODO: Unskip after resolving #2908, #2909
    @skip("DRF's built-in OrderingFilter triggering natural key attribute error in our base")
    def test_list_objects_ascending_ordered(self):
        pass

    @skip("DRF's built-in OrderingFilter triggering natural key attribute error in our base")
    def test_list_objects_descending_ordered(self):
        pass


class TestUserContextCustomValidator(CustomValidator):
    model = "dcim.locationtype"

    def clean(self):
        """
        Used to validate that the correct user context is available in the custom validator.
        """
        self.validation_error(f"TestUserContextCustomValidator: user is {self.context['user']}")


@tag("example_app")
class AppCustomValidationTest(TestCase):
    def setUp(self):
        # When creating a fresh test DB, wrapping model clean methods fails, which is normal.
        # This always occurs during the first run of migrations, however, During testing we
        # must manually call the method again to actually perform the action, now that the
        # ContentType table has been created.
        wrap_model_clean_methods()
        super().setUp()

    def test_custom_validator_raises_exception(self):
        location_type = LocationType.objects.get(name="Campus")
        location = Location(name="this location has a matching name", location_type=location_type)

        with self.assertRaises(ValidationError):
            location.clean()

    def test_relationship_association_validator_raises_exception(self):
        namespace = Namespace.objects.first()
        prefix_status = Status.objects.get_for_model(Prefix).first()
        prefix = Prefix.objects.create(
            prefix=netaddr.IPNetwork("192.168.10.0/24"), status=prefix_status, namespace=namespace
        )
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.22.0/24"), status=prefix_status, namespace=namespace)
        status = Status.objects.get_for_model(IPAddress).first()
        ipaddress = IPAddress.objects.create(address="192.168.22.1/24", status=status, namespace=namespace)
        relationship = Relationship.objects.create(
            label="Test Relationship",
            key="test_relationship",
            source_type=ContentType.objects.get_for_model(Prefix),
            destination_type=ContentType.objects.get_for_model(IPAddress),
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        relationship_assoc = RelationshipAssociation(relationship=relationship, source=prefix, destination=ipaddress)
        with self.assertRaises(ValidationError):
            relationship_assoc.clean()

    def test_custom_validator_non_web_request_uses_anonymous_user(self):
        location_type = LocationType.objects.get(name="Campus")
        before = registry["plugin_custom_validators"]["dcim.locationtype"]
        try:
            registry["plugin_custom_validators"]["dcim.locationtype"] = [TestUserContextCustomValidator]

            with self.assertRaises(ValidationError) as context:
                location_type.clean()
            self.assertEqual(context.exception.message, "TestUserContextCustomValidator: user is AnonymousUser")
        finally:
            registry["plugin_custom_validators"]["dcim.locationtype"] = before

    def test_custom_validator_web_request_uses_real_user(self):
        location_type = LocationType.objects.get(name="Campus")
        before = registry["plugin_custom_validators"]["dcim.locationtype"]
        try:
            registry["plugin_custom_validators"]["dcim.locationtype"] = [TestUserContextCustomValidator]

            with self.assertRaises(ValidationError) as context:
                with web_request_context(user=self.user):
                    location_type.clean()
            self.assertEqual(context.exception.message, f"TestUserContextCustomValidator: user is {self.user}")
        finally:
            registry["plugin_custom_validators"]["dcim.locationtype"] = before


@tag("example_app")
class ExampleModelCustomActionViewTest(TestCase):
    """Test for custom action view `all_names` added to Example App"""

    @classmethod
    def setUpTestData(cls):
        from example_app.models import ExampleModel

        cls.model = ExampleModel
        ExampleModel.objects.create(name="Example 1", number=100)
        ExampleModel.objects.create(name="Example 2", number=200)
        ExampleModel.objects.create(name="Example 3", number=300)
        cls.custom_view_url = reverse("plugins:example_app:examplemodel_all_names")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_custom_action_view_anonymous(self):
        self.client.logout()
        response = self.client.get(self.custom_view_url)
        self.assertHttpStatus(response, 200)
        # TODO: all this is doing is checking that a login link appears somewhere on the page (i.e. in the nav).
        response_body = response.content.decode(response.charset)
        self.assertIn("/login/?next=", response_body, msg=response_body)

    def test_custom_action_view_without_permission(self):
        with disable_warnings("django.request"):
            response = self.client.get(self.custom_view_url)
            self.assertHttpStatus(response, 403)
            response_body = response.content.decode(response.charset)
            self.assertNotIn("/login/", response_body, msg=response_body)

    def test_custom_action_view_with_permission(self):
        self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")

        response = self.client.get(self.custom_view_url)
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))

        for example_model in self.model.objects.all():
            self.assertIn(example_model.name, response_body, msg=response_body)

    def test_custom_action_view_with_constrained_permission(self):
        instance1 = self.model.objects.first()
        # Add object-level permission
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        response = self.client.get(self.custom_view_url)
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))

        self.assertIn(instance1.name, response_body, msg=response_body)

        for example_model in self.model.objects.exclude(pk=instance1.pk):
            self.assertNotIn(example_model.name, response_body, msg=response_body)


@tag("example_app")
class FilterExtensionTest(TestCase):
    """
    Tests for adding filter extensions
    """

    queryset = Tenant.objects.all()
    filterset = TenantFilterSet
    user_permissions = ("tenancy.view_tenant",)

    @classmethod
    def setUpTestData(cls):
        tenant_groups = TenantGroup.objects.all()[:3]
        tenants = (
            Tenant.objects.create(name="Tenant 1", tenant_group=tenant_groups[0], description="tenant-1.nautobot.com"),
            Tenant.objects.create(name="Tenant 2", tenant_group=tenant_groups[1], description="tenant-2.nautobot.com"),
            Tenant.objects.create(name="Tenant 3", tenant_group=tenant_groups[2], description="tenant-3.nautobot.com"),
        )
        Tenant.objects.create(name="Valid filter tenant", description="ABC12")
        Tenant.objects.create(name="Another valid filter tenant", description="DEF34")
        Tenant.objects.create(name="Invalid filter tenant", description="abc12")
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        Location.objects.create(
            name="Location 1",
            tenant=tenants[0],
            location_type=location_type,
            status=location_status,
        )
        Location.objects.create(
            name="Location 2",
            tenant=tenants[1],
            location_type=location_type,
            status=location_status,
        )
        Location.objects.create(
            name="Location 3",
            tenant=tenants[2],
            location_type=location_type,
            status=location_status,
        )

        manufacturers = Manufacturer.objects.all()[:3]

        roles = Role.objects.get_for_model(Device)

        DeviceType.objects.create(
            manufacturer=manufacturers[0],
            model="Model 1",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
        )
        DeviceType.objects.create(
            manufacturer=manufacturers[1],
            model="Model 2",
            part_number="Part Number 2",
            u_height=2,
            is_full_depth=True,
        )
        DeviceType.objects.create(
            manufacturer=manufacturers[2],
            model="Model 3",
            part_number="Part Number 3",
            u_height=3,
            is_full_depth=False,
        )

        device_status = Status.objects.get_for_model(Device).first()
        Device.objects.create(
            name="Device 1",
            device_type=DeviceType.objects.get(model="Model 1"),
            role=roles[0],
            tenant=tenants[0],
            location=Location.objects.get(name="Location 1"),
            status=device_status,
        )
        Device.objects.create(
            name="Device 2",
            device_type=DeviceType.objects.get(model="Model 2"),
            role=roles[1],
            tenant=tenants[1],
            location=Location.objects.get(name="Location 2"),
            status=device_status,
        )
        Device.objects.create(
            name="Device 3",
            device_type=DeviceType.objects.get(model="Model 2"),
            role=roles[3],
            tenant=tenants[2],
            location=Location.objects.get(name="Location 3"),
            status=device_status,
        )

    def test_basic_custom_filter(self):
        """
        Test that adding a custom filter, filters correctly.
        """
        params = {"example_app_description": ["tenant-1.nautobot.com"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_added_lookup(self):
        """
        Test that the dynamically created filters work on App created filters as well.
        """
        params = {"example_app_description__ic": ["tenant-1.nautobot"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_nested_lookup(self):
        """
        Test that filters work against nested filters.
        """
        params = {"example_app_dtype": ["Model 1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"example_app_dtype": ["Model 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_filter_method_param(self):
        """
        Test that a custom filter works if a valid callable `method` is provided.
        """
        params = {"example_app_sdescrip": ["tenant-1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_filter_form(self):
        """
        Test that filter forms work when added via an App.
        """
        form = TenantFilterForm(
            data={
                "example_app_description": "tenant-1.nautobot.com",
                "example_app_dtype": "model-1",
                "example_app_sdescrip": "tenant-1",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertIn("example_app_description", form.fields.keys())

    def test_filter_form_validators(self):
        from example_app.filter_extensions import TenantFilterExtension

        field_name = "example_app_validated_description"
        field = TenantFilterExtension.filterform_fields[field_name]
        self.assertIs(TenantFilterForm.base_fields[field_name], field)  # pylint: disable=no-member
        self.assertEqual(TenantFilterForm().fields[field_name].validators, field.validators)
        for value, valid in (("ABC12", True), ("abc12", False), ("", True)):
            with self.subTest(value=value):
                form = TenantFilterForm(data={field_name: value})
                self.assertEqual(form.is_valid(), valid, form.errors)
                if not valid:
                    self.assertEqual(form.errors[field_name], ["Invalid filter value"])

    def test_filterset_form_validators(self):
        field_name = "example_app_validated_description"
        filterset = self.filterset({field_name: ["abc12"]}, self.queryset)
        self.assertFalse(filterset.is_valid())
        self.assertEqual(filterset.errors[field_name], ["Invalid filter value"])

    def test_list_filter_form_validators(self):
        response = self.client.get(
            reverse("tenancy:tenant_list"),
            {"example_app_validated_description": "abc12"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["table"].rows), 0)
        self.assertContains(response, "Invalid filters were specified")
        self.assertContains(response, "Invalid filter value")

    def test_validated_filter_results(self):
        params = {"example_app_validated_description": "ABC12"}
        filterset = self.filterset(params, self.queryset)
        self.assertTrue(filterset.is_valid(), filterset.errors)
        self.assertQuerySetEqualAndNotEmpty(filterset.qs, self.queryset.filter(description="ABC12"))

        response = self.client.get(reverse("tenancy:tenant_list"), params, headers={"HX-Request": "true"})
        self.assertHttpStatus(response, 200)
        self.assertCountEqual(
            [row.record.pk for row in response.context["table"].rows],
            self.queryset.filter(description="ABC12").values_list("pk", flat=True),
        )

    def test_multiple_filter_values(self):
        field_name = "example_app_validated_description"
        for values, valid in ((["ABC12", "DEF34"], True), (["abc12", "ABC12"], False), (["ABC12", "abc12"], False)):
            for querydict in (False, True):
                with self.subTest(values=values, querydict=querydict):
                    params = {field_name: values}
                    if querydict:
                        params = QueryDict(mutable=True)
                        params.setlist(field_name, values)
                    filterset = self.filterset(params, self.queryset)
                    self.assertEqual(filterset.is_valid(), valid, filterset.errors)
                    if valid:
                        self.assertEqual(filterset.form.cleaned_data[field_name], values)
                        self.assertQuerySetEqualAndNotEmpty(filterset.qs, self.queryset.filter(description__in=values))
                    else:
                        self.assertEqual(filterset.errors[field_name], ["Invalid filter value"])
                        self.assertNotIn(field_name, filterset.form.cleaned_data)

            response = self.client.get(
                reverse("tenancy:tenant_list"), {field_name: values}, headers={"HX-Request": "true"}
            )
            self.assertHttpStatus(response, 200)
            expected_count = self.queryset.filter(description__in=values).count() if valid else 0
            self.assertEqual(len(response.context["table"].rows), expected_count)

    def test_optional_filter_values(self):
        field_name = "example_app_validated_description"
        for params in ({}, {field_name: ""}, {field_name: []}, {field_name: [""]}):
            with self.subTest(params=params):
                filterset = self.filterset(params, self.queryset)
                self.assertTrue(filterset.is_valid(), filterset.errors)
                self.assertQuerySetEqualAndNotEmpty(filterset.qs, self.queryset)

    def test_builtin_filters(self):
        params = {"name": ["Tenant 1", "Tenant 2"]}
        filterset = self.filterset(params, self.queryset)
        self.assertTrue(filterset.is_valid(), filterset.errors)
        self.assertQuerySetEqualAndNotEmpty(filterset.qs, self.queryset.filter(name__in=params["name"]))
        response = self.client.get(reverse("tenancy:tenant_list"), params, headers={"HX-Request": "true"})
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.context["table"].rows), 2)

    def _register_test_extension(self, filterset_fields, filterform_fields, filterset_form_class=forms.Form):
        """Register real extensions on isolated subclasses to avoid changing the global test environment."""

        class ExtendedFilterSet(TenantFilterSet):
            class Meta(TenantFilterSet.Meta):
                form = filterset_form_class

        class ExtendedFilterForm(TenantFilterForm):
            pass

        class Extension(plugins.FilterExtension):
            model = "tenancy.tenant"

        Extension.filterset_fields = filterset_fields
        Extension.filterform_fields = filterform_fields
        with (
            mock.patch("nautobot.core.utils.lookup.get_filterset_for_model", return_value=ExtendedFilterSet),
            mock.patch("nautobot.core.utils.lookup.get_form_for_model", return_value=ExtendedFilterForm),
        ):
            plugins.register_filter_extensions([Extension], "example_app")
        return ExtendedFilterSet, ExtendedFilterForm

    def test_multiple_validators(self):
        calls = []

        def custom_validator(value):
            calls.append(value)
            if value != "ABC12":
                raise ValidationError("Custom validation error", code="custom")

        field_name = "example_app_validators"
        field = forms.CharField(
            required=False,
            validators=[RegexValidator(r"^[A-Z]{3}[0-9]{2}$", message="Invalid filter value"), custom_validator],
        )
        filterset_class, form_class = self._register_test_extension(
            {field_name: MultiValueCharFilter(field_name="description")}, {field_name: field}
        )
        self.assertIs(form_class.base_fields[field_name], field)  # pylint: disable=no-member
        filterset = filterset_class({field_name: ["abc12"]}, self.queryset)
        self.assertFalse(filterset.is_valid())
        self.assertEqual(filterset.errors[field_name], ["Invalid filter value", "Custom validation error"])
        self.assertEqual(calls, ["abc12"])
        self.assertEqual([error.code for error in filterset.errors.as_data()[field_name]], ["invalid", "custom"])
        self.assertTrue(filterset_class({field_name: "ABC12"}, self.queryset).is_valid())
        self.assertEqual(calls, ["abc12", "ABC12"])

    def test_integer_form_field_with_string_filter(self):
        def validate_even(value):
            if value % 2:
                raise ValidationError("Must be even")

        field_name = "example_app_integer"
        filterset_class, _ = self._register_test_extension(
            {field_name: MultiValueCharFilter(field_name="description")},
            {field_name: forms.IntegerField(required=False, min_value=10, max_value=99, validators=[validate_even])},
        )
        for value, error in (
            ("42", None),
            ("9", "Ensure this value is greater than or equal to 10."),
            ("100", "Ensure this value is less than or equal to 99."),
            ("41", "Must be even"),
            ("invalid", "Enter a whole number."),
            ("", None),
        ):
            with self.subTest(value=value):
                filterset = filterset_class({field_name: [value]}, self.queryset)
                self.assertEqual(filterset.is_valid(), error is None, filterset.errors)
                if error:
                    self.assertIn(error, filterset.errors[field_name])
                else:
                    self.assertEqual(filterset.form.cleaned_data[field_name], [value] if value else [])

    def test_multiple_choice_form_field(self):
        def validate_selection(values):
            if len(values) > 1:
                raise ValidationError("Select only one description")

        field_name = "example_app_choices"
        choices = [("ABC12", "ABC12"), ("DEF34", "DEF34")]
        filterset_class, _ = self._register_test_extension(
            {field_name: django_filters.MultipleChoiceFilter(field_name="description", choices=choices)},
            {field_name: forms.MultipleChoiceField(required=False, choices=choices, validators=[validate_selection])},
        )
        for values in (["ABC12"], ["ABC12", "DEF34"], []):
            with self.subTest(values=values):
                params = QueryDict(mutable=True)
                params.setlist(field_name, values)
                filterset = filterset_class(params, self.queryset)
                self.assertEqual(filterset.is_valid(), len(values) <= 1, filterset.errors)
                if len(values) > 1:
                    self.assertEqual(filterset.errors[field_name], ["Select only one description"])

    def test_string_form_field_with_numeric_filter(self):
        field_name = "example_app_number"
        filterset_class, _ = self._register_test_extension(
            {field_name: MultiValueNumberFilter(field_name="description")},
            {field_name: forms.CharField(required=False, validators=[RegexValidator(r"^[0-9]{2}$")])},
        )
        filterset = filterset_class({field_name: ["42"]}, self.queryset)
        self.assertTrue(filterset.is_valid(), filterset.errors)
        self.assertEqual(filterset.form.cleaned_data[field_name], [Decimal("42")])
        self.assertFalse(filterset_class({field_name: ["9"]}, self.queryset).is_valid())

    def test_custom_filterset_form_clean(self):
        class CopyingForm(forms.Form):
            def clean(self):
                return dict(super().clean())

        class NoReturnForm(forms.Form):
            def clean(self):
                super().clean()
                self.cleaned_data = dict(self.cleaned_data)

        field_name = "example_app_custom_form"
        for form_class in (CopyingForm, NoReturnForm):
            with self.subTest(form_class=form_class):
                filterset_class, _ = self._register_test_extension(
                    {field_name: MultiValueCharFilter(field_name="description")},
                    {field_name: forms.CharField(required=False, validators=[RegexValidator(r"^ABC12$")])},
                    filterset_form_class=form_class,
                )
                filterset = filterset_class({field_name: ["abc12"]}, self.queryset)
                with mock.patch.object(filterset.filters[field_name], "filter") as filter_method:
                    filterset.qs
                filter_method.assert_not_called()
                self.assertFalse(filterset.is_valid())
                self.assertNotIn(field_name, filterset.form.cleaned_data)

    def test_multiple_extensions_and_registration_conflicts(self):
        field_name = "example_app_first"
        field = forms.CharField(required=False, validators=[RegexValidator(r"^ABC12$")])
        filterset_class, form_class = self._register_test_extension(
            {field_name: MultiValueCharFilter(field_name="description")}, {field_name: field}
        )

        class OtherExtension(plugins.FilterExtension):
            model = "tenancy.tenant"
            filterset_fields = {"other_app_second": MultiValueCharFilter(field_name="description")}
            filterform_fields = {
                field_name: forms.CharField(validators=[RegexValidator(r"^wrong$")]),
                "other_app_second": forms.CharField(required=False, validators=[RegexValidator(r"^DEF34$")]),
            }

        with (
            mock.patch("nautobot.core.utils.lookup.get_filterset_for_model", return_value=filterset_class),
            mock.patch("nautobot.core.utils.lookup.get_form_for_model", return_value=form_class),
            self.assertLogs("nautobot.extras.plugins", level="ERROR"),
        ):
            plugins.register_filter_extensions([OtherExtension], "other_app")

        self.assertIs(form_class.base_fields[field_name], field)  # pylint: disable=no-member
        filterset = filterset_class({field_name: "ABC12", "other_app_second": "DEF34"}, self.queryset)
        self.assertTrue(filterset.is_valid(), filterset.errors)
        filterset = filterset_class({field_name: "wrong", "other_app_second": "wrong"}, self.queryset)
        self.assertFalse(filterset.is_valid())
        self.assertEqual(set(filterset.errors), {field_name, "other_app_second"})
        self.assertNotIn("other_app_second", self.filterset().filters)

    def test_filterset_validators_are_retained(self):
        field_name = "example_app_both"
        filterset_class, _ = self._register_test_extension(
            {field_name: django_filters.CharFilter(field_name="description", min_length=6)},
            {field_name: forms.CharField(required=False, validators=[RegexValidator(r"^[A-Z]{3}[0-9]{2}$")])},
        )
        filterset = filterset_class({field_name: "ABC12"}, self.queryset)
        self.assertFalse(filterset.is_valid())
        self.assertEqual(filterset.errors[field_name], ["Ensure this value has at least 6 characters (it has 5)."])

    def test_form_only_extension(self):
        field_name = "name__iew"
        filterset_class, _ = self._register_test_extension(
            {}, {field_name: forms.CharField(required=False, validators=[RegexValidator(r"^Tenant [0-9]$")])}
        )
        filterset = filterset_class({field_name: ["Tenant 1"]}, self.queryset)
        self.assertTrue(filterset.is_valid(), filterset.errors)
        self.assertQuerySetEqualAndNotEmpty(filterset.qs, self.queryset.filter(name="Tenant 1"))
        self.assertFalse(filterset_class({field_name: ["tenant 1"]}, self.queryset).is_valid())

    def test_form_field_without_filter(self):
        filterset_class, _ = self._register_test_extension(
            {}, {"example_app_unmatched": forms.CharField(validators=[RegexValidator(r"^valid$")])}
        )
        with override_settings(STRICT_FILTERING=False):
            filterset = filterset_class({"name": ["Tenant 1"], "example_app_unmatched": "invalid"}, self.queryset)
            self.assertTrue(filterset.is_valid(), filterset.errors)
            self.assertQuerySetEqualAndNotEmpty(filterset.qs, self.queryset.filter(name="Tenant 1"))

    def test_invalid_filter_is_not_applied(self):
        filterset = self.filterset({"example_app_validated_description": ["abc12"]}, self.queryset)
        with mock.patch.object(filterset.filters["example_app_validated_description"], "filter") as filter_method:
            filterset.qs
        filter_method.assert_not_called()
        self.assertFalse(filterset.is_valid())

    def test_filter_form_prefix(self):
        field_name = "example_app_validated_description"
        params = QueryDict(mutable=True)
        params.setlist(f"filters-{field_name}", ["abc12", "ABC12"])
        filterset = self.filterset(params, self.queryset, prefix="filters")
        with override_settings(STRICT_FILTERING=False):
            self.assertFalse(filterset.is_valid())
            self.assertEqual(filterset.errors[field_name], ["Invalid filter value"])

    def test_api_filter_form_validators(self):
        for value, expected_status in (("ABC12", 200), ("abc12", 400)):
            with self.subTest(value=value):
                response = self.client.get(
                    reverse("tenancy-api:tenant-list"), {"example_app_validated_description": value}
                )
                self.assertHttpStatus(response, expected_status)
                if expected_status == 200:
                    self.assertCountEqual(
                        [tenant["description"] for tenant in response.data["results"]],
                        self.queryset.filter(description=value).values_list("description", flat=True),
                    )
                else:
                    self.assertEqual(response.data["example_app_validated_description"], ["Invalid filter value"])


class TableExtensionTest(TestCase):
    """Tests for adding table extensions."""

    def test_alter_queryset(self):
        """Test the 'alter_queryset' method of the TableExtension class."""
        extension = plugins.TableExtension()
        queryset = object()
        result = extension.alter_queryset(queryset)
        self.assertEqual(result, queryset)

    def test__add_columns_into_model_table(self):
        """Test the '_add_columns_into_model_table' function."""
        extension = plugins.TableExtension()
        extension.model = "tenancy.tenant"
        extension.table_columns = {
            "tenant_group": tables.Column(verbose_name="Name conflicts with existing column"),
            "tenant_success": tables.Column(verbose_name="This name should be registered"),
        }
        extension.add_to_default_columns = ["tenant_group", "tenant_success"]

        with self.assertLogs("nautobot.extras.plugins", level="WARNING") as logger:
            try:
                plugins._add_columns_into_model_table(extension, "tenant")
                table = get_table_for_model(extension.model)
                expected = [
                    "ERROR:nautobot.extras.plugins:tenant: There was a name conflict with existing "
                    "table column `tenant_group`, the custom column was ignored."
                ]
                with self.subTest("error is logged"):
                    self.assertEqual(logger.output, expected)

                with self.subTest("column is added to default_columns"):
                    self.assertIn("tenant_success", table.base_columns)
            finally:
                del table.base_columns["tenant_success"]

    def test__add_column_to_table_base_columns(self):
        """Test the '_add_column_to_table_base_columns' function."""
        table = get_table_for_model("tenancy.tenant")

        with self.subTest("raises TypeError"):
            column = object()
            with self.assertRaises(TypeError) as context:
                plugins._add_column_to_table_base_columns(table, "test_column", column, "my_app")
                self.assertEqual(
                    context.exception, "Custom column `test_column` is not an instance of django_tables2.Column."
                )

        with self.subTest("raises AttributeError"):
            column = tables.Column()
            with self.assertRaises(AttributeError) as context:
                plugins._add_column_to_table_base_columns(table, "pk", column, "my_app")
                self.assertEqual(
                    context.exception, "There was a conflict with table column `pk`, the custom column was ignored."
                )

        with self.subTest("Adds column to base_columns"):
            column = tables.Column()
            plugins._add_column_to_table_base_columns(table, "unique_name", column, "my_app")
            try:
                self.assertIn("unique_name", table.base_columns)
            finally:
                del table.base_columns["unique_name"]

    def test__modify_default_table_columns(self):
        """Test the '_modify_default_table_columns' function."""
        extension = plugins.TableExtension()
        extension.model = "tenancy.tenant"
        extension.add_to_default_columns = ["new_column"]
        extension.remove_from_default_columns = ["description"]

        table = get_table_for_model(extension.model)
        table.base_columns["new_column"] = tables.Column()

        try:
            plugins._modify_default_table_columns(extension, "my_app")

            with self.subTest("column is added to default_columns"):
                self.assertIn("new_column", table.Meta.default_columns)

            with self.subTest("column is removed from default_columns"):
                self.assertNotIn("description", table.Meta.default_columns)
        finally:
            del table.base_columns["new_column"]
            table.Meta.default_columns = (name for name in table.Meta.default_columns if name != "new_column")

    def test__validate_is_subclass_of_table_extension(self):
        """Test the '_validate_is_subclass_of_table_extension' function."""
        with self.assertRaises(TypeError):
            plugins._validate_is_subclass_of_table_extension(object)

    def test__validate_table_column_name_is_prefixed_with_app_name(self):
        """Test the '_validate_table_column_name_is_prefixed_with_app_name' function."""
        with self.assertRaises(ValueError) as context:
            plugins._validate_table_column_name_is_prefixed_with_app_name("not_prefixed", "prefix")
            self.assertEqual(
                context.exception,
                "Attempted to create a custom table column `not_prefixed` that did not start with `prefix`",
            )


class LoadPluginTest(TestCase):
    """
    Validate that plugin helpers work as intended.

    Only `load_plugin` is tested, because that is called once for each plugin by
    `load_plugins`.
    """

    def test_load_plugin(self):
        """Test `load_plugin`."""

        app_name = "bad.plugin"  # Start with a bogus App name

        # FIXME(jathan): We're expecting a PluginNotFound to be raised, but
        # unittest doesn't appear to let that happen and we only see the
        # original ModuleNotFoundError, so this will have to do for now.
        with self.assertRaises(ModuleNotFoundError):
            load_plugin(app_name, settings)

        # Move to the example app. No errors should be raised (which is good).
        app_name = "example_app"
        load_plugin(app_name, settings)


@tag("example_app", "example_app_with_view_override")
class TestAppCoreViewOverrides(TestCase):
    """
    Validate that overridden core views work as expected.

    The functionality is loaded and unloaded by this test case to isolate it from the rest of the test suite.
    """

    def setUp(self):
        super().setUp()
        self.device = create_test_device("Device")
        provider = Provider.objects.first()
        circuit_type = CircuitType.objects.first()
        self.circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            circuit_type=circuit_type,
            status=Status.objects.get_for_model(Circuit).first(),
        )
        self.user.is_superuser = True
        self.user.save()

    def test_views_are_overridden(self):
        response = self.client.get(reverse("plugins:example_app:view_to_be_overridden"))
        self.assertEqual("Hello world! I'm an overridden view.", response.content.decode(response.charset))

        response = self.client.get(
            f"{reverse('plugins:plugin_detail', kwargs={'plugin': 'example_app_with_view_override'})}"
        )
        self.assertIn(
            "plugins:example_app:view_to_be_overridden <code>example_app_with_view_override.views.ViewOverride</code>",
            extract_page_body(response.content.decode(response.charset)),
        )


@tag("example_app")
class PluginTemplateExtensionsTest(TestCase):
    """
    Test that registered TemplateExtensions inject content as expected
    """

    def setUp(self):
        super().setUp()
        self.location = Location.objects.first()
        self.user.is_superuser = True
        self.user.save()

    def test_list_view_buttons(self):
        response = self.client.get(reverse("dcim:location_list"))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("LOCATION CONTENT - BUTTONS LIST", response_body, msg=response_body)

    def test_detail_view_buttons(self):
        response = self.client.get(reverse("dcim:location", kwargs={"pk": self.location.pk}))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("APP INJECTED LOCATION CONTENT - BUTTONS", response_body, msg=response_body)

    def test_detail_view_left_page(self):
        response = self.client.get(reverse("dcim:location", kwargs={"pk": self.location.pk}))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("APP INJECTED CONTENT - LEFT", response_body, msg=response_body)

    def test_detail_view_right_page(self):
        response = self.client.get(reverse("dcim:location", kwargs={"pk": self.location.pk}))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("APP INJECTED CONTENT - RIGHT", response_body, msg=response_body)

    def test_detail_view_full_width_page(self):
        response = self.client.get(reverse("dcim:location", kwargs={"pk": self.location.pk}))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("APP INJECTED CONTENT - FULL WIDTH", response_body, msg=response_body)
