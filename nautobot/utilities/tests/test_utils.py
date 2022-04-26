from django.http import QueryDict
from django.test import TestCase

from nautobot.core.settings_funcs import is_truthy
from nautobot.utilities.utils import (
    deepmerge,
    dict_to_filter_params,
    get_form_for_model,
    get_filterset_for_model,
    get_model_from_name,
    get_route_for_model,
    get_table_for_model,
    normalize_querydict,
)
from nautobot.dcim.models import Device, Site
from nautobot.dcim.filters import DeviceFilterSet, SiteFilterSet
from nautobot.dcim.forms import DeviceForm, DeviceFilterForm, SiteForm, SiteFilterForm
from nautobot.dcim.tables import DeviceTable, SiteTable

from example_plugin.models import ExampleModel


class DictToFilterParamsTest(TestCase):
    """
    Validate the operation of dict_to_filter_params().
    """

    def test_dict_to_filter_params(self):

        input = {
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

        self.assertEqual(dict_to_filter_params(input), output)

        input["x"]["y"]["z"] = True

        self.assertNotEqual(dict_to_filter_params(input), output)


class NormalizeQueryDictTest(TestCase):
    """
    Validate normalize_querydict() utility function.
    """

    def test_normalize_querydict(self):
        self.assertDictEqual(
            normalize_querydict(QueryDict("foo=1&bar=2&bar=3&baz=")),
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

        self.assertEqual(deepmerge(dict1, dict2), merged)


class GetFooForModelTest(TestCase):
    """Tests for the various `get_foo_for_model()` functions."""

    def test_get_filterset_for_model(self):
        """
        Test the util function `get_filterset_for_model` returns the appropriate FilterSet, if model (as dotted string or class) provided.
        """
        self.assertEqual(get_filterset_for_model("dcim.device"), DeviceFilterSet)
        self.assertEqual(get_filterset_for_model(Device), DeviceFilterSet)
        self.assertEqual(get_filterset_for_model("dcim.site"), SiteFilterSet)
        self.assertEqual(get_filterset_for_model(Site), SiteFilterSet)

    def test_get_form_for_model(self):
        """
        Test the util function `get_form_for_model` returns the appropriate Form, if form type and model (as dotted string or class) provided.
        """
        self.assertEqual(get_form_for_model("dcim.device", "Filter"), DeviceFilterForm)
        self.assertEqual(get_form_for_model(Device, "Filter"), DeviceFilterForm)
        self.assertEqual(get_form_for_model("dcim.site", "Filter"), SiteFilterForm)
        self.assertEqual(get_form_for_model(Site, "Filter"), SiteFilterForm)
        self.assertEqual(get_form_for_model("dcim.device"), DeviceForm)
        self.assertEqual(get_form_for_model(Device), DeviceForm)
        self.assertEqual(get_form_for_model("dcim.site"), SiteForm)
        self.assertEqual(get_form_for_model(Site), SiteForm)

    def test_get_route_for_model(self):
        """
        Test the util function `get_route_for_model` returns the appropriate URL route name, if model (as dotted string or class) provided.
        """
        self.assertEqual(get_route_for_model("dcim.device", "list"), "dcim:device_list")
        self.assertEqual(get_route_for_model(Device, "list"), "dcim:device_list")
        self.assertEqual(get_route_for_model("dcim.site", "list"), "dcim:site_list")
        self.assertEqual(get_route_for_model(Site, "list"), "dcim:site_list")
        self.assertEqual(
            get_route_for_model("example_plugin.examplemodel", "list"), "plugins:example_plugin:examplemodel_list"
        )
        self.assertEqual(get_route_for_model(ExampleModel, "list"), "plugins:example_plugin:examplemodel_list")

    def test_get_table_for_model(self):
        """
        Test the util function `get_table_for_model` returns the appropriate Table, if model (as dotted string or class) provided.
        """
        self.assertEqual(get_table_for_model("dcim.device"), DeviceTable)
        self.assertEqual(get_table_for_model(Device), DeviceTable)
        self.assertEqual(get_table_for_model("dcim.site"), SiteTable)
        self.assertEqual(get_table_for_model(Site), SiteTable)

    def test_get_model_from_name(self):
        """
        Test the util function `get_model_from_name` returns the appropriate Model, if the dotted name provided.
        """
        self.assertEqual(get_model_from_name("dcim.device"), Device)
        self.assertEqual(get_model_from_name("dcim.site"), Site)


class IsTruthyTest(TestCase):
    def test_is_truthy(self):
        self.assertTrue(is_truthy("true"))
        self.assertTrue(is_truthy("True"))
        self.assertTrue(is_truthy(True))
        self.assertTrue(is_truthy("yes"))
        self.assertTrue(is_truthy("on"))
        self.assertTrue(is_truthy("y"))
        self.assertTrue(is_truthy("1"))
        self.assertTrue(is_truthy(1))

        self.assertFalse(is_truthy("false"))
        self.assertFalse(is_truthy("False"))
        self.assertFalse(is_truthy(False))
        self.assertFalse(is_truthy("no"))
        self.assertFalse(is_truthy("n"))
        self.assertFalse(is_truthy(0))
        self.assertFalse(is_truthy("0"))
