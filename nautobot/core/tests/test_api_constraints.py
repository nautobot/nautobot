"""Exercise database conflicts that occur after API input validation."""

from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, IntegrityError, transaction
from django.test import override_settings, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from nautobot.core.api.constraints import get_constraint_error
from nautobot.core.api.views import ModelViewSet
from nautobot.dcim.api.serializers import InterfaceSerializer
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleType,
    Rack,
)
from nautobot.extras.models import Role, Status
from nautobot.ipam.api.serializers import IPAddressToInterfaceSerializer
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Namespace, Prefix
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface


@skipUnless(connection.vendor in {"postgresql", "mysql"}, "Constraint translation supports PostgreSQL and MySQL")
class APIConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="constraint-tests", is_superuser=True)
        cls.status = Status.objects.create(name="Constraint test status")
        cls.role = Role.objects.create(name="Constraint test role")
        for model in (Device, Interface, Location, Module, Rack, Prefix, IPAddress, VirtualMachine, VMInterface):
            cls.status.content_types.add(ContentType.objects.get_for_model(model))
        cls.role.content_types.add(ContentType.objects.get_for_model(Device))
        cls.location_type = LocationType.objects.create(name="Constraint test location type")
        cls.location_type.content_types.add(
            ContentType.objects.get_for_model(Device), ContentType.objects.get_for_model(Rack)
        )
        cls.source, cls.destination = [
            Location.objects.create(name=name, location_type=cls.location_type, status=cls.status)
            for name in ("Constraint source", "Constraint destination")
        ]
        manufacturer = Manufacturer.objects.create(name="Constraint test manufacturer")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="Constraint test device", u_height=1
        )
        cls.tenant = Tenant.objects.create(name="Constraint test tenant")
        cls.device = cls.make_device("Constraint device", cls.source)
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Constraint test module")
        module_bay = ModuleBay.objects.create(parent_device=cls.device, position="A")
        cls.module = Module.objects.create(module_type=module_type, parent_module_bay=module_bay, status=cls.status)
        cls.interfaces = [
            Interface.objects.create(module=cls.module, name=name, type="virtual", status=cls.status)
            for name in ("existing", "change-first", "change-second")
        ]
        namespace = Namespace.objects.create(name="Constraint test namespace")
        prefix = Prefix.objects.create(prefix="192.0.2.0/24", namespace=namespace, status=cls.status)
        cls.ip = IPAddress.objects.create(address="192.0.2.1/24", parent=prefix, status=cls.status)
        cluster_type = ClusterType.objects.create(name="Constraint test cluster type")
        cluster = Cluster.objects.create(name="Constraint test cluster", cluster_type=cluster_type)
        vm = VirtualMachine.objects.create(name="Constraint test VM", cluster=cluster, status=cls.status)
        cls.vm_interface = VMInterface.objects.create(virtual_machine=vm, name="eth0", status=cls.status)

    @classmethod
    def make_device(cls, name, location, rack=None):
        return Device.objects.create(
            name=name,
            location=location,
            rack=rack,
            tenant=cls.tenant,
            device_type=cls.device_type,
            role=cls.role,
            status=cls.status,
        )

    def setUp(self):
        self.client = APIClient(HTTP_HOST="nautobot.example.com")
        self.client.force_authenticate(self.user)
        self.interface_url = reverse("dcim-api:interface-list")
        self.assignment_url = reverse("ipam-api:ipaddresstointerface-list")

    def interface_data(self, name):
        return {"name": name, "module": str(self.module.pk), "type": "virtual", "status": str(self.status.pk)}

    def device_interface_data(self, name):
        return {"name": name, "device": str(self.device.pk), "type": "virtual", "status": str(self.status.pk)}

    def test_interface_names_can_repeat_across_ownership_scopes(self):
        other_device = self.make_device("Other device", self.source)
        bay = ModuleBay.objects.create(parent_device=self.device, position="B")
        other_module = Module.objects.create(
            module_type=self.module.module_type, parent_module_bay=bay, status=self.status
        )
        data = [
            self.device_interface_data("shared"),
            self.interface_data("shared"),
            {**self.interface_data("shared"), "module": str(other_module.pk)},
            {**self.device_interface_data("shared"), "device": str(other_device.pk)},
        ]
        response = self.client.post(self.interface_url, data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Interface.objects.filter(device=self.device, name="shared").count(), 3)
        self.assertEqual(Interface.objects.filter(device=other_device, name="shared").count(), 1)

    def test_device_interface_bulk_update_conflict_rolls_back(self):
        interfaces = [
            Interface.objects.create(device=self.device, name=name, type="virtual", status=self.status)
            for name in ("a-first", "b-second")
        ]
        response = self.client.patch(
            self.interface_url,
            [{"id": str(interface.pk), "name": "same-new-name"} for interface in interfaces],
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        for interface, name in zip(interfaces, ("a-first", "b-second")):
            interface.refresh_from_db()
            self.assertEqual(interface.name, name)

    def test_device_interface_database_conflict_after_validation(self):
        Interface.objects.create(device=self.device, name="direct-existing", type="virtual", status=self.status)
        with patch.object(InterfaceSerializer, "validate", side_effect=lambda data: data):
            response = self.client.post(
                self.interface_url, self.device_interface_data("direct-existing"), format="json"
            )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("name", response.data)
        self.assertEqual(Interface.objects.filter(device=self.device, name="direct-existing").count(), 1)

    def test_breakout_children_do_not_get_separate_name_scopes(self):
        parents = [
            Interface.objects.create(device=self.device, name=name, type="100gbase-x-qsfp28", status=self.status)
            for name in ("trunk-1", "trunk-2")
        ]
        data = [
            {
                **self.device_interface_data("duplicate-child"),
                "parent_interface": str(parent.pk),
                "breakout_position": 1,
            }
            for parent in parents
        ]
        response = self.client.post(self.interface_url, data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Interface.objects.filter(device=self.device, name="duplicate-child").exists())

    def test_device_name_constraint_translation_executes_no_queries(self):
        Interface.objects.create(device=self.device, name="database-existing", type="virtual", status=self.status)
        with self.assertRaises(IntegrityError) as caught, transaction.atomic():
            Interface.objects.create(device=self.device, name="database-existing", type="virtual", status=self.status)
        with self.assertNumQueries(0):
            error = get_constraint_error(caught.exception, InterfaceSerializer())
            self.assertIsNotNone(error)
            self.assertIn("directly on this device", str(error.detail["name"]))

    def test_device_interface_update_database_conflict_rolls_back(self):
        first, second = [
            Interface.objects.create(device=self.device, name=name, type="virtual", status=self.status)
            for name in ("direct-first", "direct-second")
        ]
        with patch.object(InterfaceSerializer, "validate", side_effect=lambda data: data):
            response = self.client.patch(
                reverse("dcim-api:interface-detail", kwargs={"pk": second.pk}), {"name": first.name}, format="json"
            )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("name", response.data)
        second.refresh_from_db()
        self.assertEqual(second.name, "direct-second")

    def test_moving_module_interface_to_device_checks_name_scope(self):
        direct = Interface.objects.create(device=self.device, name="existing", type="virtual", status=self.status)
        with patch.object(InterfaceSerializer, "validate", side_effect=lambda data: data):
            response = self.client.patch(
                reverse("dcim-api:interface-detail", kwargs={"pk": self.interfaces[0].pk}),
                {"module": None},
                format="json",
            )
        self.assertEqual(response.status_code, 400, response.data)
        self.interfaces[0].refresh_from_db()
        self.assertEqual(self.interfaces[0].module_id, self.module.pk)
        self.assertEqual(Interface.objects.filter(device=self.device, name=direct.name).count(), 2)

    def test_device_name_constraint_preserves_database_name_comparisons(self):
        for name, equivalent in (("Case-name", "case-name"), ("accent-café", "accent-cafe")):
            with self.subTest(name=name):
                probe = Interface.objects.create(device=self.device, name=name, type="virtual", status=self.status)
                collision = Interface.objects.filter(pk=probe.pk, name=equivalent).exists()
                probe.delete()
                response = self.client.post(
                    self.interface_url,
                    [self.device_interface_data(name), self.device_interface_data(equivalent)],
                    format="json",
                )
                self.assertEqual(response.status_code, 400 if collision else 201, response.data)
                if collision:
                    self.assertFalse(Interface.objects.filter(device=self.device, name=name).exists())

    def test_device_name_scope_is_internal(self):
        from nautobot.core.models.utils import serialize_object
        from nautobot.dcim.graphql.types import InterfaceType

        response = self.client.post(self.interface_url, self.device_interface_data("internal-scope"), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("_device_name_scope", response.data)
        self.assertNotIn("_device_name_scope", InterfaceType._meta.fields)
        interface = Interface.objects.get(pk=response.data["id"])
        self.assertNotIn("_device_name_scope", serialize_object(interface))

    def assignment_data(self, virtual=False):
        return {
            "ip_address": str(self.ip.pk),
            "vm_interface" if virtual else "interface": str(self.vm_interface.pk if virtual else self.interfaces[0].pk),
        }

    def test_bulk_device_interface_create_conflict_rolls_back_entire_list(self):
        # Both records pass validation before either is saved.
        data = self.device_interface_data("duplicate")
        response = self.client.post(self.interface_url, [data, data], format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("name", response.data)
        self.assertFalse(Interface.objects.filter(device=self.device, name="duplicate").exists())

    def test_bulk_ip_assignment_conflict_rolls_back_entire_list(self):
        for virtual in (False, True):
            with self.subTest(virtual=virtual):
                data = self.assignment_data(virtual)
                response = self.client.post(self.assignment_url, [data, data], format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("__all__", response.data)
                self.assertIn("already exists", str(response.data))
                self.assertFalse(IPAddressToInterface.objects.filter(ip_address=self.ip).exists())

    def test_bulk_ip_assignment_database_conflict_rolls_back_entire_list(self):
        for virtual in (False, True):
            with self.subTest(virtual=virtual):
                data = self.assignment_data(virtual)
                # Simulate a race past both serializer and pre_save validation.
                # The real database constraint remains enabled.
                with patch.object(IPAddressToInterface, "full_clean"):
                    response = self.client.post(self.assignment_url, [data, data], format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("non_field_errors", response.data)
                self.assertIn("already assigned", str(response.data))
                self.assertFalse(IPAddressToInterface.objects.filter(ip_address=self.ip).exists())

    def test_bulk_module_interface_conflict_rolls_back_entire_list(self):
        data = {"name": "duplicate", "module": str(self.module.pk), "type": "virtual", "status": str(self.status.pk)}
        response = self.client.post(self.interface_url, [data, data], format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("on this module", str(response.data))
        self.assertFalse(Interface.objects.filter(module=self.module, name="duplicate").exists())

    def test_save_validation_error_rolls_back_bulk_update(self):
        original_update = InterfaceSerializer.update

        def update(serializer, instance, validated_data):
            instance = original_update(serializer, instance, validated_data)
            if instance.pk == self.interfaces[2].pk:
                raise DjangoValidationError({"description": "Invalid after save"})
            return instance

        data = [{"id": str(obj.pk), "description": "updated"} for obj in self.interfaces[1:]]
        with patch.object(InterfaceSerializer, "update", update):
            response = self.client.patch(self.interface_url, data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data, {"description": ["Invalid after save"]})
        for obj in self.interfaces[1:]:
            obj.refresh_from_db()
            self.assertEqual(obj.description, "")

    def test_detail_create_conflict_after_validation(self):
        # Simulate the state changing after validation: leave field validation
        # enabled, but allow the model conflict to reach the INSERT.
        with patch.object(InterfaceSerializer, "validate", side_effect=lambda data: data):
            response = self.client.post(self.interface_url, self.interface_data("existing"), format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("name", response.data)
        self.assertEqual(Interface.objects.filter(device=self.device, name="existing").count(), 1)

    def test_detail_update_conflict_after_validation(self):
        url = reverse("dcim-api:interface-detail", kwargs={"pk": self.interfaces[1].pk})
        with patch.object(InterfaceSerializer, "validate", side_effect=lambda data: data):
            response = self.client.patch(url, {"name": "existing"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.interfaces[1].refresh_from_db()
        self.assertEqual(self.interfaces[1].name, "change-first")

    def test_bulk_update_conflict_rolls_back_earlier_updates(self):
        data = [
            {"id": str(self.interfaces[1].pk), "name": "first-updated"},
            {"id": str(self.interfaces[2].pk), "name": "existing"},
        ]
        with patch.object(InterfaceSerializer, "validate", side_effect=lambda attrs: attrs):
            response = self.client.patch(self.interface_url, data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        for obj, original_name in zip(self.interfaces[1:], ("change-first", "change-second")):
            obj.refresh_from_db()
            self.assertEqual(obj.name, original_name)

    def test_rack_relocation_reports_child_conflict_and_rolls_back(self):
        rack = Rack.objects.create(name="Conflict rack", location=self.source, status=self.status)
        moved = self.make_device("Duplicate child", self.source, rack)
        self.make_device("Duplicate child", self.destination)
        url = reverse("dcim-api:rack-detail", kwargs={"pk": rack.pk})
        response = self.client.patch(url, {"location": str(self.destination.pk)}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("location", response.data)
        self.assertIn("Cannot move device Duplicate child", str(response.data))
        rack.refresh_from_db()
        moved.refresh_from_db()
        self.assertEqual(rack.location_id, self.source.pk)
        self.assertEqual(moved.location_id, self.source.pk)

    def test_bulk_rack_relocation_rolls_back_earlier_rack_and_children(self):
        # Name ordering makes the successful rack update run first.
        racks = [
            Rack.objects.create(name=name, location=self.source, status=self.status)
            for name in ("A successful rack", "Z conflicting rack")
        ]
        children = [
            self.make_device(name, self.source, rack) for rack, name in zip(racks, ("Unique child", "Duplicate child"))
        ]
        self.make_device("Duplicate child", self.destination)
        data = [{"id": str(rack.pk), "location": str(self.destination.pk)} for rack in racks]
        response = self.client.patch(reverse("dcim-api:rack-list"), data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("location", response.data)
        for obj in [*racks, *children]:
            obj.refresh_from_db()
            self.assertEqual(obj.location_id, self.source.pk)

    def test_successful_saves_do_not_call_translator(self):
        with patch(
            "nautobot.core.api.views.get_constraint_error", side_effect=AssertionError("Unexpected translation")
        ):
            response = self.client.post(self.interface_url, self.interface_data("new-interface"), format="json")
            self.assertEqual(response.status_code, 201, response.data)
            url = reverse("dcim-api:interface-detail", kwargs={"pk": response.data["id"]})
            response = self.client.patch(url, {"description": "updated"}, format="json")
            self.assertEqual(response.status_code, 200, response.data)

    def test_real_constraint_translation_executes_no_queries(self):
        IPAddressToInterface.objects.create(ip_address=self.ip, interface=self.interfaces[0])
        try:
            with transaction.atomic():
                # Bypass pre_save validation to exercise the database race path.
                IPAddressToInterface.objects.bulk_create(
                    [IPAddressToInterface(ip_address=self.ip, interface=self.interfaces[0])]
                )
        except IntegrityError as error:
            with self.assertNumQueries(0):
                translated = get_constraint_error(error, IPAddressToInterfaceSerializer())
            self.assertIsNotNone(translated)
            self.assertIn("already assigned", str(translated.detail))
        else:
            self.fail("The duplicate assignment did not raise an IntegrityError")

    @skipUnless(connection.vendor == "postgresql", "PostgreSQL constraint diagnostics")
    def test_unknown_database_errors_are_not_translated(self):
        for sqlstate, table, constraint in (
            ("23503", "dcim_interface", "dcim_interface_module_name_unique"),
            ("23502", "dcim_interface", "dcim_interface_module_name_unique"),
            ("23505", "another_table", "dcim_interface_module_name_unique"),
            ("23505", "dcim_interface", "unknown_constraint"),
        ):
            with self.subTest(sqlstate=sqlstate, table=table, constraint=constraint):
                cause = Exception("Database detail must not determine the response")
                cause.diag = SimpleNamespace(sqlstate=sqlstate, table_name=table, constraint_name=constraint)
                error = IntegrityError("duplicate key value")
                error.__cause__ = cause
                with self.assertNumQueries(0):
                    self.assertIsNone(get_constraint_error(error, InterfaceSerializer()))
        self.assertIsNone(get_constraint_error(IntegrityError("No diagnostics"), InterfaceSerializer()))

    def test_rack_child_validation_preserves_original_detail(self):
        rack = Rack.objects.create(name="Validation rack", location=self.source, status=self.status)
        child = self.make_device("Named child", self.source, rack)
        error = DjangoValidationError({"name": "An existing child validation rule rejected this name."})
        with patch.object(Device, "save", side_effect=error):
            response = self.client.patch(
                reverse("dcim-api:rack-detail", kwargs={"pk": rack.pk}),
                {"location": str(self.destination.pk)},
                format="json",
            )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("Named child", str(response.data["location"]))
        self.assertIn("An existing child validation rule", str(response.data["location"]))
        rack.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(rack.location_id, self.source.pk)
        self.assertEqual(child.location_id, self.source.pk)

    @override_settings(DEVICE_UNIQUENESS="none")
    def test_rack_relocation_respects_disabled_device_uniqueness(self):
        rack = Rack.objects.create(name="Allowed rack", location=self.source, status=self.status)
        child = self.make_device("Duplicate child", self.source, rack)
        self.make_device("Duplicate child", self.destination)
        response = self.client.patch(
            reverse("dcim-api:rack-detail", kwargs={"pk": rack.pk}),
            {"location": str(self.destination.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        child.refresh_from_db()
        self.assertEqual(child.location_id, self.destination.pk)

    @skipUnless(connection.vendor == "mysql", "MySQL duplicate-key diagnostics")
    def test_mysql_duplicate_key_requires_exact_diagnostics(self):
        key = "dcim_interface.dcim_interface_module_name_unique"
        for args in (
            (),
            (1062,),
            (1062, None),
            (1062, b"Duplicate entry 'value' for key '" + key.encode() + b"'"),
            (1062, f"Duplicate entry 'value' for key '{key}'", "unexpected detail"),
            (1452, f"Duplicate entry 'value' for key '{key}'"),
            (1062, "Duplicate entry 'value' for key 'other_table.dcim_interface_module_name_unique'"),
            (1062, "Duplicate entry 'value' for key 'dcim_interface.unknown_constraint'"),
            (1062, "Duplicate entry 'value' for key 'dcim_interface_module_name_unique'"),
            (1062, f"Duplicate entry 'value' for key '{key}' trailing text"),
            (1062, f"Duplicate entry 'value' for key '{key}'\n"),
            (1062, f"Localized duplicate message '{key}'"),
            (1062, f"Duplicate entry 'value' for key '{key}' for key 'other_table.other_key'"),
        ):
            with self.subTest(args=args):
                error = IntegrityError(*args)
                error.__cause__ = Exception(*args)
                with self.assertNumQueries(0):
                    self.assertIsNone(get_constraint_error(error, InterfaceSerializer()))
        self.assertIsNone(
            get_constraint_error(IntegrityError(1062, f"Duplicate entry 'x' for key '{key}'"), InterfaceSerializer())
        )

    @skipUnless(connection.vendor == "mysql", "MySQL duplicate-key diagnostics")
    def test_mysql_duplicate_value_does_not_determine_constraint(self):
        for value in ("duplicate", "line\nbreak", "value' for key 'other_table.other_key"):
            with self.subTest(value=value):
                cause = Exception(
                    1062, f"Duplicate entry '{value}' for key 'dcim_interface.dcim_interface_module_name_unique'"
                )
                error = IntegrityError(*cause.args)
                error.__cause__ = cause
                with self.assertNumQueries(0):
                    translated = get_constraint_error(error, InterfaceSerializer(many=True))
                self.assertIsNotNone(translated)
                self.assertIn("name", translated.detail)

    @skipUnless(connection.vendor == "mysql", "MySQL duplicate-key diagnostics")
    def test_real_mysql_duplicate_value_cannot_spoof_mapped_constraint(self):
        name = "value' for key 'dcim_interface.dcim_interface_module_name_unique"
        Namespace.objects.create(name=name)
        try:
            with transaction.atomic():
                Namespace.objects.create(name=name)
        except IntegrityError as error:
            self.assertEqual(error.args[0], 1062)
            with self.assertNumQueries(0):
                self.assertIsNone(get_constraint_error(error, InterfaceSerializer()))
        else:
            self.fail("The duplicate namespace did not raise an IntegrityError")

    def test_unrecognized_integrity_error_propagates_from_save(self):
        error = IntegrityError("An internal failure")
        serializer = InterfaceSerializer(data=self.interface_data("new-interface"))
        serializer.is_valid(raise_exception=True)
        view = ModelViewSet()
        view.queryset = Interface.objects.all()
        with patch.object(InterfaceSerializer, "create", side_effect=error):
            with self.assertRaises(IntegrityError) as raised:
                view.perform_create(serializer)
        self.assertIs(raised.exception, error)
