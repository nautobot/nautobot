from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.dcim.models import BaseInterface


class IPAMOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various IPAM data."""

    def test_ip_address_assigned_object_schema(self):
        """Test the polymorphic serializer for an IPAddress endpoint's `assigned_object` field."""
        ip_address_schema = self.get_component_schema("IPAddress")
        self.assert_nullable_property(ip_address_schema, "assigned_object")
        self.assert_read_only_property(ip_address_schema, "assigned_object")
        component_name = self.get_property_ref_component_name(ip_address_schema, "assigned_object")

        assigned_object_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            assigned_object_schema, models=get_all_concrete_models(BaseInterface)
        )
