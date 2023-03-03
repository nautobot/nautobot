from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.dcim.models import CableTermination, PathEndpoint


class DCIMOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various DCIM data."""

    def test_cable_termination_cable_peer_schema(self):
        """Test the polymorphic serializer for a CableTermination endpoint's `cable_peer` field."""
        # We could test each CableTermination subclass's schema but they're all derived from a common base,
        # so it'd be a waste of time. Just pick Interface arbitrarily.
        interface_schema = self.get_component_schema("Interface")
        self.assert_nullable_property(interface_schema, "cable_peer")
        self.assert_read_only_property(interface_schema, "cable_peer")
        component_name = self.get_property_ref_component_name(interface_schema, "cable_peer")

        cable_peer_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(cable_peer_schema, models=get_all_concrete_models(CableTermination))

    def test_path_endpoint_connected_endpoint_schema(self):
        """Test the polymorphic serializer for a PathEndpoint endpoint's `connected_endpoint` field."""
        # We could test each PathEndpoint subclass's schema but they're all derived from a common base class,
        # so it'd be a waste of time. Just pick Interface arbitrarily.
        interface_schema = self.get_component_schema("Interface")
        self.assert_nullable_property(interface_schema, "connected_endpoint")
        self.assert_read_only_property(interface_schema, "connected_endpoint")
        component_name = self.get_property_ref_component_name(interface_schema, "connected_endpoint")

        connected_endpoint_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            connected_endpoint_schema, models=get_all_concrete_models(PathEndpoint)
        )

    def test_cable_terminations_schema(self):
        """Test the polymorphic serializer for a Cable endpoint's `termination_a` and `termination_b` fields."""
        cable_schema = self.get_component_schema("Cable")
        self.assert_not_nullable_property(cable_schema, "termination_a")
        self.assert_not_nullable_property(cable_schema, "termination_b")
        self.assert_read_only_property(cable_schema, "termination_a")
        self.assert_read_only_property(cable_schema, "termination_b")
        # both terminations should reference the same schema component since they're interchangeable.
        component_name = self.get_property_ref_component_name(cable_schema, "termination_a")
        self.assertEqual(component_name, self.get_property_ref_component_name(cable_schema, "termination_b"))

        termination_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            termination_schema, models=get_all_concrete_models(CableTermination)
        )

    def test_cable_path_endpoints_schema(self):
        """Test the polymorphic serializer for a CablePath endpoint's `origin` and `destination` fields."""
        cable_path_schema = self.get_component_schema("CablePath")
        self.assert_not_nullable_property(cable_path_schema, "origin")
        self.assert_nullable_property(cable_path_schema, "destination")
        self.assert_read_only_property(cable_path_schema, "origin")
        self.assert_read_only_property(cable_path_schema, "destination")
        # both fields should reference the same schema component since they're interchangeable.
        component_name = self.get_property_ref_component_name(cable_path_schema, "origin")
        self.assertEqual(component_name, self.get_property_ref_component_name(cable_path_schema, "destination"))

        endpoint_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(endpoint_schema, models=get_all_concrete_models(PathEndpoint))

    def test_cable_path_path_schema(self):
        """Test the polymorphic serializer for a CablePath endpoint's `path` field."""
        cable_path_schema = self.get_component_schema("CablePath")
        self.assert_read_only_property(cable_path_schema, "path")
        self.assertEqual("array", self.get_schema_property(cable_path_schema, "path").get("type"))
        component_name = self.get_property_ref_component_name(cable_path_schema, "path")

        path_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(path_schema, models=get_all_concrete_models(CableTermination))
