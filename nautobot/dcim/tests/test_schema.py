from nautobot.core.models.utils import get_all_concrete_subclasses
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.dcim.models import CableTermination, PathEndpoint


class DCIMOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various DCIM data."""

    def test_cable_termination__cable_peer_schema(self):
        """Test the polymorphic serializer for a CableTermination endpoint's `cable_peer` field."""
        # We could test each CableTermination subclass's schema but they're all derived from a common base,
        # so it'd be a waste of time. Just pick Interface arbitrarily.
        interface_schema = self.schemas["2.0"]["components"]["schemas"]["Interface"]
        self.assertEqual(
            interface_schema["properties"]["cable_peer"],
            {
                "allOf": [{"$ref": "#/components/schemas/cable_termination__cable_peer"}],
                "nullable": True,
                "readOnly": True,
            },
        )

        cable_peer_schema = self.schemas["2.0"]["components"]["schemas"]["cable_termination__cable_peer"]
        self.assertEqual(cable_peer_schema["discriminator"]["propertyName"], "object_type")
        # We don't care what the schema calls the individual serializers in discriminator.mapping,
        # but we do want to assert that they're the correct set of models
        self.assertEqual(
            set(cable_peer_schema["discriminator"]["mapping"].keys()),
            set(
                [
                    f"{model._meta.app_label}.{model._meta.model_name}"
                    for model in get_all_concrete_subclasses(CableTermination)
                ]
            ),
        )

    def test_path_endpoint__connected_endpoint_schema(self):
        """Test the polymorphic serializer for a PathEndpoint endpoint's `connected_endpoint` field."""
        # We could test each PathEndpoint subclass's schema but they're all derived from a common base class,
        # so it'd be a waste of time. Just pick Interface arbitrarily.
        interface_schema = self.schemas["2.0"]["components"]["schemas"]["Interface"]
        self.assertEqual(
            interface_schema["properties"]["connected_endpoint"],
            {
                "allOf": [{"$ref": "#/components/schemas/path_endpoint__connected_endpoint"}],
                "nullable": True,
                "readOnly": True,
            },
        )

        connected_endpoint_schema = self.schemas["2.0"]["components"]["schemas"]["path_endpoint__connected_endpoint"]
        self.assertEqual(connected_endpoint_schema["discriminator"]["propertyName"], "object_type")
        # We don't care what the schema calls the individual serializers in discriminator.mapping,
        # but we do want to assert that they're the correct set of models
        self.assertEqual(
            set(connected_endpoint_schema["discriminator"]["mapping"].keys()),
            set(
                [
                    f"{model._meta.app_label}.{model._meta.model_name}"
                    for model in get_all_concrete_subclasses(PathEndpoint)
                ]
            ),
        )

    def test_cable__terminations_schema(self):
        """Test the polymorphic serializer for a Cable endpoint's `termination_a` and `termination_b` fields."""
        cable_schema = self.schemas["2.0"]["components"]["schemas"]["Cable"]
        self.assertEqual(
            cable_schema["properties"]["termination_a"],
            {"allOf": [{"$ref": "#/components/schemas/cable__termination_a"}], "readOnly": True},
        )
        self.assertEqual(
            cable_schema["properties"]["termination_b"],
            {"allOf": [{"$ref": "#/components/schemas/cable__termination_b"}], "readOnly": True},
        )

        termination_a_schema = self.schemas["2.0"]["components"]["schemas"]["cable__termination_a"]
        self.assertEqual(termination_a_schema["discriminator"]["propertyName"], "object_type")
        # We don't care what the schema calls the individual serializers in discriminator.mapping,
        # but we do want to assert that they're the correct set of models
        self.assertEqual(
            set(termination_a_schema["discriminator"]["mapping"].keys()),
            set(
                [
                    f"{model._meta.app_label}.{model._meta.model_name}"
                    for model in get_all_concrete_subclasses(CableTermination)
                ]
            ),
        )

        # Schema for `termination_b` should be the same as `termination_a`.
        termination_b_schema = self.schemas["2.0"]["components"]["schemas"]["cable__termination_b"]
        self.assertEqual(termination_a_schema, termination_b_schema)
