from unittest import mock
import uuid

from django import forms as django_forms
from django.apps import apps
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import QueryDict

from nautobot.circuits import models as circuits_models
from nautobot.core import exceptions, forms, settings_funcs
from nautobot.core.api import utils as api_utils
from nautobot.core.forms.utils import compress_range
from nautobot.core.models import fields as core_fields, utils as models_utils, validators
from nautobot.core.testing import TestCase
from nautobot.core.utils import data as data_utils, filtering, lookup, querysets, requests
from nautobot.core.utils.migrations import update_object_change_ct_for_replaced_models
from nautobot.dcim import filters as dcim_filters, forms as dcim_forms, models as dcim_models, tables
from nautobot.extras import models as extras_models, utils as extras_utils
from nautobot.extras.choices import ObjectChangeActionChoices, RelationshipTypeChoices
from nautobot.extras.filters import StatusFilterSet
from nautobot.extras.forms import StatusForm
from nautobot.extras.models import ObjectChange
from nautobot.ipam import models as ipam_models

from example_app.models import ExampleModel


class DictToFilterParamsTest(TestCase):
    """
    Validate the operation of dict_to_filter_params().
    """

    def test_dict_to_filter_params(self):
        input_ = {
            "a": True,
            "foo": {
                "bar": 123,
                "baz": 456,
            },
            "x": {"y": {"z": False}},
        }

        output = {
            "a": True,
            "foo__bar": 123,
            "foo__baz": 456,
            "x__y__z": False,
        }

        self.assertEqual(api_utils.dict_to_filter_params(input_), output)

        input_["x"]["y"]["z"] = True

        self.assertNotEqual(api_utils.dict_to_filter_params(input_), output)


class NormalizeQueryDictTest(TestCase):
    """
    Validate normalize_querydict() utility function.
    """

    def test_normalize_querydict(self):
        self.assertDictEqual(
            requests.normalize_querydict(QueryDict("foo=1&bar=2&bar=3&baz=")),
            {"foo": "1", "bar": ["2", "3"], "baz": ""},
        )

        self.assertDictEqual(
            requests.normalize_querydict(QueryDict("name=Sample Status&content_types=1"), form_class=StatusForm),
            {"name": "Sample Status", "content_types": ["1"]},
        )

        self.assertDictEqual(
            requests.normalize_querydict(
                QueryDict("name=Sample Status&content_types=dcim.device"), filterset=StatusFilterSet()
            ),
            {"name": ["Sample Status"], "content_types": ["dcim.device"]},
        )


class DeepMergeTest(TestCase):
    """
    Validate the behavior of the deepmerge() utility.
    """

    def test_deepmerge(self):
        dict1 = {
            "active": True,
            "foo": 123,
            "fruits": {
                "orange": 1,
                "apple": 2,
                "pear": 3,
            },
            "vegetables": None,
            "dairy": {
                "milk": 1,
                "cheese": 2,
            },
            "deepnesting": {
                "foo": {
                    "a": 10,
                    "b": 20,
                    "c": 30,
                },
            },
        }

        dict2 = {
            "active": False,
            "bar": 456,
            "fruits": {
                "banana": 4,
                "grape": 5,
            },
            "vegetables": {
                "celery": 1,
                "carrots": 2,
                "corn": 3,
            },
            "dairy": None,
            "deepnesting": {
                "foo": {
                    "a": 100,
                    "d": 40,
                },
            },
        }

        merged = {
            "active": False,
            "foo": 123,
            "bar": 456,
            "fruits": {
                "orange": 1,
                "apple": 2,
                "pear": 3,
                "banana": 4,
                "grape": 5,
            },
            "vegetables": {
                "celery": 1,
                "carrots": 2,
                "corn": 3,
            },
            "dairy": None,
            "deepnesting": {
                "foo": {
                    "a": 100,
                    "b": 20,
                    "c": 30,
                    "d": 40,
                },
            },
        }

        self.assertEqual(data_utils.deepmerge(dict1, dict2), merged)


class FlattenIterableTest(TestCase):
    """Tests for the `flatten_iterable()` function."""

    def test_list_of_lists(self):
        items = [[1, 2, 3], [4, 5], 6]
        expected = [1, 2, 3, 4, 5, 6]
        self.assertEqual(list(data_utils.flatten_iterable(items)), expected)

    def test_list_of_strings(self):
        items = ["foo", ["bar"], ["baz"]]
        expected = ["foo", "bar", "baz"]
        self.assertEqual(list(data_utils.flatten_iterable(items)), expected)


class GetFooForModelTest(TestCase):
    """Tests for the various `get_foo_for_model()` functions."""

    def test_get_filterset_for_model(self):
        """
        Test that `get_filterset_for_model` returns the right FilterSet for various inputs.
        """
        self.assertEqual(lookup.get_filterset_for_model("dcim.device"), dcim_filters.DeviceFilterSet)
        self.assertEqual(lookup.get_filterset_for_model(dcim_models.Device), dcim_filters.DeviceFilterSet)
        self.assertEqual(lookup.get_filterset_for_model("dcim.location"), dcim_filters.LocationFilterSet)
        self.assertEqual(lookup.get_filterset_for_model(dcim_models.Location), dcim_filters.LocationFilterSet)

    def test_get_form_for_model(self):
        """
        Test that `get_form_for_model` returns the right Form for various inputs.
        """
        self.assertEqual(lookup.get_form_for_model("dcim.device", "Filter"), dcim_forms.DeviceFilterForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Device, "Filter"), dcim_forms.DeviceFilterForm)
        self.assertEqual(lookup.get_form_for_model("dcim.location", "Filter"), dcim_forms.LocationFilterForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Location, "Filter"), dcim_forms.LocationFilterForm)
        self.assertEqual(lookup.get_form_for_model("dcim.device"), dcim_forms.DeviceForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Device), dcim_forms.DeviceForm)
        self.assertEqual(lookup.get_form_for_model("dcim.location"), dcim_forms.LocationForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Location), dcim_forms.LocationForm)

    def test_get_related_field_for_models(self):
        """
        Test that `get_related_field_for_models` returns the appropriate field for various inputs.
        """
        # No direct relation found
        self.assertIsNone(lookup.get_related_field_for_models(dcim_models.Device, dcim_models.LocationType))
        # ForeignKey and reverse
        self.assertEqual(lookup.get_related_field_for_models(dcim_models.Device, dcim_models.Location).name, "location")
        self.assertEqual(lookup.get_related_field_for_models(dcim_models.Location, dcim_models.Device).name, "devices")
        # ManyToMany and reverse
        self.assertEqual(
            lookup.get_related_field_for_models(ipam_models.Prefix, dcim_models.Location).name, "locations"
        )
        self.assertEqual(lookup.get_related_field_for_models(dcim_models.Location, ipam_models.Prefix).name, "prefixes")
        # Multiple candidate fields
        with self.assertRaises(AttributeError):
            # both primary_ip4 and primary_ip6 are candidates
            lookup.get_related_field_for_models(dcim_models.Device, ipam_models.IPAddress)

    def test_get_route_for_model(self):
        """
        Test that `get_route_for_model` returns the appropriate URL route name for various inputs.
        """
        # UI
        self.assertEqual(lookup.get_route_for_model("dcim.device", "list"), "dcim:device_list")
        self.assertEqual(lookup.get_route_for_model(dcim_models.Device, "list"), "dcim:device_list")
        self.assertEqual(lookup.get_route_for_model("dcim.location", "list"), "dcim:location_list")
        self.assertEqual(lookup.get_route_for_model(dcim_models.Location, "list"), "dcim:location_list")
        self.assertEqual(
            lookup.get_route_for_model("example_app.examplemodel", "list"),
            "plugins:example_app:examplemodel_list",
        )
        self.assertEqual(lookup.get_route_for_model(ExampleModel, "list"), "plugins:example_app:examplemodel_list")

        # API
        self.assertEqual(lookup.get_route_for_model("dcim.device", "list", api=True), "dcim-api:device-list")
        self.assertEqual(lookup.get_route_for_model(dcim_models.Device, "list", api=True), "dcim-api:device-list")
        self.assertEqual(lookup.get_route_for_model("dcim.location", "detail", api=True), "dcim-api:location-detail")
        self.assertEqual(lookup.get_route_for_model(ContentType, "list", api=True), "extras-api:contenttype-list")
        self.assertEqual(lookup.get_route_for_model(ContentType, "detail", api=True), "extras-api:contenttype-detail")
        self.assertEqual(lookup.get_route_for_model(Group, "list", api=True), "users-api:group-list")
        self.assertEqual(lookup.get_route_for_model(Group, "detail", api=True), "users-api:group-detail")
        self.assertEqual(
            lookup.get_route_for_model(dcim_models.Location, "detail", api=True), "dcim-api:location-detail"
        )
        self.assertEqual(
            lookup.get_route_for_model("example_app.examplemodel", "list", api=True),
            "plugins-api:example_app-api:examplemodel-list",
        )
        self.assertEqual(
            lookup.get_route_for_model(ExampleModel, "list", api=True),
            "plugins-api:example_app-api:examplemodel-list",
        )

    def test_get_table_for_model(self):
        """
        Test that `get_table_for_model` returns the appropriate Table for various inputs.
        """
        self.assertEqual(lookup.get_table_for_model("dcim.device"), tables.DeviceTable)
        self.assertEqual(lookup.get_table_for_model(dcim_models.Device), tables.DeviceTable)
        self.assertEqual(lookup.get_table_for_model("dcim.location"), tables.LocationTable)
        self.assertEqual(lookup.get_table_for_model(dcim_models.Location), tables.LocationTable)

    def test_get_model_from_name(self):
        """
        Test the util function `get_model_from_name` returns the appropriate Model, if the dotted name provided.
        """
        self.assertEqual(lookup.get_model_from_name("dcim.device"), dcim_models.Device)
        self.assertEqual(lookup.get_model_from_name("dcim.location"), dcim_models.Location)

    def test_get_model_for_view_name(self):
        """
        Test that `get_model_for_view_name` returns the appropriate Model, if the colon separated view name provided.
        """
        with self.subTest("Test core UI view."):
            self.assertEqual(lookup.get_model_for_view_name("dcim:device_list"), dcim_models.Device)
            self.assertEqual(lookup.get_model_for_view_name("dcim:device"), dcim_models.Device)
        with self.subTest("Test app UI view."):
            self.assertEqual(lookup.get_model_for_view_name("plugins:example_app:examplemodel_list"), ExampleModel)
            self.assertEqual(lookup.get_model_for_view_name("plugins:example_app:examplemodel"), ExampleModel)
        with self.subTest("Test core API view."):
            self.assertEqual(lookup.get_model_for_view_name("dcim-api:device-list"), dcim_models.Device)
            self.assertEqual(lookup.get_model_for_view_name("dcim-api:device-detail"), dcim_models.Device)
        with self.subTest("Test app API view."):
            self.assertEqual(
                lookup.get_model_for_view_name("plugins-api:example_app-api:examplemodel-detail"), ExampleModel
            )
            self.assertEqual(
                lookup.get_model_for_view_name("plugins-api:example_app-api:examplemodel-list"), ExampleModel
            )
        with self.subTest("Test unconventional model views."):
            self.assertEqual(lookup.get_model_for_view_name("extras-api:contenttype-detail"), ContentType)
            self.assertEqual(lookup.get_model_for_view_name("users-api:group-detail"), Group)
        with self.subTest("Test unexpected view."):
            with self.assertRaises(ValueError) as err:
                lookup.get_model_for_view_name("unknown:plugins:example_app:examplemodel_list")
            self.assertEqual(str(err.exception), "Unexpected View Name: unknown:plugins:example_app:examplemodel_list")

    def test_get_table_class_string_from_view_name(self):
        # Testing UIViewSet
        self.assertEqual(lookup.get_table_class_string_from_view_name("circuits:circuit_list"), "CircuitTable")
        # Testing Legacy View
        self.assertEqual(lookup.get_table_class_string_from_view_name("dcim:location_list"), "LocationTable")
        # Testing unconventional table name
        self.assertEqual(lookup.get_table_class_string_from_view_name("ipam:prefix_list"), "PrefixDetailTable")


class IsTaggableTest(TestCase):
    def test_is_taggable_true(self):
        # Classes
        self.assertTrue(models_utils.is_taggable(dcim_models.Location))
        self.assertTrue(models_utils.is_taggable(dcim_models.Device))

        # Instances
        self.assertTrue(models_utils.is_taggable(dcim_models.Location(name="Test Location")))

    def test_is_taggable_false(self):
        class FakeOut:
            tags = "Nope!"

        # Classes
        self.assertFalse(models_utils.is_taggable(dcim_models.Manufacturer))
        self.assertFalse(models_utils.is_taggable(FakeOut))

        # Instances
        self.assertFalse(models_utils.is_taggable(dcim_models.Manufacturer(name="Test Manufacturer")))
        self.assertFalse(models_utils.is_taggable(FakeOut()))

        self.assertFalse(models_utils.is_taggable(None))


class IsTruthyTest(TestCase):
    def test_is_truthy(self):
        self.assertTrue(settings_funcs.is_truthy("true"))
        self.assertTrue(settings_funcs.is_truthy("True"))
        self.assertTrue(settings_funcs.is_truthy(True))
        self.assertTrue(settings_funcs.is_truthy("yes"))
        self.assertTrue(settings_funcs.is_truthy("on"))
        self.assertTrue(settings_funcs.is_truthy("y"))
        self.assertTrue(settings_funcs.is_truthy("1"))
        self.assertTrue(settings_funcs.is_truthy(1))

        self.assertFalse(settings_funcs.is_truthy("false"))
        self.assertFalse(settings_funcs.is_truthy("False"))
        self.assertFalse(settings_funcs.is_truthy(False))
        self.assertFalse(settings_funcs.is_truthy("no"))
        self.assertFalse(settings_funcs.is_truthy("n"))
        self.assertFalse(settings_funcs.is_truthy(0))
        self.assertFalse(settings_funcs.is_truthy("0"))


class PrettyPrintQueryTest(TestCase):
    """Tests for `pretty_print_query()."""

    def test_pretty_print_query(self):
        """Test that each Q object, from deeply nested to flat, pretty prints as expected."""
        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        queries = [
            ((Q(location__name="ams01") | Q(location__name="ang01")) & ~Q(status__name="Active"))
            | Q(status__name="Planned"),
            (Q(location__name="ams01") | Q(location__name="ang01")) & ~Q(status__name="Active"),
            Q(location__name="ams01") | Q(location__name="ang01"),
            Q(location__name="ang01") & ~Q(status__name="Active"),
            Q(location__name="ams01", status__name="Planned"),
            Q(location__name="ang01"),
            Q(status__id=12345),
            Q(location__name__in=["ams01", "ang01"]),
        ]
        # pylint: enable=unsupported-binary-operation
        results = [
            """\
(
  (
    (
      location__name='ams01' OR location__name='ang01'
    ) AND (
      NOT (status__name='Active')
    )
  ) OR status__name='Planned'
)""",
            """\
(
  (
    location__name='ams01' OR location__name='ang01'
  ) AND (
    NOT (status__name='Active')
  )
)""",
            """\
(
  location__name='ams01' OR location__name='ang01'
)""",
            """\
(
  location__name='ang01' AND (
    NOT (status__name='Active')
  )
)""",
            """\
(
  location__name='ams01' AND status__name='Planned'
)""",
            """\
(
  location__name='ang01'
)""",
            """\
(
  status__id=12345
)""",
            """\
(
  location__name__in=['ams01', 'ang01']
)""",
        ]

        tests = zip(queries, results)

        for query, expected in tests:
            with self.subTest(query=query):
                self.assertEqual(models_utils.pretty_print_query(query), expected)


class CompressRangeTest(TestCase):
    """Tests for compress_range()."""

    def test_compress_range_sparse(self):
        values = [1500, 200, 10, 2222, 3000, 4096]
        self.assertEqual(
            list(compress_range(values)),
            [
                (10, 10),
                (200, 200),
                (1500, 1500),
                (2222, 2222),
                (3000, 3000),
                (4096, 4096),
            ],
        )

    def test_compress_range_dense(self):
        values = [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            100,
            101,
            102,
            103,
            104,
            105,
            1100,
            1101,
            1102,
            1103,
            1104,
            1105,
            1106,
        ]
        self.assertEqual(
            list(compress_range(values)),
            [(1, 10), (100, 105), (1100, 1106)],
        )

    def test_compress_range_complex(self):
        values = [
            10,
            11,
            12,
            13,
            14,
            15,
            100,
            200,
            210,
            211,
            212,
            222,
            500,
            501,
            502,
            503,
            600,
        ]
        self.assertEqual(
            list(compress_range(values)),
            [
                (10, 15),
                (100, 100),
                (200, 200),
                (210, 212),
                (222, 222),
                (500, 503),
                (600, 600),
            ],
        )


class SlugifyFunctionsTest(TestCase):
    """Test custom slugify functions."""

    def test_slugify_dots_to_dashes(self):
        for content, expected in (
            ("Hello.World", "hello-world"),
            ("apps.my_app.jobs", "apps-my_app-jobs"),
            ("Lots of . spaces  ... and such", "lots-of-spaces-and-such"),
        ):
            self.assertEqual(core_fields.slugify_dots_to_dashes(content), expected)

    def test_slugify_dashes_to_underscores(self):
        for content, expected in (
            ("Locations / Regions", "locations_regions"),
            ("alpha-beta_gamma delta", "alpha_beta_gamma_delta"),
            ("123 main st", "a123_main_st"),
            (" 123 main st", "a_123_main_st"),
        ):
            self.assertEqual(core_fields.slugify_dashes_to_underscores(content), expected)


class LaxURLFieldTest(TestCase):
    """Test LaxURLField and related functionality."""

    VALID_URLS = [
        "http://example.com",
        "https://local-dns/foo/bar.git",  # not supported out-of-the-box by Django, hence our custom classes
        "https://1.1.1.1:8080/",
        "https://[2001:db8::]/",
    ]
    INVALID_URLS = [
        "unknown://example.com/",
        "foo:/",
        "http://file://",
    ]

    def test_enhanced_url_validator(self):
        for valid in self.VALID_URLS:
            with self.subTest(valid=valid):
                validators.EnhancedURLValidator()(valid)

        for invalid in self.INVALID_URLS:
            with self.subTest(invalid=invalid):
                with self.assertRaises(django_forms.ValidationError):
                    validators.EnhancedURLValidator()(invalid)

    def test_forms_lax_url_field(self):
        for valid in self.VALID_URLS:
            with self.subTest(valid=valid):
                forms.LaxURLField().clean(valid)

        for invalid in self.INVALID_URLS:
            with self.subTest(invalid=invalid):
                with self.assertRaises(django_forms.ValidationError):
                    forms.LaxURLField().clean(invalid)

    def test_models_lax_url_field(self):
        for valid in self.VALID_URLS:
            with self.subTest(valid=valid):
                core_fields.LaxURLField().run_validators(valid)

        for invalid in self.INVALID_URLS:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    core_fields.LaxURLField().run_validators(invalid)


class LookupRelatedFunctionTest(TestCase):
    def test_is_single_choice_field(self):
        """
        Assert that is_single_choice_field() correctly distinguishes between single-value and multi-value filter fields.
        """
        location_filterset = dcim_filters.LocationFilterSet()

        single_choice_fields = ("has_vlans", "has_clusters")
        for field in single_choice_fields:
            with self.subTest(f"Single choice field: {field}"):
                self.assertTrue(requests.is_single_choice_field(location_filterset, field))

        multi_choice_fields = ("created", "status", "tenant", "tags")
        for field in multi_choice_fields:
            with self.subTest(f"Multi choice field: {field}"):
                self.assertFalse(requests.is_single_choice_field(location_filterset, field))

    def test_build_lookup_label(self):
        with self.subTest():
            label = filtering.build_lookup_label("name__iew", "iendswith")
            self.assertEqual(label, "ends with (iew)")

        with self.subTest("Test negation"):
            label = filtering.build_lookup_label("name__niew", "iendswith")
            self.assertEqual(label, "not ends with (niew)")

        with self.subTest("Test for exact: without a lookup expr"):
            label = filtering.build_lookup_label("name", "exact")
            self.assertEqual(label, "exact")

    def test_get_all_lookup_expr_for_field(self):
        with self.subTest():
            lookup_expr = filtering.get_all_lookup_expr_for_field(dcim_models.Location, "status")
            self.assertEqual(
                lookup_expr,
                [{"id": "status", "name": "exact"}, {"id": "status__n", "name": "not exact (n)"}],
            )

        with self.subTest("Test field with has_ prefix"):
            lookup_expr = filtering.get_all_lookup_expr_for_field(dcim_models.Location, "has_vlans")
            self.assertEqual(
                lookup_expr,
                [{"id": "has_vlans", "name": "exact"}],
            )

        with self.subTest("Test unknown field"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                filtering.get_all_lookup_expr_for_field(dcim_models.Location, "unknown_field")
            self.assertEqual(str(err.exception), "field_name not found")

    def test_get_filterset_field(self):
        location_filterset = dcim_filters.LocationFilterSet()
        with self.subTest():
            field = filtering.get_filterset_field(location_filterset, "name")
            self.assertEqual(field.__class__, location_filterset.filters.get("name").__class__)

        with self.subTest("Test invalid field"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                filtering.get_filterset_field(location_filterset, "unknown")
            self.assertEqual(str(err.exception), "unknown is not a valid LocationFilterSet field")

    def test_get_filterset_parameter_form_field(self):
        with self.subTest("Test get CharFields"):
            location_fields = ["comments", "name", "contact_email", "physical_address", "shipping_address"]
            for field_name in location_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, field_name)
                self.assertIsInstance(form_field, forms.MultiValueCharField)

            device_fields = ["serial", "name"]
            for field_name in device_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, forms.MultiValueCharField)

        with self.subTest("Test IntegerField"):
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, "asn")
            self.assertIsInstance(form_field, django_forms.IntegerField)

            device_fields = ["vc_position", "vc_priority"]
            for field_name in device_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, django_forms.IntegerField)

        with self.subTest("Test DynamicModelMultipleChoiceField"):
            location_fields = ["tenant", "status"]
            for field_name in location_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, field_name)
                self.assertIsInstance(form_field, forms.DynamicModelMultipleChoiceField)

            device_fields = ["cluster", "device_type", "location"]
            for field_name in device_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, forms.DynamicModelMultipleChoiceField)

            location_fields = ["has_circuit_terminations", "has_devices"]
            for field_name in location_fields:
                with self.subTest("Test ChoiceField", model=dcim_models.Location, field_name=field_name):
                    form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, field_name)
                    self.assertIsInstance(form_field, django_forms.ChoiceField)
                    self.assertIsInstance(form_field.widget, forms.StaticSelect2)

            device_fields = ["has_console_ports", "has_interfaces", "local_config_context_data"]
            for field_name in device_fields:
                with self.subTest("Test ChoiceField", model=dcim_models.Device, field_name=field_name):
                    form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                    self.assertIsInstance(form_field, django_forms.ChoiceField)
                    self.assertIsInstance(form_field.widget, forms.StaticSelect2)

        with self.subTest("Test MultipleChoiceField"):
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, "face")
            self.assertIsInstance(form_field, django_forms.MultipleChoiceField)

        with self.subTest("Test DateTimePicker"):
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, "last_updated")
            self.assertIsInstance(form_field.widget, forms.DateTimePicker)

            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, "last_updated")
            self.assertIsInstance(form_field.widget, forms.DateTimePicker)

        with self.subTest("Test DatePicker"):
            form_field = filtering.get_filterset_parameter_form_field(circuits_models.Circuit, "install_date")
            self.assertIsInstance(form_field.widget, forms.DatePicker)

        with self.subTest("Test Invalid parameter"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                filtering.get_filterset_parameter_form_field(dcim_models.Location, "unknown")
            self.assertEqual(str(err.exception), "unknown is not a valid LocationFilterSet field")

        with self.subTest("Test Content types"):
            form_field = filtering.get_filterset_parameter_form_field(extras_models.Status, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)

            # Assert total ContentTypes generated by form_field is == total `content_types` generated by TaggableClassesQuery
            form_field = filtering.get_filterset_parameter_form_field(extras_models.Tag, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)
            self.assertQuerysetEqualAndNotEmpty(form_field.queryset, extras_utils.TaggableClassesQuery().as_queryset())

            form_field = filtering.get_filterset_parameter_form_field(extras_models.JobHook, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)
            self.assertQuerysetEqualAndNotEmpty(
                form_field.queryset, extras_utils.ChangeLoggedModelsQuery().as_queryset()
            )

            form_field = filtering.get_filterset_parameter_form_field(
                extras_models.ObjectMetadata, "assigned_object_type"
            )
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)
            self.assertQuerysetEqualAndNotEmpty(
                form_field.queryset,
                ContentType.objects.filter(extras_utils.FeatureQuery("metadata").get_query()).order_by(
                    "app_label", "model"
                ),
            )

        with self.subTest("Test prefers_id"):
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, "location")
            self.assertEqual("id", form_field.to_field_name)
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, "vlans")
            self.assertEqual("id", form_field.to_field_name)
            # Test prefers_id=False (default)
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, "racks")
            self.assertEqual("name", form_field.to_field_name)

    def test_convert_querydict_to_factory_formset_dict(self):
        location_filter_set = dcim_filters.LocationFilterSet()

        with self.subTest("Convert QueryDict to an acceptable factory formset QueryDict and discards invalid params"):
            request_querydict = QueryDict(mutable=True)
            request_querydict.setlistdefault("status", ["active", "decommissioning"])
            request_querydict.setlistdefault("name__ic", ["location"])
            request_querydict.setlistdefault("invalid_field", ["invalid"])  # Should be ignored
            request_querydict.setlistdefault("name__iew", [""])  # Should be ignored since it has no value

            data = requests.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, location_filter_set
            )
            expected_querydict = QueryDict(mutable=True)
            expected_querydict.setlistdefault("form-TOTAL_FORMS", [3])
            expected_querydict.setlistdefault("form-INITIAL_FORMS", [0])
            expected_querydict.setlistdefault("form-MIN_NUM_FORMS", [0])
            expected_querydict.setlistdefault("form-MAX_NUM_FORMS", [100])
            expected_querydict.setlistdefault("form-0-lookup_field", ["status"])
            expected_querydict.setlistdefault("form-0-lookup_type", ["status"])
            expected_querydict.setlistdefault("form-0-lookup_value", ["active", "decommissioning"])
            expected_querydict.setlistdefault("form-1-lookup_field", ["name"])
            expected_querydict.setlistdefault("form-1-lookup_type", ["name__ic"])
            expected_querydict.setlistdefault("form-1-lookup_value", ["location"])

            self.assertEqual(data, expected_querydict)

        with self.subTest("Convert an empty QueryDict to an acceptable factory formset QueryDict"):
            request_querydict = QueryDict(mutable=True)

            data = requests.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, location_filter_set
            )
            expected_querydict = QueryDict(mutable=True)
            expected_querydict.setlistdefault("form-TOTAL_FORMS", [3])
            expected_querydict.setlistdefault("form-INITIAL_FORMS", [0])
            expected_querydict.setlistdefault("form-MIN_NUM_FORMS", [0])
            expected_querydict.setlistdefault("form-MAX_NUM_FORMS", [100])

            self.assertEqual(data, expected_querydict)

        with self.subTest("Ignores q field"):
            request_querydict = QueryDict(mutable=True)
            request_querydict.setlistdefault("status", ["active"])
            request_querydict.setlistdefault("q", "location")  # Should be ignored

            data = requests.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, location_filter_set
            )
            expected_querydict = QueryDict(mutable=True)
            expected_querydict.setlistdefault("form-TOTAL_FORMS", [3])
            expected_querydict.setlistdefault("form-INITIAL_FORMS", [0])
            expected_querydict.setlistdefault("form-MIN_NUM_FORMS", [0])
            expected_querydict.setlistdefault("form-MAX_NUM_FORMS", [100])
            expected_querydict.setlistdefault("form-0-lookup_field", ["status"])
            expected_querydict.setlistdefault("form-0-lookup_type", ["status"])
            expected_querydict.setlistdefault("form-0-lookup_value", ["active"])

            self.assertEqual(data, expected_querydict)

    def test_get_filterable_params_from_filter_params(self):
        filter_params = QueryDict(mutable=True)
        filter_params.update({"page": "1", "per_page": "20", "name": "Location 1"})
        filter_params.setlistdefault("status", ["active", "planned"])

        non_filter_params = ["page", "per_page"]
        data = requests.get_filterable_params_from_filter_params(
            filter_params, non_filter_params, dcim_filters.LocationFilterSet()
        )

        self.assertEqual(data, {"name": ["Location 1"], "status": ["active", "planned"]})

    def test_ensure_content_type_and_field_name_in_query_params(self):
        with self.assertRaises(django_forms.ValidationError) as err:
            requests.ensure_content_type_and_field_name_in_query_params({})
        self.assertEqual(str(err.exception.args[0]), "content_type and field_name are required parameters")
        self.assertEqual(err.exception.code, 400)

        with self.assertRaises(django_forms.ValidationError) as err:
            requests.ensure_content_type_and_field_name_in_query_params(
                {"field_name": "name", "content_type": "dcim.abc"}
            )
        self.assertEqual(str(err.exception.args[0]), "content_type not found")
        self.assertEqual(err.exception.code, 404)


class GetFilterFieldLabelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        device_ct = ContentType.objects.get_for_model(dcim_models.Device)
        cls.peer_relationship = extras_models.Relationship(
            label="HA Device Peer",
            key="ha_device_peer",
            source_type=device_ct,
            destination_type=device_ct,
            source_label="Peer",
            destination_label="Peer",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )
        cls.peer_relationship.validated_save()

        cls.custom_field = extras_models.CustomField(key="labeled_custom_field", label="Moo!", type="text")
        cls.custom_field.validated_save()
        cls.custom_field.content_types.add(device_ct)

    def test_get_filter_field_label(self):
        """Validate the operation of get_filter_field_label()."""

        device_filter_set_filters = dcim_filters.DeviceFilterSet().filters

        with self.subTest("Simple field name"):
            self.assertEqual(filtering.get_filter_field_label(device_filter_set_filters["id"]), "Id")

        with self.subTest("Semi-complex field name"):
            self.assertEqual(
                filtering.get_filter_field_label(device_filter_set_filters["has_interfaces"]), "Has interfaces"
            )

        with self.subTest("Relationship field name"):
            self.assertEqual(
                filtering.get_filter_field_label(device_filter_set_filters[f"cr_{self.peer_relationship.key}__peer"]),
                self.peer_relationship.source_label,
            )

        with self.subTest("Custom field with label"):
            self.assertEqual(
                filtering.get_filter_field_label(device_filter_set_filters[f"cf_{self.custom_field.key}"]),
                "Moo!",
            )


class FieldNameToDisplayTest(TestCase):
    def test__field_name_to_display(self):
        """Validate the operation of _field_name_to_display()."""

        with self.subTest("id => Id"):
            self.assertEqual(filtering._field_name_to_display("id"), "Id")

        with self.subTest("device_type => Device Type"):
            self.assertEqual(filtering._field_name_to_display("device_type"), "Device type")

        with self.subTest("_custom_field_data__site_type => Site Type"):
            self.assertEqual(filtering._field_name_to_display("_custom_field_data__site_type"), "Site type")

        with self.subTest("cr_sister_sites__peer => Peer"):
            # This shouldn't ever be an input because get_filter_field_label
            # will use the label from the custom field instead of the field name
            self.assertEqual(filtering._field_name_to_display("cr_sister_sites__peer"), "Cr_sister_sites peer")


class IsFooTest(TestCase):
    def test_is_url(self):
        """Validate the operation of `is_url()`."""
        with self.subTest("Test a valid URL."):
            self.assertTrue(
                data_utils.is_url("http://localhost:3000/api/extras/statuses/3256ead7-0745-432a-a031-3928c9b7d075/")
            )
        with self.subTest("Test an nvalid URL."):
            self.assertFalse(data_utils.is_url("pizza"))

    def test_is_uuid(self):
        """Validate the operation of `is_uuid()`."""
        with self.subTest("Test valid UUID."):
            self.assertTrue(data_utils.is_uuid(uuid.uuid4()))
            self.assertTrue(data_utils.is_uuid(str(uuid.uuid4())))
        with self.subTest("Test invalid UUID."):
            self.assertFalse(data_utils.is_uuid(None))
            self.assertFalse(data_utils.is_uuid(1))
            self.assertFalse(data_utils.is_uuid("abc123"))


class MergeDictsWithoutCollisionTest(TestCase):
    """Test the merge_dicts_without_collision() data utility function."""

    def test_no_collisions(self):
        self.assertEqual({"a": 1, "b": 2}, data_utils.merge_dicts_without_collision({"a": 1}, {"b": 2}))

    def test_collision_but_same_value(self):
        self.assertEqual(
            {"a": 1, "b": 2, "c": 3}, data_utils.merge_dicts_without_collision({"a": 1, "c": 3}, {"b": 2, "c": 3})
        )

    def test_collision_differing_values(self):
        with self.assertRaises(ValueError) as err:
            data_utils.merge_dicts_without_collision({"a": 1}, {"a": 2})
        self.assertEqual(str(err.exception), 'Conflicting values for key "a": (1, 2)')


class TestMigrationUtils(TestCase):
    def test_update_object_change_ct_for_replaced_models(self):
        """Assert update and update reverse of ObjectChange"""
        location = dcim_models.Location.objects.first()
        request_id = uuid.uuid4()
        location_ct = ContentType.objects.get_for_model(dcim_models.Location)
        device_ct = ContentType.objects.get_for_model(dcim_models.Device)
        ObjectChange.objects.create(
            user_name="test-user",
            request_id=request_id,
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object=location,
            related_object=location,
            object_repr=str(location),
            object_data={"name": location.name},
        )

        with self.subTest("Update ObjectChange ContentType"):
            update_object_change_ct_for_replaced_models(
                apps=apps,
                new_app_model={"app_name": "dcim", "model": "device"},
                replaced_apps_models=[{"app_name": "dcim", "model": "location"}],
            )
            self.assertEqual(ObjectChange.objects.get(request_id=request_id).changed_object_type, device_ct)
            self.assertEqual(ObjectChange.objects.get(request_id=request_id).related_object_type, device_ct)

        with self.subTest("Reverse ObjectChange ContentType changes"):
            update_object_change_ct_for_replaced_models(
                apps=apps,
                new_app_model={"app_name": "dcim", "model": "device"},
                replaced_apps_models=[{"app_name": "dcim", "model": "location"}],
                reverse_migration=True,
            )
            self.assertEqual(ObjectChange.objects.get(request_id=request_id).changed_object_type, location_ct)
            self.assertEqual(ObjectChange.objects.get(request_id=request_id).related_object_type, location_ct)


class TestQuerySetUtils(TestCase):
    def test_maybe_select_related(self):
        # If possible, select_related should be called
        queryset = ipam_models.IPAddress.objects.all()
        with mock.patch.object(queryset, "select_related", wraps=queryset.select_related) as mock_select_related:
            new_queryset = querysets.maybe_select_related(queryset, ["parent", "status"])
            mock_select_related.assert_called_with("parent", "status")
            self.assertIsNot(new_queryset, queryset)

        # Case where it shouldn't be called
        queryset = ipam_models.IPAddress.objects.values_list("host", flat=True)
        with mock.patch.object(queryset, "select_related", wraps=queryset.select_related) as mock_select_related:
            new_queryset = querysets.maybe_select_related(queryset, ["parent", "status"])
            mock_select_related.assert_not_called()
            self.assertIs(new_queryset, queryset)

        # Another case where it shouldn't be called
        queryset = ipam_models.IPAddress.objects.difference(ipam_models.IPAddress.objects.filter(ip_version=4))
        with mock.patch.object(queryset, "select_related", wraps=queryset.select_related) as mock_select_related:
            new_queryset = querysets.maybe_select_related(queryset, ["parent", "status"])
            mock_select_related.assert_not_called()
            self.assertIs(new_queryset, queryset)

    def test_maybe_prefetch_related(self):
        # If possible, prefetch_related should be called
        queryset = ipam_models.IPAddress.objects.all()
        with mock.patch.object(queryset, "prefetch_related", wraps=queryset.prefetch_related) as mock_prefetch_related:
            new_queryset = querysets.maybe_prefetch_related(queryset, ["nat_outside_list"])
            mock_prefetch_related.assert_called_with("nat_outside_list")
            self.assertIsNot(new_queryset, queryset)

        # Case where it shouldn't be called
        queryset = ipam_models.IPAddress.objects.difference(ipam_models.IPAddress.objects.filter(ip_version=4))
        with mock.patch.object(queryset, "prefetch_related", wraps=queryset.prefetch_related) as mock_prefetch_related:
            new_queryset = querysets.maybe_prefetch_related(queryset, ["nat_outside_list"])
            mock_prefetch_related.assert_not_called()
            self.assertIs(new_queryset, queryset)
