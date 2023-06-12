from io import StringIO
import yaml

from django.conf import settings
from django.core.management import call_command
from django.test import tag
from rest_framework.settings import api_settings

from nautobot.core.testing import views


@tag("unit")
class OpenAPISchemaTestCases:
    class BaseSchemaTestCase(views.TestCase):
        """Base class for testing of the OpenAPI schema."""

        @classmethod
        def setUpTestData(cls):
            # We could load the schema from the /api/swagger.yaml endpoint in setUp(self) via self.client,
            # but it's fairly expensive to do so. Better to do so only once per class.
            cls.schemas = {}
            for api_version in api_settings.ALLOWED_VERSIONS:
                out = StringIO()
                err = StringIO()
                call_command("spectacular", "--api-version", api_version, stdout=out, stderr=err)
                cls.schemas[api_version] = yaml.safe_load(out.getvalue())

        def get_component_schema(self, component_name, api_version=None):
            """Helper method to pull a specific component schema from the larger OpenAPI schema already loaded."""
            if api_version is None:
                api_version = settings.REST_FRAMEWORK_VERSION
            self.assertIn(component_name, self.schemas[api_version]["components"]["schemas"])
            return self.schemas[api_version]["components"]["schemas"][component_name]

        def assert_component_mapped_by_object_type(self, schema, models):
            """Test method to assert that this polymorphic component has the expected permitted types."""
            # For all polymorphic nested serializers, we should be using the "object_type" field to discriminate them.
            self.assertEqual(schema["discriminator"]["propertyName"], "object_type")
            if models is None:
                models = []
            # We don't care what the schema calls the individual serializers in discriminator.mapping,
            # but we do want to assert that they're the correct set of model content-types as keys
            self.assertEqual(
                set(schema["discriminator"]["mapping"].keys()),
                {f"{model._meta.app_label}.{model._meta.model_name}" for model in models},
            )

        def get_schema_property(self, component_schema, property_name):
            """Helper method to pull a specific property schema from a larger component schema already extracted."""
            self.assertIn(property_name, component_schema["properties"])
            return component_schema["properties"][property_name]

        def get_property_ref_component_name(self, component_schema, property_name):
            """Helper method to identify a component referenced by the given property of the current component."""
            property_schema = self.get_schema_property(component_schema, property_name)
            if "allOf" in property_schema:
                # "allOf":
                # - "$ref": "#/components/schemas/ComponentName"
                self.assertEqual(len(property_schema["allOf"]), 1)
                self.assertIn("$ref", property_schema["allOf"][0])
                return property_schema["allOf"][0]["$ref"].split("/")[-1]
            if property_schema.get("type") == "array":
                # "type": "array"
                # "items":
                #   "$ref": "#/components/schemas/ComponentName"
                self.assertIn("items", property_schema)
                self.assertIn("$ref", property_schema["items"])
                return property_schema["items"]["$ref"].split("/")[-1]
            # TODO: extend to handle other cases as needed?
            self.fail(f"Property schema not as expected: {property_schema}")
            return None

        def assert_nullable_property(self, component_schema, property_name):
            """Test method to assert that the given component property is marked as nullable."""
            self.assertTrue(self.get_schema_property(component_schema, property_name).get("nullable", False))

        def assert_not_nullable_property(self, component_schema, property_name):
            """Test method to assert that the given component property is marked as non-nullable."""
            self.assertFalse(self.get_schema_property(component_schema, property_name).get("nullable", False))

        def assert_read_only_property(self, component_schema, property_name):
            """Test method to assert that the given component property is marked as read-only."""
            self.assertTrue(self.get_schema_property(component_schema, property_name).get("readOnly", False))

        def assert_not_read_only_property(self, component_schema, property_name):
            """Test method to assert that the given component property is not marked as read-only."""
            self.assertFalse(self.get_schema_property(component_schema, property_name).get("readOnly", False))

        def validate_polymorphic_property(
            self,
            component_name,
            property_name,
            models=None,
            nullable=False,
            read_only=True,
            many=False,
        ):
            """
            Bringing it all together.

            This validates the schema to show that:
            - The component exists and has such a property
            - The property has the correct `nullable` and `readOnly` values
            - The property has the correct multiplicity
            - The property is a reference to another component
            - The property's referenced component is polymorphic and has the expected set of model content-types.

            Returns:
                tuple: (ref_component_name, ref_component_schema)
            """
            component_schema = self.get_component_schema(component_name)

            if nullable:
                self.assert_nullable_property(component_schema, property_name)
            else:
                self.assert_not_nullable_property(component_schema, property_name)

            if read_only:
                self.assert_read_only_property(component_schema, property_name)
            else:
                self.assert_not_read_only_property(component_schema, property_name)

            if many:
                self.assertEqual("array", self.get_schema_property(component_schema, property_name).get("type"))
            else:
                self.assertNotEqual("array", self.get_schema_property(component_schema, property_name).get("type"))

            ref_component_name = self.get_property_ref_component_name(component_schema, property_name)
            ref_component_schema = self.get_component_schema(ref_component_name)
            self.assert_component_mapped_by_object_type(ref_component_schema, models=models)

            return (ref_component_name, ref_component_schema)
