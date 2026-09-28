from drf_spectacular.renderers import OpenApiYamlRenderer
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.utils import extend_schema_field
from openapi_spec_validator import validate
from rest_framework import serializers as drf_serializers
import yaml

from nautobot.core.testing import TestCase


def _fields_with_instance_annotations(serializer_class):
    """Names of declared fields carrying a drf-spectacular annotation on the field instance itself."""
    return [
        name
        for name, field in getattr(serializer_class, "_declared_fields", {}).items()
        if "_spectacular_annotation" in field.__dict__
    ]


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

    def test_no_instance_level_schema_annotations(self):
        """
        Assert `extend_schema_field` is never applied to a serializer field instance.

        DRF's `Field.__deepcopy__` re-instantiates declared fields from their original constructor
        arguments when a serializer binds its fields, silently discarding instance attributes such
        as the schema override, leaving the field rendered as a bare untyped object in the schema.
        Apply the annotation to a Field subclass instead; see `CableTerminationsPayloadField` in
        `nautobot/dcim/api/serializers.py` for the reference pattern.
        """

        # Negative control: prove the detector actually catches the broken pattern.
        class BrokenSerializer(drf_serializers.Serializer):
            broken = extend_schema_field({"type": "object"})(drf_serializers.JSONField())

        self.assertEqual(_fields_with_instance_annotations(BrokenSerializer), ["broken"])

        offenders = {}
        seen = set()
        stack = [drf_serializers.Serializer]
        while stack:
            for subclass in stack.pop().__subclasses__():
                if subclass in seen:
                    continue
                seen.add(subclass)
                stack.append(subclass)
                module = subclass.__module__
                # Only Nautobot's own serializers are ours to fix; test modules may contain
                # deliberately-broken fixtures like the negative control above.
                if module.partition(".")[0] not in ("nautobot", "example_app") or "tests" in module:
                    continue
                annotated = _fields_with_instance_annotations(subclass)
                if annotated:
                    offenders[f"{module}.{subclass.__name__}"] = annotated
        self.assertEqual(
            offenders,
            {},
            "extend_schema_field() was applied to serializer field instance(s). DRF's Field.__deepcopy__ "
            "discards instance-level annotations when a serializer binds its fields, so the schema "
            "override would be silently lost. Apply @extend_schema_field to a Field subclass instead "
            "(see CableTerminationsPayloadField in nautobot/dcim/api/serializers.py).",
        )
