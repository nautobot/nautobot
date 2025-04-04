from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.dcim.models import CableTermination, PathEndpoint


class DCIMOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various DCIM data."""

    def test_cable_termination_cable_peer_schema(self):
        """Test the polymorphic serializer for a CableTermination endpoint's `cable_peer` field."""
        # We could test each CableTermination subclass's schema but they're all derived from a common base,
        # so it'd be a waste of time. Just pick Interface arbitrarily.
        self.validate_polymorphic_property(
            "Interface",
            "cable_peer",
            models=get_all_concrete_models(CableTermination),
            nullable=True,
        )

    def test_path_endpoint_connected_endpoint_schema(self):
        """Test the polymorphic serializer for a PathEndpoint endpoint's `connected_endpoint` field."""
        # We could test each PathEndpoint subclass's schema but they're all derived from a common base class,
        # so it'd be a waste of time. Just pick Interface arbitrarily.
        self.validate_polymorphic_property(
            "Interface",
            "connected_endpoint",
            models=get_all_concrete_models(PathEndpoint),
            nullable=True,
        )

    def test_cable_terminations_schema(self):
        """Test the polymorphic serializer for a Cable endpoint's `termination_a` and `termination_b` fields."""
        termination_a_ref_name, _ = self.validate_polymorphic_property(
            "Cable",
            "termination_a",
            models=get_all_concrete_models(CableTermination),
        )
        termination_b_ref_name, _ = self.validate_polymorphic_property(
            "Cable",
            "termination_b",
            models=get_all_concrete_models(CableTermination),
        )
        # both terminations should reference the same schema component since they're interchangeable.
        self.assertEqual(termination_a_ref_name, termination_b_ref_name)

    def test_cable_path_endpoints_schema(self):
        """Test the polymorphic serializer for a CablePath endpoint's `origin` and `destination` fields."""
        origin_ref_name, _ = self.validate_polymorphic_property(
            "CablePath",
            "origin",
            models=get_all_concrete_models(PathEndpoint),
        )
        destination_ref_name, _ = self.validate_polymorphic_property(
            "CablePath",
            "destination",
            models=get_all_concrete_models(PathEndpoint),
            nullable=True,
        )
        # both fields should reference the same schema component since they're interchangeable.
        self.assertEqual(origin_ref_name, destination_ref_name)

    def test_cable_path_path_schema(self):
        """Test the polymorphic serializer for a CablePath endpoint's `path` field."""
        self.validate_polymorphic_property(
            "CablePath",
            "path",
            models=get_all_concrete_models(CableTermination),
            many=True,
        )
