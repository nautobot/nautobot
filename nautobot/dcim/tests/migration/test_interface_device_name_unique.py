from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection, IntegrityError, transaction
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class InterfaceDeviceNameMigrationTestCase(MigratorTestCase):
    migrate_from = ("dcim", "0097_virtualdevicecontext_controller_managed_device_group")
    migrate_to = ("dcim", "0098_interface_device_name_unique")

    def prepare(self):
        apps = self.old_state.apps
        status = apps.get_model("extras", "Status").objects.create(name="Migration status")
        role = apps.get_model("extras", "Role").objects.create(name="Migration role")
        location_type = apps.get_model("dcim", "LocationType").objects.create(name="Migration location type")
        location = apps.get_model("dcim", "Location").objects.create(
            name="Migration location", location_type=location_type, status=status
        )
        manufacturer = apps.get_model("dcim", "Manufacturer").objects.create(name="Migration manufacturer")
        device_type = apps.get_model("dcim", "DeviceType").objects.create(
            manufacturer=manufacturer, model="Migration device type"
        )
        device = apps.get_model("dcim", "Device").objects.create(
            name="Migration device", device_type=device_type, location=location, status=status, role=role
        )
        module_type = apps.get_model("dcim", "ModuleType").objects.create(
            manufacturer=manufacturer, model="Migration module type"
        )
        Interface = apps.get_model("dcim", "Interface")
        self.attributes = {"device_id": device.pk, "name": "shared", "type": "virtual", "status_id": status.pk}
        Interface.objects.create(**self.attributes)
        for position in ("A", "B"):
            bay = apps.get_model("dcim", "ModuleBay").objects.create(
                parent_device=device, name=position, position=position
            )
            module = apps.get_model("dcim", "Module").objects.create(
                module_type=module_type, parent_module_bay=bay, status=status
            )
            Interface.objects.create(**self.attributes, module=module)

        # A legacy duplicate must stop migration without changing any records.
        duplicate = Interface.objects.create(**self.attributes)
        migration = import_module("nautobot.dcim.migrations.0098_interface_device_name_unique")
        with self.assertRaisesRegex(RuntimeError, "Resolve these duplicates"):
            migration.check_device_interface_names(apps, SimpleNamespace(connection=connection))
        self.assertEqual(Interface.objects.filter(name="shared").count(), 4)
        duplicate.delete()
        # MySQL 8.0.11 supports generated columns but not functional indexes.
        # The migration must work without expression-index support.
        feature = patch.object(connection.features, "supports_expression_indexes", False)
        feature.start()
        self.addCleanup(feature.stop)

    def test_constraint_preserves_module_names_and_can_be_reversed(self):
        Interface = self.new_state.apps.get_model("dcim", "Interface")
        self.assertEqual(Interface.objects.filter(name="shared").count(), 3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Interface.objects.create(**self.attributes)

        old_state = self._migrator.apply_tested_migration(self.migrate_from)
        old_interface = old_state.apps.get_model("dcim", "Interface")
        duplicate = old_interface.objects.create(**self.attributes)
        duplicate.delete()
        self._migrator.apply_tested_migration(self.migrate_to)
