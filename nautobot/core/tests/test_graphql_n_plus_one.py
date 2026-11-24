"""N+1 detection for GraphQL nested filtered relations.

Auto-discovers every filterable nested list field in the built GraphQL schema and verifies that
applying a filter does not produce a query-count explosion proportional to the number of parent objects.
"""

from collections import defaultdict
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.test.client import RequestFactory
from graphene_django.settings import graphene_settings
from graphql import execute, parse
from graphql.type import (
    is_list_type,
    is_non_null_type,
    is_object_type,
)

from nautobot.core.testing import AssertNoRepeatedQueries, TestCase
from nautobot.data_validation.models import DataCompliance
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Controller, Device, DeviceType, Interface, Location, Manufacturer, Module
from nautobot.extras.models import Role, Status, Tag
from nautobot.ipam.models import IPAddress

User = get_user_model()


def _unwrap_type(gql_type):
    """Strip NonNull / List wrappers and return (is_list, named_type)."""
    is_list = False
    t = gql_type
    while True:
        if is_non_null_type(t):
            t = t.of_type
        elif is_list_type(t):
            is_list = True
            t = t.of_type
        else:
            break
    return is_list, t


def _pick_string_filter_arg(gql_field):
    """Return the name of a usable string-type filter arg on *gql_field*, or ``None``.

    Prefers ``name`` because virtually every Nautobot model exposes it as a
    simple string / ``[String]`` filter.
    """
    skip = {"limit", "offset"}
    best = None
    for arg_name, arg in gql_field.args.items():
        if arg_name in skip:
            continue
        _, inner = _unwrap_type(arg.type)
        type_name = getattr(inner, "name", None)
        if type_name != "String":
            continue
        if arg_name == "name":
            return "name"
        if best is None:
            best = arg_name
    return best


def discover_filterable_nested_list_fields(schema):
    """Walk the schema and return ``[(parent_field, nested_field, filter_arg), ...]``.

    Each tuple represents a top-level list query field (e.g. ``devices``) that contains a nested
    list field (e.g. ``interfaces``) accepting at least one string-typed filter argument.
    """
    results = []
    query_type = schema.query_type

    for parent_name, parent_field in query_type.fields.items():
        parent_is_list, parent_named = _unwrap_type(parent_field.type)
        if not parent_is_list or not is_object_type(parent_named):
            continue

        for nested_name, nested_field in parent_named.fields.items():
            nested_is_list, nested_named = _unwrap_type(nested_field.type)
            if not nested_is_list or not is_object_type(nested_named):
                continue
            if not nested_field.args:
                continue

            filter_arg = _pick_string_filter_arg(nested_field)
            if filter_arg:
                results.append((parent_name, nested_name, filter_arg))

    return results


def discover_filterable_nested_list_fields_by_app(schema):
    """Group the results of `discover_filterable_nested_list_fields()` by the app label of each parent field's model."""
    cases_by_app = defaultdict(list)
    for parent_name, nested_name, filter_arg in discover_filterable_nested_list_fields(schema):
        _, parent_named = _unwrap_type(schema.query_type.fields[parent_name].type)
        app_label = parent_named.graphene_type._meta.model._meta.app_label
        cases_by_app[app_label].append((parent_name, nested_name, filter_arg))
    return cases_by_app


N_PLUS_ONE_THRESHOLD = 10


class GraphQLNPlusOneTestMixin:
    """Auto-discovers the filterable nested list fields of one app's models and asserts none produce N+1 queries.

    There is one test class per app, rather than one test for the whole schema, so that the parallel test runner can
    spread the work across processes.
    """

    app_label = None

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="n_plus_one_test_user", is_active=True, is_superuser=True)

    def setUp(self):
        super().setUp()
        self.schema = graphene_settings.SCHEMA.graphql_schema

    def _execute(self, query):
        """Execute a GraphQL query with a **fresh** request context (empty filter cache)."""
        request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        request.id = uuid.uuid4()
        request.user = self.user
        return execute(schema=self.schema, document=parse(query), context_value=request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_no_n_plus_one_on_filtered_nested_relations(self):
        """For every nested list field that accepts a string filter, verify no N+1 pattern occurs."""
        cases = discover_filterable_nested_list_fields_by_app(self.schema)[self.app_label]
        self.assertGreater(
            len(cases), 0, f"Schema introspection found no filterable nested list fields for `{self.app_label}`"
        )

        # Single prewarm run to populate internal caches (ContentType, Relationship, etc.)
        first_parent, first_nested, first_arg = cases[0]
        self._execute(f'{{ {first_parent} {{ {first_nested}({first_arg}: "__prewarm__") {{ id }} }} }}')

        for parent_name, nested_name, filter_arg in cases:
            with self.subTest(parent=parent_name, nested=nested_name, filter=filter_arg):
                query = f'{{ {parent_name} {{ {nested_name}({filter_arg}: "__n_plus_one_test__") {{ id }} }} }}'

                # Prewarm this specific query path
                self._execute(query)

                # Measured run with fresh request context
                with AssertNoRepeatedQueries(self, threshold=N_PLUS_ONE_THRESHOLD):
                    result = self._execute(query)

                # The query should execute without hard errors (GraphQL filter-validation
                # errors are acceptable since we pass a dummy value).
                if result.errors:
                    for err in result.errors:
                        if not isinstance(err.original_error, Exception):
                            self.fail(f"Unexpected hard error for {parent_name}.{nested_name}: {err}")


class CircuitsGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "circuits"


class CloudGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "cloud"


class ContentTypesGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "contenttypes"


class DataValidationGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "data_validation"


class DCIMGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "dcim"


class ExampleAppGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "example_app"


class ExtrasGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "extras"


class IPAMGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "ipam"


class LoadBalancersGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "load_balancers"


class TenancyGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "tenancy"


class VirtualizationGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "virtualization"


class VPNGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "vpn"


class WirelessGraphQLNPlusOneTest(GraphQLNPlusOneTestMixin, TestCase):
    app_label = "wireless"


class GraphQLNPlusOneCoverageTest(TestCase):
    def test_every_app_with_filterable_nested_list_fields_has_a_test_class(self):
        tested_app_labels = {test_class.app_label for test_class in GraphQLNPlusOneTestMixin.__subclasses__()}
        app_labels = set(discover_filterable_nested_list_fields_by_app(graphene_settings.SCHEMA.graphql_schema))
        self.assertEqual(
            app_labels - tested_app_labels, set(), "Add a `GraphQLNPlusOneTestMixin` test class for each of these apps"
        )


class GraphQLTagsAndConfigContextNPlusOneTest(TestCase):
    """Regression tests for N+1 query patterns on the `tags` and `config_context` resolvers (issue #9015).

    These resolvers are added dynamically and are not "filterable nested list fields", so they are not covered
    by the `GraphQLNPlusOneTestMixin` tests above.
    """

    DEVICE_COUNT = 15

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="n_plus_one_tags_test_user", is_active=True, is_superuser=True)

        # Make the device list deterministic by removing pre-existing fixture objects that reference devices.
        IPAddress.objects.all().delete()
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        Module.objects.all().delete()

        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="n+1 test device_type")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type__name="Campus").first()
        interface_status = Status.objects.get_for_model(Interface).first()

        interface_tag = Tag.objects.create(name="n+1 test interface tag")
        interface_tag.content_types.add(ContentType.objects.get_for_model(Interface))

        # One tagged interface per device. With DEVICE_COUNT > threshold, an un-prefetched `tags` resolver
        # issues one extras_tag query per interface, and an un-annotated `config_context` resolver issues one
        # extras_configcontext query per device - both detectable as N+1.
        for i in range(cls.DEVICE_COUNT):
            device = Device.objects.create(
                name=f"n+1-device-{i}",
                device_type=device_type,
                role=device_role,
                location=location,
                status=device_status,
            )
            interface = Interface.objects.create(
                device=device,
                name="Vlan4094",
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=interface_status,
            )
            interface.tags.add(interface_tag)

    def setUp(self):
        super().setUp()
        self.schema = graphene_settings.SCHEMA.graphql_schema

    def _execute(self, query):
        """Execute a GraphQL query with a fresh request context (empty filter cache)."""
        request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        request.id = uuid.uuid4()
        request.user = self.user
        return execute(schema=self.schema, document=parse(query), context_value=request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_no_n_plus_one_on_nested_tags(self):
        """`{ devices { interfaces { tags } } }` must prefetch tags rather than query per interface."""
        query = "{ devices { interfaces { tags { name } } } }"
        self._execute(query)  # Prewarm caches (ContentType, etc.)
        with AssertNoRepeatedQueries(self, threshold=N_PLUS_ONE_THRESHOLD):
            result = self._execute(query)
        self.assertFalse(result.errors, msg=str(result.errors))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_no_n_plus_one_on_config_context(self):
        """`{ devices { config_context } }` must annotate config context rather than query per device."""
        query = "{ devices { config_context } }"
        self._execute(query)  # Prewarm caches (ContentType, etc.)
        with AssertNoRepeatedQueries(self, threshold=N_PLUS_ONE_THRESHOLD):
            result = self._execute(query)
        self.assertFalse(result.errors, msg=str(result.errors))


class GraphQLGenericRelationNPlusOneTest(TestCase):
    """Regression test for N+1 query patterns on nested generic relations, independent of fixture data.

    The `GraphQLNPlusOneTestMixin` tests only detect an N+1 on a generic relation when the fixtures happen to contain
    related objects for enough parents, which most generic relations (contacts, data compliance, ...) do not.
    """

    MANUFACTURER_COUNT = 15

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="n_plus_one_generic_test_user", is_active=True, is_superuser=True)

        manufacturer_ct = ContentType.objects.get_for_model(Manufacturer)
        for i in range(cls.MANUFACTURER_COUNT):
            manufacturer = Manufacturer.objects.create(name=f"n+1 generic relation manufacturer {i}")
            DataCompliance.objects.create(
                compliance_class_name="NPlusOneComplianceRule",
                content_type=manufacturer_ct,
                object_id=manufacturer.pk,
                valid=True,
            )

    def setUp(self):
        super().setUp()
        self.schema = graphene_settings.SCHEMA.graphql_schema

    def _execute(self, query):
        """Execute a GraphQL query with a fresh request context (empty filter cache)."""
        request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        request.id = uuid.uuid4()
        request.user = self.user
        return execute(schema=self.schema, document=parse(query), context_value=request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_no_n_plus_one_on_nested_generic_relation(self):
        """`{ manufacturers { associated_data_compliance { id } } }` must prefetch rather than query per object."""
        query = "{ manufacturers { associated_data_compliance { id } } }"
        self._execute(query)  # Prewarm caches (ContentType, etc.)
        with AssertNoRepeatedQueries(self, threshold=N_PLUS_ONE_THRESHOLD):
            result = self._execute(query)
        self.assertFalse(result.errors, msg=str(result.errors))
