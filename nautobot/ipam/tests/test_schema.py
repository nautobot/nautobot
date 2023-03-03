from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.dcim.models import BaseInterface


class IPAMOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various IPAM data."""

    def test_ip_address_assigned_object_schema(self):
        """Test the polymorphic serializer for an IPAddress endpoint's `assigned_object` field."""
        self.validate_polymorphic_property(
            "IPAddress",
            "assigned_object",
            models=get_all_concrete_models(BaseInterface),
            nullable=True,
        )
