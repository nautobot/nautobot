from unittest import skip, skipIf

from django.db import connection

from nautobot.core.testing.migrations import NautobotDataMigrationTest
from nautobot.extras.choices import CustomFieldTypeChoices


# https://github.com/nautobot/nautobot/issues/3435
@skipIf(
    connection.vendor != "postgresql",
    "mysql does not support rollbacks",
)
@skip("test skipped until base test can be fixed to handle new migrations")
class CustomFieldDataMigrationTest(NautobotDataMigrationTest):
    migrate_from = [("extras", "0075_rename_slug_to_key_for_custom_field")]
    migrate_to = [("extras", "0076_migrate_custom_field_data")]

    def populateDataBeforeMigration(self, installed_apps):
        """populate CustomField data pre-migrations"""
        self.custom_field = installed_apps.get_model("extras", "CustomField")
        self.location = installed_apps.get_model("dcim", "Location")
        self.location_type = installed_apps.get_model("dcim", "LocationType")
        self.content_type = installed_apps.get_model("contenttypes", "ContentType")
        self.location_ct = self.content_type.objects.get_for_model(self.location)

        location_type = self.location_type.objects.create(name="Test Location Type 1")

        self.locations = (
            self.location.objects.create(
                location_type=location_type,
                name="Test Location 1",
            ),
            self.location.objects.create(
                location_type=location_type,
                name="Test Location 2",
            ),
            self.location.objects.create(
                location_type=location_type,
                name="Test Location 3",
            ),
        )

        self.custom_fields = (
            self.custom_field.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                name="Text Custom Field 1",
                default="value_1",
                key="text_custom_field_1",
            ),
            self.custom_field.objects.create(
                type=CustomFieldTypeChoices.TYPE_SELECT,
                name="Text Custom Field 2",
                default="value_2",
                key="text_custom_field_2",
            ),
            self.custom_field.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                name="Text Custom Field 3",
                default="value_1",
                key="text_custom_field_3",
            ),
            self.custom_field.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                name="Text Custom Field 4",
                default="value_3",
                key="text_custom_field_4",
            ),
            self.custom_field.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                name="123 main ave",
                default="value_3",
                key="123_main_ave",
            ),
            self.custom_field.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                name="456 main ave",
                default="value_3",
                key=" 456-main_ave",
            ),
        )

        for cf in self.custom_fields:
            cf.content_types.set([self.location_ct])

        self.locations[0]._custom_field_data = {"Text Custom Field 1": "ABC", "Text Custom Field 2": "Bar"}
        self.locations[0].save()
        self.locations[1]._custom_field_data = {
            "Text Custom Field 1": "ABC",
            "Text Custom Field 3": "Bar",
            "Text Custom Field 4": "FOO",
            "123 main ave": "New Address",
            "456 main ave": "Old Address",
        }
        self.locations[1].save()
        self.locations[2]._custom_field_data = {
            "Text Custom Field 1": "ABC",
            "Text Custom Field 2": "Bar",
            "Text Custom Field 3": "FOO",
            "123 main ave": "New Address",
            "456 main ave": "Old Address",
        }
        self.locations[2].save()

    def test_label_field_populated_correctly(self):
        for cf in self.custom_field.objects.exclude(label="Example Plugin Automatically Added Custom Field"):
            self.assertEqual(cf.name, cf.label)

    def test_key_field_is_graphql_safe(self):
        cf_1 = self.custom_field.objects.get(name="123 main ave")
        cf_2 = self.custom_field.objects.get(name="456 main ave")
        self.assertEqual(cf_1.key, "a123_main_ave")
        self.assertEqual(cf_2.key, "a_456_main_ave")

    @skip("Something bad is happening with the test data, suspecting bad merge")
    def test_custom_field_data_populated_correctly(self):
        location_0 = self.location.objects.get(name="Test Location 1")
        self.assertEqual(
            location_0._custom_field_data,
            {
                "a123_main_ave": None,
                "a_456_main_ave": None,
                "example_plugin_auto_custom_field": None,
                "text_custom_field_1": "ABC",
                "text_custom_field_2": "Bar",
                "text_custom_field_3": None,
                "text_custom_field_4": None,
            },
        )
        location_1 = self.location.objects.get(name="Test Location 2")
        print(location_1._custom_field_data)
        self.assertEqual(
            location_1._custom_field_data,
            {
                "a123_main_ave": "New Address",
                "a_456_main_ave": "Old Address",
                "example_plugin_auto_custom_field": None,
                "text_custom_field_1": "ABC",
                "text_custom_field_2": None,
                "text_custom_field_3": "Bar",
                "text_custom_field_4": "FOO",
            },
        )
        location_2 = self.location.objects.get(name="Test Location 3")
        self.assertEqual(
            location_2._custom_field_data,
            {
                "a123_main_ave": "New Address",
                "a_456_main_ave": "Old Address",
                "example_plugin_auto_custom_field": None,
                "text_custom_field_1": "ABC",
                "text_custom_field_2": "Bar",
                "text_custom_field_3": "FOO",
                "text_custom_field_4": None,
            },
        )
