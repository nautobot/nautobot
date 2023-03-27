import pickle

from django import forms as django_forms
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import QueryDict
from django.test import RequestFactory, TestCase

from example_plugin.models import ExampleModel

from nautobot.circuits import models as circuits_models
from nautobot.core import constants, exceptions, forms, settings_funcs, testing
from nautobot.core.api import utils as api_utils
from nautobot.core.models import fields as core_fields, utils as models_utils
from nautobot.core.utils import data as data_utils, filtering, lookup, requests
from nautobot.dcim import filters as dcim_filters
from nautobot.dcim import forms as dcim_forms
from nautobot.dcim import models as dcim_models
from nautobot.dcim import tables
from nautobot.extras import models as extras_models
from nautobot.extras import utils as extras_utils


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
        Test the util function `get_filterset_for_model` returns the appropriate FilterSet, if model (as dotted string or class) provided.
        """
        self.assertEqual(lookup.get_filterset_for_model("dcim.device"), dcim_filters.DeviceFilterSet)
        self.assertEqual(lookup.get_filterset_for_model(dcim_models.Device), dcim_filters.DeviceFilterSet)
        self.assertEqual(lookup.get_filterset_for_model("dcim.location"), dcim_filters.LocationFilterSet)
        self.assertEqual(lookup.get_filterset_for_model(dcim_models.Location), dcim_filters.LocationFilterSet)

    def test_get_form_for_model(self):
        """
        Test the util function `get_form_for_model` returns the appropriate Form, if form type and model (as dotted string or class) provided.
        """
        self.assertEqual(lookup.get_form_for_model("dcim.device", "Filter"), dcim_forms.DeviceFilterForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Device, "Filter"), dcim_forms.DeviceFilterForm)
        self.assertEqual(lookup.get_form_for_model("dcim.location", "Filter"), dcim_forms.LocationFilterForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Location, "Filter"), dcim_forms.LocationFilterForm)
        self.assertEqual(lookup.get_form_for_model("dcim.device"), dcim_forms.DeviceForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Device), dcim_forms.DeviceForm)
        self.assertEqual(lookup.get_form_for_model("dcim.location"), dcim_forms.LocationForm)
        self.assertEqual(lookup.get_form_for_model(dcim_models.Location), dcim_forms.LocationForm)

    def test_get_route_for_model(self):
        """
        Test the util function `get_route_for_model` returns the appropriate URL route name, if model (as dotted string or class) provided.
        """
        # UI
        self.assertEqual(lookup.get_route_for_model("dcim.device", "list"), "dcim:device_list")
        self.assertEqual(lookup.get_route_for_model(dcim_models.Device, "list"), "dcim:device_list")
        self.assertEqual(lookup.get_route_for_model("dcim.location", "list"), "dcim:location_list")
        self.assertEqual(lookup.get_route_for_model(dcim_models.Location, "list"), "dcim:location_list")
        self.assertEqual(
            lookup.get_route_for_model("example_plugin.examplemodel", "list"),
            "plugins:example_plugin:examplemodel_list",
        )
        self.assertEqual(lookup.get_route_for_model(ExampleModel, "list"), "plugins:example_plugin:examplemodel_list")

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
            lookup.get_route_for_model("example_plugin.examplemodel", "list", api=True),
            "plugins-api:example_plugin-api:examplemodel-list",
        )
        self.assertEqual(
            lookup.get_route_for_model(ExampleModel, "list", api=True),
            "plugins-api:example_plugin-api:examplemodel-list",
        )

    def test_get_table_for_model(self):
        """
        Test the util function `get_table_for_model` returns the appropriate Table, if model (as dotted string or class) provided.
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
            ((Q(location__slug="ams01") | Q(location__slug="ang01")) & ~Q(status__slug="active"))
            | Q(status__slug="planned"),
            (Q(location__slug="ams01") | Q(location__slug="ang01")) & ~Q(status__slug="active"),
            Q(location__slug="ams01") | Q(location__slug="ang01"),
            Q(location__slug="ang01") & ~Q(status__slug="active"),
            Q(location__slug="ams01", status__slug="planned"),
            Q(location__slug="ang01"),
            Q(status__id=12345),
            Q(location__slug__in=["ams01", "ang01"]),
        ]
        # pylint: enable=unsupported-binary-operation
        results = [
            """\
(
  (
    (
      location__slug='ams01' OR location__slug='ang01'
    ) AND (
      NOT (status__slug='active')
    )
  ) OR status__slug='planned'
)""",
            """\
(
  (
    location__slug='ams01' OR location__slug='ang01'
  ) AND (
    NOT (status__slug='active')
  )
)""",
            """\
(
  location__slug='ams01' OR location__slug='ang01'
)""",
            """\
(
  location__slug='ang01' AND (
    NOT (status__slug='active')
  )
)""",
            """\
(
  location__slug='ams01' AND status__slug='planned'
)""",
            """\
(
  location__slug='ang01'
)""",
            """\
(
  status__id=12345
)""",
            """\
(
  location__slug__in=['ams01', 'ang01']
)""",
        ]

        tests = zip(queries, results)

        for query, expected in tests:
            with self.subTest(query=query):
                self.assertEqual(models_utils.pretty_print_query(query), expected)


class SlugifyFunctionsTest(TestCase):
    """Test custom slugify functions."""

    def test_slugify_dots_to_dashes(self):
        for content, expected in (
            ("Hello.World", "hello-world"),
            ("plugins.my_plugin.jobs", "plugins-my_plugin-jobs"),
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


class LookupRelatedFunctionTest(TestCase):
    def test_is_single_choice_field(self):
        """
        Assert that is_single_choice_field() correctly distinguishes between single-value and multi-value filter fields.
        """
        filterset_class = dcim_filters.LocationFilterSet

        single_choice_fields = ("has_vlans", "has_clusters")
        for field in single_choice_fields:
            with self.subTest(f"Single choice field: {field}"):
                self.assertTrue(requests.is_single_choice_field(filterset_class, field))

        multi_choice_fields = ("created", "status", "tenant", "tags")
        for field in multi_choice_fields:
            with self.subTest(f"Multi choice field: {field}"):
                self.assertFalse(requests.is_single_choice_field(filterset_class, field))

    def test_build_lookup_label(self):
        with self.subTest():
            label = filtering.build_lookup_label("slug__iew", "iendswith")
            self.assertEqual(label, "ends with (iew)")

        with self.subTest("Test negation"):
            label = filtering.build_lookup_label("slug__niew", "iendswith")
            self.assertEqual(label, "not ends with (niew)")

        with self.subTest("Test for exact: without a lookup expr"):
            label = filtering.build_lookup_label("slug", "exact")
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
        with self.subTest():
            field = filtering.get_filterset_field(dcim_filters.LocationFilterSet, "name")
            self.assertEqual(field.__class__, dcim_filters.LocationFilterSet().filters.get("name").__class__)

        with self.subTest("Test invalid field"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                filtering.get_filterset_field(dcim_filters.LocationFilterSet, "unknown")
            self.assertEqual(str(err.exception), "unknown is not a valid LocationFilterSet field")

    def test_get_filterset_parameter_form_field(self):
        with self.subTest("Test get CharFields"):
            location_fields = ["comments", "name", "contact_email", "physical_address", "shipping_address"]
            for field_name in location_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, field_name)
                self.assertIsInstance(form_field, django_forms.CharField)

            device_fields = ["serial", "name"]
            for field_name in device_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, django_forms.CharField)

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

        with self.subTest("Test NullBooleanField"):
            location_fields = ["has_circuit_terminations", "has_devices"]
            for field_name in location_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Location, field_name)
                self.assertIsInstance(form_field, django_forms.NullBooleanField)

            device_fields = ["has_console_ports", "has_interfaces"]
            for field_name in device_fields:
                form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, django_forms.NullBooleanField)

        with self.subTest("Test ChoiceField"):
            form_field = filtering.get_filterset_parameter_form_field(dcim_models.Device, "face")
            self.assertIsInstance(form_field, django_forms.ChoiceField)

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
            self.assertEqual(form_field.queryset.count(), extras_utils.TaggableClassesQuery().as_queryset().count())

            form_field = filtering.get_filterset_parameter_form_field(extras_models.JobHook, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)
            self.assertEqual(form_field.queryset.count(), extras_utils.ChangeLoggedModelsQuery().as_queryset().count())

    def test_convert_querydict_to_factory_formset_dict(self):
        with self.subTest("Convert QueryDict to an acceptable factory formset QueryDict and discards invalid params"):
            request_querydict = QueryDict(mutable=True)
            request_querydict.setlistdefault("status", ["active", "decommissioning"])
            request_querydict.setlistdefault("name__ic", ["location"])
            request_querydict.setlistdefault("invalid_field", ["invalid"])  # Should be ignored
            request_querydict.setlistdefault("name__iew", [""])  # Should be ignored since it has no value

            data = requests.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, dcim_filters.LocationFilterSet
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
                request_querydict, dcim_filters.LocationFilterSet
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
                request_querydict, dcim_filters.LocationFilterSet
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
        filterset_class = dcim_filters.LocationFilterSet
        data = requests.get_filterable_params_from_filter_params(filter_params, non_filter_params, filterset_class)

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


class NautobotFakeRequestTest(testing.TestCase):
    """Test the NautobotFakeRequest class."""

    def setUp(self):
        """Create the RequestFactory."""
        super().setUp()
        self.factory = RequestFactory()

    def get_with_user(self, url):
        """RequestFactory() doesn't run middleware, so simulate it."""
        request = self.factory.get(url)
        request.user = self.user
        return request

    def test_copy_safe_request(self):
        """Test that copy_safe_request() produces a realistic looking NautobotFakeRequest."""
        real_request = self.get_with_user("/")
        fake_request = requests.copy_safe_request(real_request)
        self.assertEqual(real_request.POST, fake_request.POST)
        self.assertEqual(real_request.GET, fake_request.GET)
        self.assertEqual(real_request.user, fake_request.user)
        self.assertEqual(real_request.path, fake_request.path)
        for key in fake_request.META.keys():
            self.assertIn(key, constants.HTTP_REQUEST_META_SAFE_COPY)
            self.assertEqual(real_request.META[key], fake_request.META[key])
        self.assertEqual(fake_request.user, self.user)

    def test_fake_request_json_no_extra_db_access(self):
        """Verify that serializing and deserializing a NautobotFakeRequest as JSON doesn't unnecessarily access the DB."""
        real_request = self.get_with_user("/")
        fake_request = requests.copy_safe_request(real_request)
        with self.assertNumQueries(0):
            new_fake_request = requests.NautobotFakeRequest.nautobot_deserialize(fake_request.nautobot_serialize())
        # After creating the new instance, its `user` is a lazy attribute, which should evaluate on demand:
        with self.assertNumQueries(1):
            new_fake_request.user
            self.assertEqual(new_fake_request.user, self.user)
        # It should then be cached and not require re-lookup from the DB
        with self.assertNumQueries(0):
            new_fake_request.user

    def test_fake_request_pickle_no_extra_db_access(self):
        """Verify that pickling and unpickling a NautobotFakeRequest doesn't unnecessarily access the DB."""
        real_request = self.get_with_user("/")
        fake_request = requests.copy_safe_request(real_request)
        with self.assertNumQueries(0):
            new_fake_request = pickle.loads(pickle.dumps(fake_request))
        # After creating the new instance, its `user` is a lazy attribute, which should evaluate on demand:
        with self.assertNumQueries(1):
            new_fake_request.user
            self.assertEqual(new_fake_request.user, self.user)
        # It should then be cached and not require re-lookup from the DB
        with self.assertNumQueries(0):
            new_fake_request.user
