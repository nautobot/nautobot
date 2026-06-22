from django_test_migrations.contrib.unittest_case import MigratorTestCase


class Fix128GfcTypoMigrationTestCase(MigratorTestCase):
    # Target the migration immediately preceding yours, and your new migration
    migrate_from = ("dcim", "0084_add_module_type_image_support")
    migrate_to = ("dcim", "0085_fix_128gfc_qsfp28_typo")

    def prepare(self):
        """Set up database data with the old incorrect type before migration runs."""
        Manufacturer = self.old_state.apps.get_model("dcim", "Manufacturer")
        DeviceType = self.old_state.apps.get_model("dcim", "DeviceType")
        InterfaceTemplate = self.old_state.apps.get_model("dcim", "InterfaceTemplate")

        # Establish minimal parent dependencies required by the database schema
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Test Switch Model")

        # Instantiate a template with the old typo slug
        self.template_typo = InterfaceTemplate.objects.create(
            device_type=device_type, name="FibreChannel1/1", type="128gfc-sfp28"
        )

    def test_migration(self):
        """Verify that records were successfully converted to the new type."""
        Interface = self.new_state.apps.get_model("dcim", "Interface")
        InterfaceTemplate = self.new_state.apps.get_model("dcim", "InterfaceTemplate")

        # Assert no instances containing the old typo string remain
        self.assertEqual(Interface.objects.filter(type="128gfc-sfp28").count(), 0)
        self.assertEqual(InterfaceTemplate.objects.filter(type="128gfc-sfp28").count(), 0)

        # Verify our prepared record has successfully evolved to the corrected slug
        updated_template = InterfaceTemplate.objects.get(name="FibreChannel1/1")
        self.assertEqual(updated_template.type, "128gfc-qsfp28")
