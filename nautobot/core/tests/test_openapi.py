from drf_spectacular.renderers import OpenApiYamlRenderer
from drf_spectacular.settings import spectacular_settings
from openapi_spec_validator import validate
import yaml

from nautobot.core.testing import TestCase


class OpenAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        generator_class = spectacular_settings.DEFAULT_GENERATOR_CLASS
        generator = generator_class()  # TODO: in future we may want to specify an `api_version=...` here
        schema = generator.get_schema(request=None, public=True)
        # We probably could stop here but let's round-trip it through the YAML renderer just for the heck of it
        renderer = OpenApiYamlRenderer()
        cls.binary_output = renderer.render(schema, renderer_context={})
        cls.yaml_output = cls.binary_output.decode("utf-8")
        cls.schema = yaml.safe_load(cls.yaml_output)

    def test_filter_boolean_type(self):
        """
        Test that a boolean filter is correctly represented as a boolean.

        Testing for regression of https://github.com/nautobot/nautobot/issues/4377.
        """
        query_params = self.schema["paths"]["/dcim/devices/"]["get"]["parameters"]
        at_least_one_test = False
        for query_param_info in query_params:
            if query_param_info["name"].startswith("has_"):
                self.assertEqual("boolean", query_param_info["schema"]["type"])
                at_least_one_test = True
        self.assertTrue(at_least_one_test)

    def test_filter_datetime_type(self):
        """
        Test that a datetime filter is correctly represented as an array of date-time strings.

        Testing for regression of https://github.com/nautobot/nautobot/issues/4377.
        """
        query_params = self.schema["paths"]["/dcim/devices/"]["get"]["parameters"]
        at_least_one_test = False
        for query_param_info in query_params:
            if query_param_info["name"].endswith("_isnull"):
                # The broad catch below does not apply to isnull, which will return a boolean.
                continue
            if query_param_info["name"].startswith("created") or query_param_info["name"].startswith("last_updated"):
                self.assertEqual("array", query_param_info["schema"]["type"])
                self.assertEqual("string", query_param_info["schema"]["items"]["type"])
                self.assertEqual("date-time", query_param_info["schema"]["items"]["format"])
                at_least_one_test = True
        self.assertTrue(at_least_one_test)

    def test_filter_integer_type(self):
        """
        Test that an integer filter is correctly represented as an array of integers.

        Testing for regression of https://github.com/nautobot/nautobot/issues/4377.
        """
        query_params = self.schema["paths"]["/dcim/devices/"]["get"]["parameters"]
        at_least_one_test = False
        for query_param_info in query_params:
            if query_param_info["name"].endswith("_isnull"):
                # The broad catch below does not apply to isnull, which will return a boolean.
                continue
            if query_param_info["name"].startswith("device_redundancy_group_priority"):
                self.assertEqual("array", query_param_info["schema"]["type"])
                self.assertEqual("integer", query_param_info["schema"]["items"]["type"])
                at_least_one_test = True
        self.assertTrue(at_least_one_test)

    def test_validate_openapi_spec(self):
        """
        Validate that the generated OpenAPI spec is valid according to the OpenAPI 3.0 schema.
        """
        validate(self.schema)
