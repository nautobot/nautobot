from django import forms as django_forms
from django.db.models import Q
from django.http import QueryDict
from django.test import TestCase
from example_plugin.models import ExampleModel

from nautobot.core import exceptions, forms, settings_funcs, utils
from nautobot.dcim import filters
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

        self.assertEqual(utils.dict_to_filter_params(input_), output)

        input_["x"]["y"]["z"] = True

        self.assertNotEqual(utils.dict_to_filter_params(input_), output)


class NormalizeQueryDictTest(TestCase):
    """
    Validate normalize_querydict() utility function.
    """

    def test_normalize_querydict(self):
        self.assertDictEqual(
            utils.normalize_querydict(QueryDict("foo=1&bar=2&bar=3&baz=")),
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

        self.assertEqual(utils.deepmerge(dict1, dict2), merged)


class FlattenIterableTest(TestCase):
    """Tests for the `flatten_iterable()` function."""

    def test_list_of_lists(self):
        items = [[1, 2, 3], [4, 5], 6]
        expected = [1, 2, 3, 4, 5, 6]
        self.assertEqual(list(utils.flatten_iterable(items)), expected)

    def test_list_of_strings(self):
        items = ["foo", ["bar"], ["baz"]]
        expected = ["foo", "bar", "baz"]
        self.assertEqual(list(utils.flatten_iterable(items)), expected)


class GetFooForModelTest(TestCase):
    """Tests for the various `get_foo_for_model()` functions."""

    def test_get_filterset_for_model(self):
        """
        Test the util function `get_filterset_for_model` returns the appropriate FilterSet, if model (as dotted string or class) provided.
        """
        self.assertEqual(utils.get_filterset_for_model("dcim.device"), filters.DeviceFilterSet)
        self.assertEqual(utils.get_filterset_for_model(dcim_models.Device), filters.DeviceFilterSet)
        self.assertEqual(utils.get_filterset_for_model("dcim.site"), filters.SiteFilterSet)
        self.assertEqual(utils.get_filterset_for_model(dcim_models.Site), filters.SiteFilterSet)

    def test_get_form_for_model(self):
        """
        Test the util function `get_form_for_model` returns the appropriate Form, if form type and model (as dotted string or class) provided.
        """
        self.assertEqual(utils.get_form_for_model("dcim.device", "Filter"), dcim_forms.DeviceFilterForm)
        self.assertEqual(utils.get_form_for_model(dcim_models.Device, "Filter"), dcim_forms.DeviceFilterForm)
        self.assertEqual(utils.get_form_for_model("dcim.site", "Filter"), dcim_forms.SiteFilterForm)
        self.assertEqual(utils.get_form_for_model(dcim_models.Site, "Filter"), dcim_forms.SiteFilterForm)
        self.assertEqual(utils.get_form_for_model("dcim.device"), dcim_forms.DeviceForm)
        self.assertEqual(utils.get_form_for_model(dcim_models.Device), dcim_forms.DeviceForm)
        self.assertEqual(utils.get_form_for_model("dcim.site"), dcim_forms.SiteForm)
        self.assertEqual(utils.get_form_for_model(dcim_models.Site), dcim_forms.SiteForm)

    def test_get_route_for_model(self):
        """
        Test the util function `get_route_for_model` returns the appropriate URL route name, if model (as dotted string or class) provided.
        """
        # UI
        self.assertEqual(utils.get_route_for_model("dcim.device", "list"), "dcim:device_list")
        self.assertEqual(utils.get_route_for_model(dcim_models.Device, "list"), "dcim:device_list")
        self.assertEqual(utils.get_route_for_model("dcim.site", "list"), "dcim:site_list")
        self.assertEqual(utils.get_route_for_model(dcim_models.Site, "list"), "dcim:site_list")
        self.assertEqual(
            utils.get_route_for_model("example_plugin.examplemodel", "list"), "plugins:example_plugin:examplemodel_list"
        )
        self.assertEqual(utils.get_route_for_model(ExampleModel, "list"), "plugins:example_plugin:examplemodel_list")

        # API
        self.assertEqual(utils.get_route_for_model("dcim.device", "list", api=True), "dcim-api:device-list")
        self.assertEqual(utils.get_route_for_model(dcim_models.Device, "list", api=True), "dcim-api:device-list")
        self.assertEqual(utils.get_route_for_model("dcim.site", "detail", api=True), "dcim-api:site-detail")
        self.assertEqual(utils.get_route_for_model(dcim_models.Site, "detail", api=True), "dcim-api:site-detail")
        self.assertEqual(
            utils.get_route_for_model("example_plugin.examplemodel", "list", api=True),
            "plugins-api:example_plugin-api:examplemodel-list",
        )
        self.assertEqual(
            utils.get_route_for_model(ExampleModel, "list", api=True),
            "plugins-api:example_plugin-api:examplemodel-list",
        )

    def test_get_table_for_model(self):
        """
        Test the util function `get_table_for_model` returns the appropriate Table, if model (as dotted string or class) provided.
        """
        self.assertEqual(utils.get_table_for_model("dcim.device"), tables.DeviceTable)
        self.assertEqual(utils.get_table_for_model(dcim_models.Device), tables.DeviceTable)
        self.assertEqual(utils.get_table_for_model("dcim.site"), tables.SiteTable)
        self.assertEqual(utils.get_table_for_model(dcim_models.Site), tables.SiteTable)

    def test_get_model_from_name(self):
        """
        Test the util function `get_model_from_name` returns the appropriate Model, if the dotted name provided.
        """
        self.assertEqual(utils.get_model_from_name("dcim.device"), dcim_models.Device)
        self.assertEqual(utils.get_model_from_name("dcim.site"), dcim_models.Site)


class IsTaggableTest(TestCase):
    def test_is_taggable_true(self):
        # Classes
        self.assertTrue(utils.is_taggable(dcim_models.Site))
        self.assertTrue(utils.is_taggable(dcim_models.Device))

        # Instances
        self.assertTrue(utils.is_taggable(dcim_models.Site(name="Test Site")))

    def test_is_taggable_false(self):
        class FakeOut:
            tags = "Nope!"

        # Classes
        self.assertFalse(utils.is_taggable(dcim_models.Region))
        self.assertFalse(utils.is_taggable(FakeOut))

        # Instances
        self.assertFalse(utils.is_taggable(dcim_models.Region(name="Test Region")))
        self.assertFalse(utils.is_taggable(FakeOut()))

        self.assertFalse(utils.is_taggable(None))


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
        queries = [
            ((Q(site__slug="ams01") | Q(site__slug="ang01")) & ~Q(status__slug="active")) | Q(status__slug="planned"),
            (Q(site__slug="ams01") | Q(site__slug="ang01")) & ~Q(status__slug="active"),
            Q(site__slug="ams01") | Q(site__slug="ang01"),
            Q(site__slug="ang01") & ~Q(status__slug="active"),
            Q(site__slug="ams01", status__slug="planned"),
            Q(site__slug="ang01"),
            Q(status__id=12345),
            Q(site__slug__in=["ams01", "ang01"]),
        ]
        results = [
            """\
(
  (
    (
      site__slug='ams01' OR site__slug='ang01'
    ) AND (
      NOT (status__slug='active')
    )
  ) OR status__slug='planned'
)""",
            """\
(
  (
    site__slug='ams01' OR site__slug='ang01'
  ) AND (
    NOT (status__slug='active')
  )
)""",
            """\
(
  site__slug='ams01' OR site__slug='ang01'
)""",
            """\
(
  site__slug='ang01' AND (
    NOT (status__slug='active')
  )
)""",
            """\
(
  site__slug='ams01' AND status__slug='planned'
)""",
            """\
(
  site__slug='ang01'
)""",
            """\
(
  status__id=12345
)""",
            """\
(
  site__slug__in=['ams01', 'ang01']
)""",
        ]

        tests = zip(queries, results)

        for query, expected in tests:
            with self.subTest(query=query):
                self.assertEqual(utils.pretty_print_query(query), expected)


class SlugifyFunctionsTest(TestCase):
    """Test custom slugify functions."""

    def test_slugify_dots_to_dashes(self):
        for content, expected in (
            ("Hello.World", "hello-world"),
            ("plugins.my_plugin.jobs", "plugins-my_plugin-jobs"),
            ("Lots of . spaces  ... and such", "lots-of-spaces-and-such"),
        ):
            self.assertEqual(utils.slugify_dots_to_dashes(content), expected)

    def test_slugify_dashes_to_underscores(self):
        for content, expected in (
            ("Sites / Regions", "sites_regions"),
            ("alpha-beta_gamma delta", "alpha_beta_gamma_delta"),
        ):
            self.assertEqual(utils.slugify_dashes_to_underscores(content), expected)


class LookupRelatedFunctionTest(TestCase):
    def test_is_single_choice_field(self):
        # Assert function returns True for any field starting with create or has_
        # Cause these fields are either boolean fields or date time fields which one accepts single values
        filterset_class = filters.SiteFilterSet

        single_choice_fields = ("created", "created__gte", "has_vlans", "has_clusters", "q")
        for field in single_choice_fields:
            self.assertTrue(utils.is_single_choice_field(filterset_class, field))

        multi_choice_fields = ("status", "tenant", "tags")
        for field in multi_choice_fields:
            self.assertFalse(utils.is_single_choice_field(filterset_class, field))

    def test_build_lookup_label(self):
        with self.subTest():
            label = utils.build_lookup_label("slug__iew", "iendswith")
            self.assertEqual(label, "ends with (iew)")

        with self.subTest("Test negation"):
            label = utils.build_lookup_label("slug__niew", "iendswith")
            self.assertEqual(label, "not ends with (niew)")

        with self.subTest("Test for exact: without a lookup expr"):
            label = utils.build_lookup_label("slug", "exact")
            self.assertEqual(label, "exact")

    def test_get_all_lookup_expr_for_field(self):
        with self.subTest():
            lookup_expr = utils.get_all_lookup_expr_for_field(dcim_models.Site, "status")
            self.assertEqual(
                lookup_expr,
                [{"id": "status", "name": "exact"}, {"id": "status__n", "name": "not exact (n)"}],
            )

        with self.subTest("Test field with has_ prefix"):
            lookup_expr = utils.get_all_lookup_expr_for_field(dcim_models.Site, "has_vlans")
            self.assertEqual(
                lookup_expr,
                [{"id": "has_vlans", "name": "exact"}],
            )

        with self.subTest("Test unknown field"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                utils.get_all_lookup_expr_for_field(dcim_models.Site, "unknown_field")
            self.assertEqual(str(err.exception), "field_name not found")

    def test_get_filterset_field(self):
        with self.subTest():
            field = utils.get_filterset_field(filters.SiteFilterSet, "name")
            self.assertEqual(field.__class__, filters.SiteFilterSet().filters.get("name").__class__)

        with self.subTest("Test invalid field"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                utils.get_filterset_field(filters.SiteFilterSet, "unknown")
            self.assertEqual(str(err.exception), "unknown is not a valid SiteFilterSet field")

    def test_get_filterset_parameter_form_field(self):
        with self.subTest("Test get CharFields"):
            site_fields = ["comments", "name", "contact_email", "physical_address", "shipping_address"]
            for field_name in site_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Site, field_name)
                self.assertIsInstance(form_field, django_forms.CharField)

            device_fields = ["serial", "name"]
            for field_name in device_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, django_forms.CharField)

        with self.subTest("Test IntegerField"):
            form_field = utils.get_filterset_parameter_form_field(dcim_models.Site, "asn")
            self.assertIsInstance(form_field, django_forms.IntegerField)

            device_fields = ["vc_position", "vc_priority"]
            for field_name in device_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, django_forms.IntegerField)

        with self.subTest("Test DynamicModelMultipleChoiceField"):
            site_fields = ["region", "tenant", "status"]
            for field_name in site_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Site, field_name)
                self.assertIsInstance(form_field, forms.DynamicModelMultipleChoiceField)

            device_fields = ["cluster", "device_type", "region"]
            for field_name in device_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, forms.DynamicModelMultipleChoiceField)

        with self.subTest("Test ChoiceField"):
            site_fields = ["has_locations", "has_circuit_terminations", "has_devices"]
            for field_name in site_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Site, field_name)
                self.assertIsInstance(form_field, django_forms.ChoiceField)

            device_fields = ["has_console_ports", "has_interfaces", "face"]
            for field_name in device_fields:
                form_field = utils.get_filterset_parameter_form_field(dcim_models.Device, field_name)
                self.assertIsInstance(form_field, django_forms.ChoiceField)

        with self.subTest("Test DateTimePicker"):
            form_field = utils.get_filterset_parameter_form_field(dcim_models.Site, "last_updated")
            self.assertIsInstance(form_field.widget, forms.DateTimePicker)

            form_field = utils.get_filterset_parameter_form_field(dcim_models.Device, "last_updated")
            self.assertIsInstance(form_field.widget, forms.DateTimePicker)

        with self.subTest("Test DatePicker"):
            form_field = utils.get_filterset_parameter_form_field(dcim_models.Site, "created")
            self.assertIsInstance(form_field.widget, forms.DatePicker)

            form_field = utils.get_filterset_parameter_form_field(dcim_models.Device, "created")
            self.assertIsInstance(form_field.widget, forms.DatePicker)

        with self.subTest("Test Invalid parameter"):
            with self.assertRaises(exceptions.FilterSetFieldNotFound) as err:
                utils.get_filterset_parameter_form_field(dcim_models.Site, "unknown")
            self.assertEqual(str(err.exception), "unknown is not a valid SiteFilterSet field")

        with self.subTest("Test Content types"):
            form_field = utils.get_filterset_parameter_form_field(extras_models.Status, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)

            # Assert total ContentTypes generated by form_field is == total `content_types` generated by TaggableClassesQuery
            form_field = utils.get_filterset_parameter_form_field(extras_models.Tag, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)
            self.assertEqual(form_field.queryset.count(), extras_utils.TaggableClassesQuery().as_queryset().count())

            form_field = utils.get_filterset_parameter_form_field(extras_models.JobHook, "content_types")
            self.assertIsInstance(form_field, forms.MultipleContentTypeField)
            self.assertEqual(form_field.queryset.count(), extras_utils.ChangeLoggedModelsQuery().as_queryset().count())

    def test_convert_querydict_to_factory_formset_dict(self):
        with self.subTest("Convert QueryDict to an acceptable factory formset QueryDict and discards invalid params"):
            request_querydict = QueryDict(mutable=True)
            request_querydict.setlistdefault("status", ["active", "decommissioning"])
            request_querydict.setlistdefault("name__ic", ["site"])
            request_querydict.setlistdefault("invalid_field", ["invalid"])  # Should be ignored
            request_querydict.setlistdefault("name__iew", [""])  # Should be ignored since it has no value

            data = utils.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, filters.SiteFilterSet
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
            expected_querydict.setlistdefault("form-1-lookup_value", ["site"])

            self.assertEqual(data, expected_querydict)

        with self.subTest("Convert an empty QueryDict to an acceptable factory formset QueryDict"):
            request_querydict = QueryDict(mutable=True)

            data = utils.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, filters.SiteFilterSet
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
            request_querydict.setlistdefault("q", "site")  # Should be ignored

            data = utils.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, filters.SiteFilterSet
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
        filter_params.update({"page": "1", "per_page": "20", "name": "Site 1"})
        filter_params.setlistdefault("status", ["active", "planned"])

        non_filter_params = ["page", "per_page"]
        filterset_class = filters.SiteFilterSet
        data = utils.get_filterable_params_from_filter_params(filter_params, non_filter_params, filterset_class)

        self.assertEqual(data, {"name": ["Site 1"], "status": ["active", "planned"]})

    def test_ensure_content_type_and_field_name_inquery_params(self):
        with self.assertRaises(django_forms.ValidationError) as err:
            utils.ensure_content_type_and_field_name_inquery_params({})
        self.assertEqual(str(err.exception.args[0]), "content_type and field_name are required parameters")
        self.assertEqual(err.exception.code, 400)

        with self.assertRaises(django_forms.ValidationError) as err:
            utils.ensure_content_type_and_field_name_inquery_params({"field_name": "name", "content_type": "dcim.abc"})
        self.assertEqual(str(err.exception.args[0]), "content_type not found")
        self.assertEqual(err.exception.code, 404)
