from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.testing.schema import OpenAPISchemaTestCases
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery


class ExtrasOpenAPISchemaTestCase(OpenAPISchemaTestCases.BaseSchemaTestCase):
    """Test cases for the OpenAPI schema representation of various Extras data."""

    def test_config_context_owner_schema(self):
        """Test the polymorphic serializer for a ConfigContext endpoint's `owner` field."""
        config_context_schema = self.get_component_schema("ConfigContext")
        self.assert_nullable_property(config_context_schema, "owner")
        self.assert_read_only_property(config_context_schema, "owner")
        component_name = self.get_property_ref_component_name(config_context_schema, "owner")

        owner_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            owner_schema, models=FeatureQuery("config_context_owners").list_subclasses()
        )

    def test_config_context_schema_owner_schema(self):
        """Test the polymorphic serializer for a ConfigContextSchema endpoint's `owner` field."""
        config_context_schema_schema = self.get_component_schema("ConfigContextSchema")
        self.assert_nullable_property(config_context_schema_schema, "owner")
        self.assert_read_only_property(config_context_schema_schema, "owner")
        component_name = self.get_property_ref_component_name(config_context_schema_schema, "owner")

        owner_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            # There isn't a separate FeatureQuery for config_context_schema_owners, it shares with config_context_owners
            owner_schema,
            models=FeatureQuery("config_context_owners").list_subclasses(),
        )

    def test_export_template_owner_schema(self):
        """Test the polymorphic serializer for an ExportTemplate endpoint's `owner` field."""
        export_template_schema = self.get_component_schema("ExportTemplate")
        self.assert_nullable_property(export_template_schema, "owner")
        self.assert_read_only_property(export_template_schema, "owner")
        component_name = self.get_property_ref_component_name(export_template_schema, "owner")

        owner_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            owner_schema, models=FeatureQuery("export_template_owners").list_subclasses()
        )

    # TODO test ImageAttachment.owner schema. Currently this is a hard-coded list of serializers, and so there's
    # no way to write a test without again hard-coding that list into the test.

    def test_note_assigned_object_schema(self):
        """Test the polymorphic serializer for a Note endpoint's `assigned_object` field."""
        note_schema = self.get_component_schema("Note")
        self.assert_nullable_property(note_schema, "assigned_object")
        self.assert_read_only_property(note_schema, "assigned_object")
        component_name = self.get_property_ref_component_name(note_schema, "assigned_object")

        assigned_object_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(assigned_object_schema, models=get_all_concrete_models(NotesMixin))

    def test_object_change_changed_object_schema(self):
        """Test the polymorphic serializer for an ObjectChange endpoint's `changed_object` field."""
        object_change_schema = self.get_component_schema("ObjectChange")
        self.assert_nullable_property(object_change_schema, "changed_object")
        self.assert_read_only_property(object_change_schema, "changed_object")
        component_name = self.get_property_ref_component_name(object_change_schema, "changed_object")

        changed_object_schema = self.get_component_schema(component_name)
        self.assert_component_mapped_by_object_type(
            changed_object_schema, models=ChangeLoggedModelsQuery().list_subclasses()
        )
