from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery


class ExtrasOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various Extras data."""

    def test_config_context_owner_schema(self):
        """Test the polymorphic serializer for a ConfigContext endpoint's `owner` field."""
        self.validate_polymorphic_property(
            "ConfigContext",
            "owner",
            models=FeatureQuery("config_context_owners").list_subclasses(),
            nullable=True,
        )

    def test_config_context_schema_owner_schema(self):
        """Test the polymorphic serializer for a ConfigContextSchema endpoint's `owner` field."""
        self.validate_polymorphic_property(
            "ConfigContextSchema",
            "owner",
            # There isn't a separate FeatureQuery for config_context_schema_owners, it shares with config_context_owners
            models=FeatureQuery("config_context_owners").list_subclasses(),
            nullable=True,
        )

    def test_export_template_owner_schema(self):
        """Test the polymorphic serializer for an ExportTemplate endpoint's `owner` field."""
        self.validate_polymorphic_property(
            "ExportTemplate",
            "owner",
            models=FeatureQuery("export_template_owners").list_subclasses(),
            nullable=True,
        )

    # TODO test ImageAttachment.owner schema. Currently this is a hard-coded list of serializers, and so there's
    # no way to write a test without again hard-coding that list into the test.

    def test_note_assigned_object_schema(self):
        """Test the polymorphic serializer for a Note endpoint's `assigned_object` field."""
        self.validate_polymorphic_property(
            "Note",
            "assigned_object",
            models=get_all_concrete_models(NotesMixin),
            nullable=True,
        )

    def test_object_change_changed_object_schema(self):
        """Test the polymorphic serializer for an ObjectChange endpoint's `changed_object` field."""
        self.validate_polymorphic_property(
            "ObjectChange",
            "changed_object",
            models=ChangeLoggedModelsQuery().list_subclasses(),
            nullable=True,
        )
