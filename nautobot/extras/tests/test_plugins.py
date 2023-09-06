from unittest import mock, skipIf, skip

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.template import engines
from django.test import override_settings
from django.urls import NoReverseMatch, reverse

import netaddr

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core.celery import app
from nautobot.core.testing import APIViewTestCases, TestCase, ViewTestCases, extract_page_body
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Location, LocationType
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.tenancy.filters import TenantFilterSet
from nautobot.tenancy.forms import TenantFilterForm
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipTypeChoices
from nautobot.extras.jobs import get_job
from nautobot.extras.models import CustomField, Relationship, RelationshipAssociation, Role, Secret, Status
from nautobot.extras.plugins.exceptions import PluginImproperlyConfigured
from nautobot.extras.plugins.utils import load_plugin
from nautobot.extras.plugins.validators import wrap_model_clean_methods
from nautobot.extras.registry import registry, DatasourceContent
from nautobot.ipam.models import Prefix, IPAddress, Namespace
from nautobot.users.models import ObjectPermission

from example_plugin import config as example_config
from example_plugin.datasources import refresh_git_text_files
from example_plugin.models import ExampleModel


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginTest(TestCase):
    def test_config(self):
        self.assertIn(
            "example_plugin.ExamplePluginConfig",
            settings.INSTALLED_APPS,
        )

    def test_models(self):
        # Test saving an instance
        instance = ExampleModel(name="Instance 1", number=100)
        instance.save()
        self.assertIsNotNone(instance.pk)

        # Test deleting an instance
        instance.delete()
        self.assertIsNone(instance.pk)

    def test_admin(self):
        # Test admin view URL resolution
        url = reverse("admin:example_plugin_examplemodel_add")
        self.assertEqual(url, "/admin/example_plugin/examplemodel/add/")

    def test_banner_registration(self):
        """
        Check that plugin Banner is registered.
        """
        from example_plugin.banner import banner

        self.assertIn(banner, registry["plugin_banners"])

    def test_template_extensions_registration(self):
        """
        Check that plugin TemplateExtensions are registered.
        """
        from example_plugin.template_content import LocationContent

        self.assertIn(LocationContent, registry["plugin_template_extensions"]["dcim.location"])

    def test_custom_validators_registration(self):
        """
        Check that plugin custom validators are registered correctly.
        """
        from example_plugin.custom_validators import LocationCustomValidator, RelationshipAssociationCustomValidator

        self.assertIn(LocationCustomValidator, registry["plugin_custom_validators"]["dcim.location"])
        self.assertIn(
            RelationshipAssociationCustomValidator,
            registry["plugin_custom_validators"]["extras.relationshipassociation"],
        )

    def test_jinja_filter_registration(self):
        """
        Check that plugin custom jinja filters are registered correctly.
        """
        from example_plugin.jinja_filters import leet_speak

        rendering_engine = engines["jinja"]

        self.assertEqual(leet_speak, rendering_engine.env.filters[leet_speak.__name__])

    def test_graphql_types_registration(self):
        """
        Check that plugin GraphQL Types are registered.
        """
        from example_plugin.graphql.types import AnotherExampleModelType

        self.assertIn(AnotherExampleModelType, registry["plugin_graphql_types"])

    def test_extras_features_graphql(self):
        """
        Check that plugin GraphQL Types are registered.
        """
        registered_models = registry.get("model_features", {}).get("graphql", {})

        self.assertIn("example_plugin", registered_models.keys())
        self.assertIn("examplemodel", registered_models["example_plugin"])

    def test_jobs_registration(self):
        """
        Check that plugin jobs are registered correctly and discoverable.
        """
        from example_plugin.jobs import ExampleJob

        self.assertIn(ExampleJob, registry.get("plugin_jobs", []))
        self.assertEqual(ExampleJob, get_job("example_plugin.jobs.ExampleJob"))
        self.assertIn("example_plugin.jobs.ExampleJob", app.tasks)

    def test_git_datasource_contents_registration(self):
        """
        Check that plugin DatasourceContents are registered.
        """
        registered_datasources = registry.get("datasource_contents", {}).get("extras.gitrepository", [])

        plugin_datasource = DatasourceContent(
            name="text files",
            content_identifier="example_plugin.textfile",
            icon="mdi-note-text",
            weight=1000,
            callback=refresh_git_text_files,
        )

        for datasource in registered_datasources:
            if datasource.name == plugin_datasource.name:
                self.assertEqual(datasource.content_identifier, plugin_datasource.content_identifier)
                self.assertEqual(datasource.icon, plugin_datasource.icon)
                self.assertEqual(datasource.weight, plugin_datasource.weight)
                self.assertEqual(datasource.callback, plugin_datasource.callback)
                break
        else:
            self.fail(f"Datasource {plugin_datasource.name} not found in registered_datasources!")

    def test_middleware(self):
        """
        Check that plugin middleware is registered.
        """
        self.assertIn(
            "example_plugin.middleware.ExampleMiddleware",
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
        with self.assertRaises(PluginImproperlyConfigured):
            example_config.validate({}, "0.8")

    def test_max_version(self):
        """
        Check enforcement of maximum Nautobot version.
        """
        with self.assertRaises(PluginImproperlyConfigured):
            example_config.validate({}, "10.0")

    def test_required_settings(self):
        """
        Validate enforcement of required settings.
        """

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
        Validate that plugin installed apps and dependencies are are registered.
        """
        self.assertIn(
            "example_plugin.ExamplePluginConfig",
            settings.INSTALLED_APPS,
        )
        self.assertIn("nautobot.extras.tests.example_plugin_dependency", settings.INSTALLED_APPS)

        # Establish example config to have invalid installed_apps (tuple)
        class ExampleConfigWithInstalledApps(example_config):
            installed_apps = ("foo", "bar")

        # Validation should fail when a installed_apps is not a list
        with self.assertRaises(PluginImproperlyConfigured):
            ExampleConfigWithInstalledApps.validate({}, settings.VERSION)

    def test_registry_nav_menu_dict(self):
        """
        Validate that example plugin is adding new items to `registry["nav_menu"]`.
        """
        self.assertIn("Example Group 1", registry["nav_menu"]["tabs"]["Example Menu"]["groups"])

    def test_nautobot_database_ready_signal(self):
        """
        Validate that the plugin's registered callback for the `nautobot_database_ready` signal got called,
        creating a custom field definition in the database.
        """
        cf = CustomField.objects.get(key="example_plugin_auto_custom_field")
        self.assertEqual(cf.type, CustomFieldTypeChoices.TYPE_TEXT)
        self.assertEqual(cf.label, "Example Plugin Automatically Added Custom Field")
        self.assertEqual(list(cf.content_types.all()), [ContentType.objects.get_for_model(Location)])

    def test_secrets_provider(self):
        """
        Validate that a plugin can provide a custom Secret provider and it will be used.
        """
        # The "constant-value" provider is implemented by the plugin
        secret = Secret.objects.create(
            name="Constant Secret",
            provider="constant-value",
            parameters={"constant": "It's a secret to everybody"},
        )
        self.assertEqual(secret.get_value(), secret.parameters["constant"])
        self.assertEqual(secret.get_value(obj=secret), secret.parameters["constant"])


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginGenericViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    model = ExampleModel

    @classmethod
    def setUpTestData(cls):
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


class PluginListViewTest(TestCase):
    def test_list_plugins_anonymous(self):
        # Make the request as an unauthenticated user
        self.client.logout()
        response = self.client.get(reverse("plugins:plugins_list"))
        # Redirects to the login page
        self.assertHttpStatus(response, 302)

    def test_list_plugins_authenticated_superuser(self):
        self.user.is_superuser = True
        self.user.save()

        response = self.client.get(reverse("plugins:plugins_list"))
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset)).lower()
        self.assertIn("example app", response_body, msg=response_body)

    def test_list_plugins_authenticated_not_admin(self):
        response = self.client.get(reverse("plugins:plugins_list"))
        # Access Denied
        self.assertHttpStatus(response, 403)


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginDetailViewTest(TestCase):
    def test_view_detail_anonymous(self):
        # Make the request as an unauthenticated user
        self.client.logout()
        response = self.client.get(reverse("plugins:plugin_detail", kwargs={"plugin": "example_plugin"}))
        # Redirects to the login page
        self.assertHttpStatus(response, 302)

    def test_view_detail_authenticated(self):
        response = self.client.get(reverse("plugins:plugin_detail", kwargs={"plugin": "example_plugin"}))
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))
        # plugin verbose name
        self.assertIn("Example Nautobot App", response_body, msg=response_body)
        # plugin description
        self.assertIn("For testing purposes only", response_body, msg=response_body)


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginAPITest(APIViewTestCases.APIViewTestCase):
    model = ExampleModel
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
        # Example objects to test.
        ExampleModel.objects.create(name="Example 1", number=1)
        ExampleModel.objects.create(name="Example 2", number=2)
        ExampleModel.objects.create(name="Example 3", number=3)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_api_urls(self):
        # Test list URL resolution
        list_url = reverse("plugins-api:example_plugin-api:examplemodel-list")
        self.assertEqual(list_url, self._get_list_url())

        # Test detail URL resolution
        instance = ExampleModel.objects.first()
        detail_url = reverse("plugins-api:example_plugin-api:examplemodel-detail", kwargs={"pk": instance.pk})
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


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginCustomValidationTest(TestCase):
    def setUp(self):
        # When creating a fresh test DB, wrapping model clean methods fails, which is normal.
        # This always occurs during the first run of migrations, however, During testing we
        # must manually call the method again to actually perform the action, now that the
        # ContentType table has been created.
        wrap_model_clean_methods()

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


class FilterExtensionTest(TestCase):
    """
    Tests for adding filter extensions
    """

    queryset = Tenant.objects.all()
    filterset = TenantFilterSet

    @classmethod
    def setUpTestData(cls):
        tenant_groups = TenantGroup.objects.all()[:3]
        tenants = (
            Tenant.objects.create(name="Tenant 1", tenant_group=tenant_groups[0], description="tenant-1.nautobot.com"),
            Tenant.objects.create(name="Tenant 2", tenant_group=tenant_groups[1], description="tenant-2.nautobot.com"),
            Tenant.objects.create(name="Tenant 3", tenant_group=tenant_groups[2], description="tenant-3.nautobot.com"),
        )
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
        params = {"example_plugin_description": ["tenant-1.nautobot.com"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_added_lookup(self):
        """
        Test that the dynamically created filters work on plugin created filters as well.
        """
        params = {"example_plugin_description__ic": ["tenant-1.nautobot"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_nested_lookup(self):
        """
        Test that filters work against nested filters.
        """
        params = {"example_plugin_dtype": ["Model 1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"example_plugin_dtype": ["Model 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_filter_method_param(self):
        """
        Test that a custom filter works if a valid callable `method` is provided.
        """
        params = {"example_plugin_sdescrip": ["tenant-1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_filter_form(self):
        """
        Test that filter forms work when added via a plugin.
        """
        form = TenantFilterForm(
            data={
                "example_plugin_description": "tenant-1.nautobot.com",
                "example_plugin_dtype": "model-1",
                "example_plugin_sdescrip": "tenant-1",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertIn("example_plugin_description", form.fields.keys())


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

        # Move to the example plugin. No errors should be raised (which is good).
        plugin_name = "example_plugin"
        load_plugin(plugin_name, settings)


class TestPluginCoreViewOverrides(TestCase):
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
        response = self.client.get(reverse("plugins:example_plugin:view_to_be_overridden"))
        self.assertEqual(b"Hello world! I'm an overridden view.", response.content)

        response = self.client.get(
            f'{reverse("plugins:plugin_detail", kwargs={"plugin": "example_plugin_with_view_override"})}'
        )
        self.assertIn(
            (
                b"plugins:example_plugin:view_to_be_overridden <code>"
                b"example_plugin_with_view_override.views.ViewOverride</code>"
            ),
            response.content,
        )
