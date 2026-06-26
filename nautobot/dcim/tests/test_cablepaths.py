from io import StringIO
from unittest import mock
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.dcim import signals as dcim_signals
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Cable,
    CablePath,
    CableToCableTermination,
    CableType,
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceType,
    FrontPort,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    PowerFeed,
    PowerOutlet,
    PowerPanel,
    PowerPort,
    RearPort,
)
from nautobot.dcim.signals import create_cablepath, defer_cable_path_rebuilds, rebuild_paths
from nautobot.dcim.utils import disconnect_termination, object_to_path_node, path_node_to_object
from nautobot.extras.models import Role, Status


class CablePathTestCase(TestCase):
    """
    Test Nautobot's ability to trace and retrace CablePaths in response to data model changes. Tests are numbered
    as follows:

        1XX: Test direct connections between different endpoint types
        2XX: Test different cable topologies
        3XX: Test responses to changes in existing objects
    """

    @classmethod
    def setUpTestData(cls):
        # Create a single device that will hold all components
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Test Device")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            location=cls.location,
            device_type=device_type,
            role=device_role,
            name="Test Device",
            status=device_status,
        )

        cls.powerpanel = PowerPanel.objects.create(location=cls.location, name="Power Panel")

        provider = Provider.objects.first()
        circuit_type = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()
        cls.circuit = Circuit.objects.create(
            provider=provider, circuit_type=circuit_type, cid="Circuit 1", status=circuit_status
        )

        cls.interface_status = Status.objects.get_for_model(Interface).first()

        cls.statuses = Status.objects.get_for_model(Cable)
        cls.status = cls.statuses.get(name="Connected")
        cls.status_planned = cls.statuses.get(name="Planned")

        # create a Cable that is not contained in any CablePath
        cls.dneCable = Cable(status=cls.status)

    def assertPathExists(self, origin, destination, path=None, is_active=None, msg=None):
        """
        Assert that a CablePath from origin to destination with a specific intermediate path exists.

        :param origin: Originating endpoint
        :param destination: Terminating endpoint, or None
        :param path: Sequence of objects comprising the intermediate path (optional)
        :param is_active: Boolean indicating whether the end-to-end path is complete and active (optional)
        :param msg: Custom failure message (optional)

        :return: The matching CablePath (if any)
        """
        kwargs = {
            "origin_type": ContentType.objects.get_for_model(origin),
            "origin_id": origin.pk,
        }
        if destination is not None:
            kwargs["destination_type"] = ContentType.objects.get_for_model(destination)
            kwargs["destination_id"] = destination.pk
        else:
            kwargs["destination_type__isnull"] = True
            kwargs["destination_id__isnull"] = True
        if path is not None:
            kwargs["path"] = [object_to_path_node(obj) for obj in path]
        if is_active is not None:
            kwargs["is_active"] = is_active
        if msg is None:
            if destination is not None:
                msg = f"Missing path from {origin} to {destination}"
            else:
                msg = f"Missing partial path originating from {origin}"

        cablepath = CablePath.objects.filter(**kwargs).first()
        self.assertIsNotNone(cablepath, msg=msg)

        return cablepath

    def assertPathIsSet(self, origin, cablepath, msg=None):
        """
        Assert that a specific CablePath instance is set as the path on the origin.

        :param origin: The originating path endpoint
        :param cablepath: The CablePath instance originating from this endpoint
        :param msg: Custom failure message (optional)
        """
        if msg is None:
            msg = f"Path #{cablepath.pk} not set on originating endpoint {origin}"
        primary_path = origin.cable_paths.first()
        self.assertIsNotNone(primary_path, msg=msg)
        self.assertEqual(primary_path.pk, cablepath.pk, msg=msg)

    def assertPathIsNotSet(self, origin, msg=None):
        """
        Assert that a specific CablePath instance is set as the path on the origin.

        :param origin: The originating path endpoint
        :param msg: Custom failure message (optional)
        """
        primary_path = origin.cable_paths.first()
        if msg is None:
            msg = f"Path #{primary_path.pk if primary_path else None} set as origin on {origin}; should be None!"
        self.assertIsNone(primary_path, msg=msg)

    def assertContainedByPath(self, path_parts):
        """
        For each {part: count} in `path_parts`, assert that part is contained in
        count number of CablePaths.

        :param path_parts: A dictionary of CablePath parts mapped to their counts
        """
        for part, count in path_parts.items():
            self.assertEqual(CablePath.objects.filter(path__contains=part).count(), count)
        self.assertEqual(CablePath.objects.filter(path__contains=self.dneCable).count(), 0)

    def test_101_interface_to_interface(self):
        """
        [IF1] --C1-- [IF2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)

        # Create cable 1
        cable1 = Cable(termination_a=interface1, termination_b=interface2, status=self.status)
        cable1.save()
        path1 = self.assertPathExists(origin=interface1, destination=interface2, path=(cable1,), is_active=True)
        path2 = self.assertPathExists(origin=interface2, destination=interface1, path=(cable1,), is_active=True)
        self.assertEqual(CablePath.objects.count(), 2)
        interface1.refresh_from_db()
        interface2.refresh_from_db()
        self.assertPathIsSet(interface1, path1)
        self.assertPathIsSet(interface2, path2)

        self.assertContainedByPath({cable1: 2})

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_102_consoleport_to_consoleserverport(self):
        """
        [CP1] --C1-- [CSP1]
        """
        consoleport1 = ConsolePort.objects.create(device=self.device, name="Console Port 1")
        consoleserverport1 = ConsoleServerPort.objects.create(device=self.device, name="Console Server Port 1")

        # Create cable 1
        cable1 = Cable(
            termination_a=consoleport1,
            termination_b=consoleserverport1,
            status=self.status,
        )
        cable1.save()
        path1 = self.assertPathExists(
            origin=consoleport1,
            destination=consoleserverport1,
            path=(cable1,),
            is_active=True,
        )
        path2 = self.assertPathExists(
            origin=consoleserverport1,
            destination=consoleport1,
            path=(cable1,),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 2)
        consoleport1.refresh_from_db()
        consoleserverport1.refresh_from_db()
        self.assertPathIsSet(consoleport1, path1)
        self.assertPathIsSet(consoleserverport1, path2)

        self.assertContainedByPath({cable1: 2})

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_103_powerport_to_poweroutlet(self):
        """
        [PP1] --C1-- [PO1]
        """
        powerport1 = PowerPort.objects.create(device=self.device, name="Power Port 1")
        poweroutlet1 = PowerOutlet.objects.create(device=self.device, name="Power Outlet 1")

        # Create cable 1
        cable1 = Cable(termination_a=powerport1, termination_b=poweroutlet1, status=self.status)
        cable1.save()
        path1 = self.assertPathExists(origin=powerport1, destination=poweroutlet1, path=(cable1,), is_active=True)
        path2 = self.assertPathExists(origin=poweroutlet1, destination=powerport1, path=(cable1,), is_active=True)
        self.assertEqual(CablePath.objects.count(), 2)
        powerport1.refresh_from_db()
        poweroutlet1.refresh_from_db()
        self.assertPathIsSet(powerport1, path1)
        self.assertPathIsSet(poweroutlet1, path2)

        self.assertContainedByPath({cable1: 2})

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_104_powerport_to_powerfeed(self):
        """
        [PP1] --C1-- [PF1]
        """
        powerport1 = PowerPort.objects.create(device=self.device, name="Power Port 1")
        powerfeed_status = Status.objects.get_for_model(PowerFeed).first()
        powerfeed1 = PowerFeed.objects.create(power_panel=self.powerpanel, name="Power Feed 1", status=powerfeed_status)

        # Create cable 1
        cable1 = Cable(termination_a=powerport1, termination_b=powerfeed1, status=self.status)
        cable1.save()
        path1 = self.assertPathExists(origin=powerport1, destination=powerfeed1, path=(cable1,), is_active=True)
        path2 = self.assertPathExists(origin=powerfeed1, destination=powerport1, path=(cable1,), is_active=True)
        self.assertEqual(CablePath.objects.count(), 2)
        powerport1.refresh_from_db()
        powerfeed1.refresh_from_db()
        self.assertPathIsSet(powerport1, path1)
        self.assertPathIsSet(powerfeed1, path2)

        self.assertContainedByPath({cable1: 2})

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_105_interface_to_circuittermination(self):
        """
        [IF1] --C1-- [CT1A]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        circuittermination1 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="A"
        )

        # Create cable 1
        cable1 = Cable(
            termination_a=interface1,
            termination_b=circuittermination1,
            status=self.status,
        )
        cable1.save()
        path1 = self.assertPathExists(
            origin=interface1,
            destination=circuittermination1,
            path=(cable1,),
            is_active=True,
        )
        path2 = self.assertPathExists(
            origin=circuittermination1,
            destination=interface1,
            path=(cable1,),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 2)
        interface1.refresh_from_db()
        circuittermination1.refresh_from_db()
        self.assertPathIsSet(interface1, path1)
        self.assertPathIsSet(circuittermination1, path2)

        self.assertContainedByPath({cable1: 2})

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_201_single_path_via_pass_through(self):
        """
        [IF1] --C1-- [FP1] [RP1] --C2-- [IF2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=1)
        frontport1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1",
            rear_port=rearport1,
            rear_port_position=1,
        )

        # Create cable 1
        cable1 = Cable(termination_a=interface1, termination_b=frontport1, status=self.status)
        cable1.save()
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, frontport1, rearport1),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 1)

        # Create cable 2
        cable2 = Cable(termination_a=rearport1, termination_b=interface2, status=self.status)
        cable2.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface2,
            path=(cable1, frontport1, rearport1, cable2),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable2, rearport1, frontport1, cable1),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 2)

        self.assertContainedByPath(
            {
                cable1: 2,
                rearport1: 2,
                frontport1: 2,
                cable2: 2,
            }
        )

        # Delete cable 2
        cable2.delete()
        path1 = self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, frontport1, rearport1),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 1)
        interface1.refresh_from_db()
        interface2.refresh_from_db()
        self.assertPathIsSet(interface1, path1)
        self.assertPathIsNotSet(interface2)

    def test_202_multiple_paths_via_pass_through(self):
        """
        [IF1] --C1-- [FP1:1] [RP1] --C3-- [RP2] [FP2:1] --C4-- [IF3]
        [IF2] --C2-- [FP1:2]                    [FP2:2] --C5-- [IF4]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        interface3 = Interface.objects.create(device=self.device, name="Interface 3", status=self.interface_status)
        interface4 = Interface.objects.create(device=self.device, name="Interface 4", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=4)
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=4)
        frontport1_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        frontport1_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:2",
            rear_port=rearport1,
            rear_port_position=2,
        )
        frontport2_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2:1",
            rear_port=rearport2,
            rear_port_position=1,
        )
        frontport2_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2:2",
            rear_port=rearport2,
            rear_port_position=2,
        )

        # Create cables 1-2
        cable1 = Cable(termination_a=interface1, termination_b=frontport1_1, status=self.status)
        cable1.save()
        cable2 = Cable(termination_a=interface2, termination_b=frontport1_2, status=self.status)
        cable2.save()
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, frontport1_1, rearport1),
            is_active=False,
        )
        self.assertPathExists(
            origin=interface2,
            destination=None,
            path=(cable2, frontport1_2, rearport1),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 2)

        # Create cable 3
        cable3 = Cable(termination_a=rearport1, termination_b=rearport2, status=self.status)
        cable3.save()
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, frontport1_1, rearport1, cable3, rearport2, frontport2_1),
            is_active=False,
        )
        self.assertPathExists(
            origin=interface2,
            destination=None,
            path=(cable2, frontport1_2, rearport1, cable3, rearport2, frontport2_2),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 2)

        # Create cables 4-5
        cable4 = Cable(termination_a=frontport2_1, termination_b=interface3, status=self.status)
        cable4.save()
        cable5 = Cable(termination_a=frontport2_2, termination_b=interface4, status=self.status)
        cable5.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface3,
            path=(
                cable1,
                frontport1_1,
                rearport1,
                cable3,
                rearport2,
                frontport2_1,
                cable4,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface4,
            path=(
                cable2,
                frontport1_2,
                rearport1,
                cable3,
                rearport2,
                frontport2_2,
                cable5,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface3,
            destination=interface1,
            path=(
                cable4,
                frontport2_1,
                rearport2,
                cable3,
                rearport1,
                frontport1_1,
                cable1,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface4,
            destination=interface2,
            path=(
                cable5,
                frontport2_2,
                rearport2,
                cable3,
                rearport1,
                frontport1_2,
                cable2,
            ),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 4)

        self.assertContainedByPath(
            {
                cable1: 2,
                cable2: 2,
                cable3: 4,
                cable4: 2,
                cable5: 2,
                frontport1_1: 2,
                frontport1_2: 2,
                frontport2_1: 2,
                frontport2_2: 2,
                rearport1: 4,
                rearport2: 4,
            }
        )

        # Delete cable 3
        cable3.delete()

        # Check for four partial paths; one from each interface
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=True).count(), 4)
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=False).count(), 0)
        # Path PKs change across a cable deletion (signal-driven rebuild replaces the rows
        # rather than updating in place); refetch the post-delete path for each origin.
        for origin in (interface1, interface2, interface3, interface4):
            origin.refresh_from_db()
            self.assertIsNotNone(origin.cable_paths.first())

    def test_203_multiple_paths_via_nested_pass_throughs(self):
        """
        [IF1] --C1-- [FP1:1] [RP1] --C3-- [FP2] [RP2] --C4-- [RP3] [FP3] --C5-- [RP4] [FP4:1] --C6-- [IF3]
        [IF2] --C2-- [FP1:2]                                                          [FP4:2] --C7-- [IF4]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        interface3 = Interface.objects.create(device=self.device, name="Interface 3", status=self.interface_status)
        interface4 = Interface.objects.create(device=self.device, name="Interface 4", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=4)
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=1)
        rearport3 = RearPort.objects.create(device=self.device, name="Rear Port 3", positions=1)
        rearport4 = RearPort.objects.create(device=self.device, name="Rear Port 4", positions=4)
        frontport1_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        frontport1_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:2",
            rear_port=rearport1,
            rear_port_position=2,
        )
        frontport2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2",
            rear_port=rearport2,
            rear_port_position=1,
        )
        frontport3 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 3",
            rear_port=rearport3,
            rear_port_position=1,
        )
        frontport4_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 4:1",
            rear_port=rearport4,
            rear_port_position=1,
        )
        frontport4_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 4:2",
            rear_port=rearport4,
            rear_port_position=2,
        )

        # Create cables 1-2, 6-7
        cable1 = Cable(termination_a=interface1, termination_b=frontport1_1, status=self.status)
        cable1.save()
        cable2 = Cable(termination_a=interface2, termination_b=frontport1_2, status=self.status)
        cable2.save()
        cable6 = Cable(termination_a=interface3, termination_b=frontport4_1, status=self.status)
        cable6.save()
        cable7 = Cable(termination_a=interface4, termination_b=frontport4_2, status=self.status)
        cable7.save()
        self.assertEqual(CablePath.objects.count(), 4)  # Four partial paths; one from each interface

        # Create cables 3 and 5
        cable3 = Cable(termination_a=rearport1, termination_b=frontport2, status=self.status)
        cable3.save()
        cable5 = Cable(termination_a=rearport4, termination_b=frontport3, status=self.status)
        cable5.save()
        self.assertEqual(CablePath.objects.count(), 4)  # Four (longer) partial paths; one from each interface

        # Create cable 4
        cable4 = Cable(termination_a=rearport2, termination_b=rearport3, status=self.status)
        cable4.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface3,
            path=(
                cable1,
                frontport1_1,
                rearport1,
                cable3,
                frontport2,
                rearport2,
                cable4,
                rearport3,
                frontport3,
                cable5,
                rearport4,
                frontport4_1,
                cable6,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface4,
            path=(
                cable2,
                frontport1_2,
                rearport1,
                cable3,
                frontport2,
                rearport2,
                cable4,
                rearport3,
                frontport3,
                cable5,
                rearport4,
                frontport4_2,
                cable7,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface3,
            destination=interface1,
            path=(
                cable6,
                frontport4_1,
                rearport4,
                cable5,
                frontport3,
                rearport3,
                cable4,
                rearport2,
                frontport2,
                cable3,
                rearport1,
                frontport1_1,
                cable1,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface4,
            destination=interface2,
            path=(
                cable7,
                frontport4_2,
                rearport4,
                cable5,
                frontport3,
                rearport3,
                cable4,
                rearport2,
                frontport2,
                cable3,
                rearport1,
                frontport1_2,
                cable2,
            ),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 4)

        self.assertContainedByPath(
            {
                cable1: 2,
                cable2: 2,
                cable3: 4,
                cable4: 4,
                cable5: 4,
                cable6: 2,
                cable7: 2,
                frontport1_1: 2,
                frontport1_2: 2,
                frontport2: 4,
                frontport3: 4,
                frontport4_1: 2,
                frontport4_2: 2,
                rearport1: 4,
                rearport2: 4,
                rearport3: 4,
                rearport4: 4,
            }
        )

        # Delete cable 3
        cable3.delete()

        # Check for four partial paths; one from each interface
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=True).count(), 4)
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=False).count(), 0)

    def test_204_multiple_paths_via_multiple_pass_throughs(self):
        """
        [IF1] --C1-- [FP1:1] [RP1] --C3-- [RP2] [FP2:1] --C4-- [FP3:1] [RP3] --C6-- [RP4] [FP4:1] --C7-- [IF3]
        [IF2] --C2-- [FP1:2]                    [FP2:1] --C5-- [FP3:1]                    [FP4:2] --C8-- [IF4]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        interface3 = Interface.objects.create(device=self.device, name="Interface 3", status=self.interface_status)
        interface4 = Interface.objects.create(device=self.device, name="Interface 4", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=4)
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=4)
        rearport3 = RearPort.objects.create(device=self.device, name="Rear Port 3", positions=4)
        rearport4 = RearPort.objects.create(device=self.device, name="Rear Port 4", positions=4)
        frontport1_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        frontport1_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:2",
            rear_port=rearport1,
            rear_port_position=2,
        )
        frontport2_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2:1",
            rear_port=rearport2,
            rear_port_position=1,
        )
        frontport2_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2:2",
            rear_port=rearport2,
            rear_port_position=2,
        )
        frontport3_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 3:1",
            rear_port=rearport3,
            rear_port_position=1,
        )
        frontport3_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 3:2",
            rear_port=rearport3,
            rear_port_position=2,
        )
        frontport4_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 4:1",
            rear_port=rearport4,
            rear_port_position=1,
        )
        frontport4_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 4:2",
            rear_port=rearport4,
            rear_port_position=2,
        )

        # Create cables 1-3, 6-8
        cable1 = Cable(termination_a=interface1, termination_b=frontport1_1, status=self.status)
        cable1.save()
        cable2 = Cable(termination_a=interface2, termination_b=frontport1_2, status=self.status)
        cable2.save()
        cable3 = Cable(termination_a=rearport1, termination_b=rearport2, status=self.status)
        cable3.save()
        cable6 = Cable(termination_a=rearport3, termination_b=rearport4, status=self.status)
        cable6.save()
        cable7 = Cable(termination_a=interface3, termination_b=frontport4_1, status=self.status)
        cable7.save()
        cable8 = Cable(termination_a=interface4, termination_b=frontport4_2, status=self.status)
        cable8.save()
        self.assertEqual(CablePath.objects.count(), 4)  # Four partial paths; one from each interface

        # Create cables 4 and 5
        cable4 = Cable(termination_a=frontport2_1, termination_b=frontport3_1, status=self.status)
        cable4.save()
        cable5 = Cable(termination_a=frontport2_2, termination_b=frontport3_2, status=self.status)
        cable5.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface3,
            path=(
                cable1,
                frontport1_1,
                rearport1,
                cable3,
                rearport2,
                frontport2_1,
                cable4,
                frontport3_1,
                rearport3,
                cable6,
                rearport4,
                frontport4_1,
                cable7,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface4,
            path=(
                cable2,
                frontport1_2,
                rearport1,
                cable3,
                rearport2,
                frontport2_2,
                cable5,
                frontport3_2,
                rearport3,
                cable6,
                rearport4,
                frontport4_2,
                cable8,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface3,
            destination=interface1,
            path=(
                cable7,
                frontport4_1,
                rearport4,
                cable6,
                rearport3,
                frontport3_1,
                cable4,
                frontport2_1,
                rearport2,
                cable3,
                rearport1,
                frontport1_1,
                cable1,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface4,
            destination=interface2,
            path=(
                cable8,
                frontport4_2,
                rearport4,
                cable6,
                rearport3,
                frontport3_2,
                cable5,
                frontport2_2,
                rearport2,
                cable3,
                rearport1,
                frontport1_2,
                cable2,
            ),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 4)

        self.assertContainedByPath(
            {
                cable1: 2,
                cable2: 2,
                cable3: 4,
                cable4: 2,
                cable5: 2,
                cable6: 4,
                cable7: 2,
                cable8: 2,
                rearport1: 4,
                rearport2: 4,
                rearport3: 4,
                rearport4: 4,
                frontport1_1: 2,
                frontport1_2: 2,
                frontport2_1: 2,
                frontport2_2: 2,
                frontport3_1: 2,
                frontport3_2: 2,
                frontport4_1: 2,
                frontport4_2: 2,
            }
        )

        # Delete cable 5
        cable5.delete()

        # Check for two complete paths (IF1 <--> IF2) and two partial (IF3 <--> IF4)
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=True).count(), 2)
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=False).count(), 2)

    def test_205_multiple_paths_via_patched_pass_throughs(self):
        """
        [IF1] --C1-- [FP1:1] [RP1] --C3-- [FP2] [RP2] --C4-- [RP3] [FP3:1] --C5-- [IF3]
        [IF2] --C2-- [FP1:2]                                       [FP3:2] --C6-- [IF4]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        interface3 = Interface.objects.create(device=self.device, name="Interface 3", status=self.interface_status)
        interface4 = Interface.objects.create(device=self.device, name="Interface 4", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=4)
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 5", positions=1)
        rearport3 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=4)
        frontport1_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        frontport1_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:2",
            rear_port=rearport1,
            rear_port_position=2,
        )
        frontport2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 5",
            rear_port=rearport2,
            rear_port_position=1,
        )
        frontport3_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2:1",
            rear_port=rearport3,
            rear_port_position=1,
        )
        frontport3_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2:2",
            rear_port=rearport3,
            rear_port_position=2,
        )

        # Create cables 1-2, 5-6
        cable1 = Cable(termination_a=interface1, termination_b=frontport1_1, status=self.status)  # IF1 -> FP1:1
        cable1.save()
        cable2 = Cable(termination_a=interface2, termination_b=frontport1_2, status=self.status)  # IF2 -> FP1:2
        cable2.save()
        cable5 = Cable(termination_a=interface3, termination_b=frontport3_1, status=self.status)  # IF3 -> FP3:1
        cable5.save()
        cable6 = Cable(termination_a=interface4, termination_b=frontport3_2, status=self.status)  # IF4 -> FP3:2
        cable6.save()
        self.assertEqual(CablePath.objects.count(), 4)  # Four partial paths; one from each interface

        # Create cables 3-4
        cable3 = Cable(termination_a=rearport1, termination_b=frontport2, status=self.status)  # RP1 -> FP2
        cable3.save()
        cable4 = Cable(termination_a=rearport2, termination_b=rearport3, status=self.status)  # RP2 -> RP3
        cable4.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface3,
            path=(
                cable1,
                frontport1_1,
                rearport1,
                cable3,
                frontport2,
                rearport2,
                cable4,
                rearport3,
                frontport3_1,
                cable5,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface4,
            path=(
                cable2,
                frontport1_2,
                rearport1,
                cable3,
                frontport2,
                rearport2,
                cable4,
                rearport3,
                frontport3_2,
                cable6,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface3,
            destination=interface1,
            path=(
                cable5,
                frontport3_1,
                rearport3,
                cable4,
                rearport2,
                frontport2,
                cable3,
                rearport1,
                frontport1_1,
                cable1,
            ),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface4,
            destination=interface2,
            path=(
                cable6,
                frontport3_2,
                rearport3,
                cable4,
                rearport2,
                frontport2,
                cable3,
                rearport1,
                frontport1_2,
                cable2,
            ),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 4)

        self.assertContainedByPath(
            {
                cable1: 2,
                cable2: 2,
                cable3: 4,
                cable4: 4,
                cable5: 2,
                cable6: 2,
                rearport1: 4,
                rearport2: 4,
                rearport3: 4,
                frontport1_1: 2,
                frontport1_2: 2,
                frontport2: 4,
                frontport3_1: 2,
                frontport3_2: 2,
            }
        )

        # Delete cable 3
        cable3.delete()

        # Check for four partial paths; one from each interface
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=True).count(), 4)
        self.assertEqual(CablePath.objects.filter(destination_id__isnull=False).count(), 0)

    def test_206_unidirectional_split_paths(self):
        """
        [IF1] --C1-- [RP1] [FP1:1] --C2-- [IF2]
                           [FP1:2] --C3-- [IF3]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        interface3 = Interface.objects.create(device=self.device, name="Interface 3", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=4)
        frontport1_1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        frontport1_2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1:2",
            rear_port=rearport1,
            rear_port_position=2,
        )

        # Create cables 1
        cable1 = Cable(termination_a=interface1, termination_b=rearport1, status=self.status)
        cable1.save()
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, rearport1),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 1)

        # Create cables 2-3
        cable2 = Cable(termination_a=interface2, termination_b=frontport1_1, status=self.status)
        cable2.save()
        cable3 = Cable(termination_a=interface3, termination_b=frontport1_2, status=self.status)
        cable3.save()
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable2, frontport1_1, rearport1, cable1),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface3,
            destination=interface1,
            path=(cable3, frontport1_2, rearport1, cable1),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 3)

        self.assertContainedByPath(
            {
                cable1: 3,
                cable2: 1,
                cable3: 1,
                frontport1_1: 1,
                frontport1_2: 1,
                rearport1: 3,
            }
        )

        # Delete cable 1
        cable1.delete()

        # Check that the partial path was deleted and the two complete paths are now partial
        self.assertPathExists(
            origin=interface2,
            destination=None,
            path=(cable2, frontport1_1, rearport1),
            is_active=False,
        )
        self.assertPathExists(
            origin=interface3,
            destination=None,
            path=(cable3, frontport1_2, rearport1),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 2)

    def test_207_rearport_without_frontport(self):
        """
        [IF1] --C1-- [FP1] [RP1] --C2-- [RP2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=1)
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=1)
        frontport1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1",
            rear_port=rearport1,
            rear_port_position=1,
        )

        # Create cables
        cable1 = Cable(termination_a=interface1, termination_b=frontport1, status=self.status)
        cable1.save()
        cable2 = Cable(termination_a=rearport1, termination_b=rearport2, status=self.status)
        cable2.save()
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, frontport1, rearport1, cable2, rearport2),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 1)

        self.assertContainedByPath(
            {
                cable1: 1,
                cable2: 1,
                frontport1: 1,
                rearport1: 1,
                rearport2: 1,
            }
        )

    def test_207a_mid_path_breakout_bails_out(self):
        """
        Mid-path breakout cables are not yet supported lane-aware. A trace that encounters a
        breakout cable past the origin's directly-connected hop should stop with `is_split=True`
        rather than picking an arbitrary peer via `get_cable_peer()`.

        [IF1] --C1 (straight)-- [RP1] [FP1] --C2 (breakout 1:4)-- [FP2] [RP2]
        """
        breakout_type = CableType(
            name="Test mid-path 1:4 breakout",
            a_connectors=1,
            b_connectors=4,
            total_lanes=4,
        )
        breakout_type.validated_save()  # populates `mapping` via clean()

        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=1)
        frontport1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=1)
        frontport2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2",
            rear_port=rearport2,
            rear_port_position=1,
        )

        # Regular cable: IF1 ↔ RP1 (pass-through to FP1).
        cable1 = Cable(termination_a=interface1, termination_b=rearport1, status=self.status)
        cable1.save()

        # Sanity check: with only the straight cable, the trace stops at FP1 with no destination.
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, rearport1, frontport1),
            is_active=False,
        )

        # Breakout cable mid-path: FP1 ↔ FP2 with breakout cable_type.
        cable2 = Cable(
            termination_a=frontport1,
            termination_b=frontport2,
            cable_type=breakout_type,
            status=self.status,
        )
        cable2.save()

        # The retraced path should still stop at FP1 — but now marked `is_split=True` because the
        # trace hit a breakout cable it can't navigate.
        cp = self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, rearport1, frontport1),
            is_active=False,
        )
        self.assertTrue(cp.is_split, msg=f"Expected is_split=True on mid-path breakout; got {cp}")

    def test_207a2_get_split_nodes_with_frontport_terminal(self):
        """
        `CablePath.get_split_nodes()` must handle a split path whose terminal node is a FrontPort,
        not just the RearPort case (test_206). A front-to-rear trace that bails out at a mid-path
        breakout (see test_207a) stops on the FrontPort, so `path[-1]` is a FrontPort. The next
        segments are the breakout cable's far-side lane terminations (FP2 here) — onward across the
        cable — not the rear port behind FP1, which is backward and already in the traced path.

        [IF1] --C1 (straight)-- [RP1] [FP1] --C2 (breakout 1:4)-- [FP2] [RP2]
        """
        breakout_type = CableType(
            name="Test split-nodes 1:4 breakout",
            a_connectors=1,
            b_connectors=4,
            total_lanes=4,
        )
        breakout_type.validated_save()  # populates `mapping` via clean()

        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=1)
        frontport1 = FrontPort.objects.create(
            device=self.device, name="Front Port 1", rear_port=rearport1, rear_port_position=1
        )
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=1)
        frontport2 = FrontPort.objects.create(
            device=self.device, name="Front Port 2", rear_port=rearport2, rear_port_position=1
        )

        # Straight cable IF1 ↔ RP1 (pass-through to FP1), then a breakout cable on FP1 that fans out.
        cable1 = Cable(termination_a=interface1, termination_b=rearport1, status=self.status)
        cable1.save()
        Cable(termination_a=frontport1, termination_b=frontport2, cable_type=breakout_type, status=self.status).save()

        cp = self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, rearport1, frontport1),
            is_active=False,
        )

        # Precondition: the path split on a FrontPort, the branch the old code mishandled.
        self.assertTrue(cp.is_split)
        self.assertIsInstance(path_node_to_object(cp.path[-1]), FrontPort)

        # Onward node is the breakout cable's far-side peer (FP2), not the already-traversed RP1.
        split_nodes = list(cp.get_split_nodes())
        self.assertEqual([node.pk for node in split_nodes], [frontport2.pk])

    def test_207b_breakout_with_partial_lanes(self):
        """
        Breakout cable with only some fan-out lanes connected. The trunk side should produce one
        CablePath per lane defined by the cable type: the connected lane gets a complete path,
        and the unconnected lanes get partial paths (is_split=True, destination=None, path=[cable])
        labeled with each lane's connector/position.

        [IF_trunk] --C1 (breakout 1:4)-- [IF_lane1]   (lane 1: connected)
                                         <unconnected> (lanes 2-4: no fan-out termination)
        """
        breakout_type = CableType(
            name="Test partial-lanes 1:4 breakout",
            a_connectors=1,
            b_connectors=4,
            total_lanes=4,
        )
        breakout_type.validated_save()

        if_trunk = Interface.objects.create(device=self.device, name="Trunk", status=self.interface_status)
        if_lane1 = Interface.objects.create(device=self.device, name="Lane 1", status=self.interface_status)

        cable = Cable(
            termination_a=if_trunk,
            termination_b=if_lane1,
            cable_type=breakout_type,
            status=self.status,
        )
        cable.save()

        trunk_paths = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=if_trunk.pk
        ).order_by("peer_connector")
        # One CablePath per fan-out lane.
        self.assertEqual(trunk_paths.count(), 4)

        lane1_path = trunk_paths.get(peer_connector=1)
        self.assertEqual(lane1_path.destination, if_lane1)
        self.assertFalse(lane1_path.is_split, msg=f"Lane 1 should be complete, got {lane1_path}")
        self.assertTrue(lane1_path.is_active)

        for connector in (2, 3, 4):
            partial = trunk_paths.get(peer_connector=connector)
            self.assertIsNone(
                partial.destination,
                msg=f"Lane {connector} should have no destination, got {partial.destination}",
            )
            self.assertTrue(partial.is_split, msg=f"Lane {connector} should be split, got {partial}")
            self.assertFalse(partial.is_active)
            # Path should be just the cable (entered but couldn't be traversed lane-aware).
            self.assertEqual(partial.path, [object_to_path_node(cable)])

        # The single connected fan-out side has one complete reverse-direction path.
        lane1_reverse = CablePath.objects.get(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=if_lane1.pk
        )
        self.assertEqual(lane1_reverse.destination, if_trunk)

    def test_207c_mid_path_breakout_lane_traverses_to_trunk(self):
        """
        A breakout lane reached mid-path leads deterministically back to its single trunk endpoint,
        so the trace continues through it to completion (the fan-out side still splits — see
        test_207a). This mirrors a patch-panel/MPO topology where a far endpoint reaches the trunk
        endpoint through a breakout whose lane lands on a patch-panel front port.

        [IF_trunk] --C_bk (breakout 1:2, lane B1)-- [FP1][RP1] --C2-- [RP2][FP2] --C3-- [IF_dest]
        """
        breakout_type = CableType(
            name="Test mid-path lane 1:2 breakout",
            a_connectors=1,
            b_connectors=2,
            total_lanes=2,
        )
        breakout_type.validated_save()  # populates `mapping` via clean()

        if_trunk = Interface.objects.create(device=self.device, name="Trunk", status=self.interface_status)
        if_dest = Interface.objects.create(device=self.device, name="Dest", status=self.interface_status)

        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=2)
        frontport1 = FrontPort.objects.create(
            device=self.device, name="Front Port 1", rear_port=rearport1, rear_port_position=1
        )
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=2)
        frontport2 = FrontPort.objects.create(
            device=self.device, name="Front Port 2", rear_port=rearport2, rear_port_position=1
        )

        # IF_dest -- C3 -- FP2 (pass-through to RP2)
        cable3 = Cable(termination_a=frontport2, termination_b=if_dest, status=self.status)
        cable3.save()
        # RP2 -- C2 -- RP1 (straight rear-to-rear)
        cable2 = Cable(termination_a=rearport2, termination_b=rearport1, status=self.status)
        cable2.save()
        # FP1 -- C_bk (breakout lane B1) -- IF_trunk
        cable_bk = Cable(termination_a=if_trunk, termination_b=frontport1, cable_type=breakout_type, status=self.status)
        cable_bk.save()

        # Tracing from the destination interface reaches the trunk interface: the breakout lane (B1)
        # maps to a single trunk connector, so it is followed rather than treated as a split.
        cp = self.assertPathExists(
            origin=if_dest,
            destination=if_trunk,
            path=(cable3, frontport2, rearport2, cable2, rearport1, frontport1, cable_bk),
            is_active=True,
        )
        self.assertFalse(cp.is_split, msg=f"Lane-side mid-path breakout should traverse, not split; got {cp}")

    def test_208_single_path_via_circuit(self):
        """
        [IF1] --C1-- [CT1A] [CT1Z] --C2-- [IF2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        circuittermination1 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="A"
        )
        circuittermination2 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="Z"
        )

        # Create cable 1
        cable1 = Cable(
            termination_a=interface1,
            termination_b=circuittermination1,
            status=self.status,
        )
        cable1.save()

        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, circuittermination1, circuittermination2),
            is_active=False,
        )

        # Create cable 2
        cable2 = Cable(
            termination_a=interface2,
            termination_b=circuittermination2,
            status=self.status,
        )
        cable2.save()

        self.assertPathExists(
            origin=interface1,
            destination=interface2,
            path=(cable1, circuittermination1, circuittermination2, cable2),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable2, circuittermination2, circuittermination1, cable1),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 4)

        self.assertContainedByPath(
            {
                cable1: 3,
                cable2: 3,
                circuittermination1: 2,
                circuittermination2: 2,
            }
        )

        # Delete cable 2
        cable2.delete()
        path1 = self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, circuittermination1, circuittermination2),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 2)
        interface1.refresh_from_db()
        interface2.refresh_from_db()
        self.assertPathIsSet(interface1, path1)
        self.assertPathIsNotSet(interface2)

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_209_single_path_via_circuit_add_circuit_termination(self):
        """
        Tests case where a user might want to add a second termination to a circuit at a later time.
        [IF1] --C1-- [CT1A] then [IF1] --C1-- [CT1A][CT1Z] --C2-- [IF2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        circuittermination1 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="A"
        )

        # Create cable 1
        cable1 = Cable(
            termination_a=interface1,
            termination_b=circuittermination1,
            status=self.status,
        )
        cable1.save()

        self.assertPathExists(
            origin=interface1,
            destination=circuittermination1,
            path=(cable1,),
            is_active=True,
        )

        circuittermination2 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="Z"
        )

        # Create cable 2
        cable2 = Cable(
            termination_a=interface2,
            termination_b=circuittermination2,
            status=self.status,
        )
        cable2.save()

        self.assertPathExists(
            origin=interface1,
            destination=interface2,
            path=(cable1, circuittermination1, circuittermination2, cable2),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable2, circuittermination2, circuittermination1, cable1),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 4)

        self.assertContainedByPath(
            {
                cable1: 3,
                cable2: 3,
                circuittermination1: 2,
                circuittermination2: 2,
            }
        )

        # Delete cable 2
        cable2.delete()
        path1 = self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, circuittermination1, circuittermination2),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 2)
        interface1.refresh_from_db()
        interface2.refresh_from_db()
        self.assertPathIsSet(interface1, path1)
        self.assertPathIsNotSet(interface2)

        # Delete cable 1
        cable1.delete()

        # Check that all CablePaths have been deleted
        self.assertEqual(CablePath.objects.count(), 0)

    def test_210_single_path_via_circuit_add_circuit_termination(self):
        """
        Tests case for circuit termination loop.
        [CT1A][CT1Z]
        """
        circuittermination1 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="A"
        )
        circuittermination2 = CircuitTermination.objects.create(
            circuit=self.circuit, location=self.location, term_side="Z"
        )
        cable1 = Cable(
            termination_a=circuittermination1,
            termination_b=circuittermination2,
            status=self.status,
        )
        with self.assertRaises(ValidationError):
            cable1.save()

    def test_301_create_path_via_existing_cable(self):
        """
        [IF1] --C1-- [FP1] [RP2] --C2-- [RP2] [FP2] --C3-- [IF2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=1)
        rearport2 = RearPort.objects.create(device=self.device, name="Rear Port 2", positions=1)
        frontport1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1",
            rear_port=rearport1,
            rear_port_position=1,
        )
        frontport2 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 2",
            rear_port=rearport2,
            rear_port_position=1,
        )

        # Create cable 2
        cable2 = Cable(termination_a=rearport1, termination_b=rearport2, status=self.status)
        cable2.save()
        self.assertEqual(CablePath.objects.count(), 0)

        # Create cable1
        cable1 = Cable(termination_a=interface1, termination_b=frontport1, status=self.status)
        cable1.save()
        self.assertPathExists(
            origin=interface1,
            destination=None,
            path=(cable1, frontport1, rearport1, cable2, rearport2, frontport2),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 1)

        # Create cable 3
        cable3 = Cable(termination_a=frontport2, termination_b=interface2, status=self.status)
        cable3.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface2,
            path=(cable1, frontport1, rearport1, cable2, rearport2, frontport2, cable3),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable3, frontport2, rearport2, cable2, rearport1, frontport1, cable1),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 2)

        self.assertContainedByPath(
            {
                cable1: 2,
                cable2: 2,
                cable3: 2,
                frontport1: 2,
                frontport2: 2,
                rearport1: 2,
                rearport2: 2,
            }
        )

    def test_302_update_path_on_cable_status_change(self):
        """
        [IF1] --C1-- [FP1] [RP1] --C2-- [IF2]
        """
        interface1 = Interface.objects.create(device=self.device, name="Interface 1", status=self.interface_status)
        interface2 = Interface.objects.create(device=self.device, name="Interface 2", status=self.interface_status)
        rearport1 = RearPort.objects.create(device=self.device, name="Rear Port 1", positions=1)
        frontport1 = FrontPort.objects.create(
            device=self.device,
            name="Front Port 1",
            rear_port=rearport1,
            rear_port_position=1,
        )

        # Create cables 1 and 2
        cable1 = Cable(termination_a=interface1, termination_b=frontport1, status=self.status)
        cable1.save()
        cable2 = Cable(termination_a=rearport1, termination_b=interface2, status=self.status)
        cable2.save()
        self.assertEqual(CablePath.objects.filter(is_active=True).count(), 2)
        self.assertEqual(CablePath.objects.count(), 2)

        # Change cable 2's status to "planned"
        cable2.status = self.status_planned
        cable2.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface2,
            path=(cable1, frontport1, rearport1, cable2),
            is_active=False,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable2, rearport1, frontport1, cable1),
            is_active=False,
        )
        self.assertEqual(CablePath.objects.count(), 2)

        # Change cable 2's status to "connected"
        cable2 = Cable.objects.get(pk=cable2.pk)
        cable2.status = self.status
        cable2.save()
        self.assertPathExists(
            origin=interface1,
            destination=interface2,
            path=(cable1, frontport1, rearport1, cable2),
            is_active=True,
        )
        self.assertPathExists(
            origin=interface2,
            destination=interface1,
            path=(cable2, rearport1, frontport1, cable1),
            is_active=True,
        )
        self.assertEqual(CablePath.objects.count(), 2)

        self.assertContainedByPath(
            {
                cable1: 2,
                cable2: 2,
                frontport1: 2,
                rearport1: 2,
            }
        )

    def test_303_disconnect_termination_straight_cable(self):
        """
        Disconnecting one termination of a straight cable: the cable survives, the disconnected
        side has no CablePath, and the still-connected side has a partial path.

        [IF1] --C1-- [IF2]   →  [IF1]    C1   [IF2]
                                          (IF2 still on the cable, IF1 disconnected)
        """
        if1 = Interface.objects.create(device=self.device, name="IF1", status=self.interface_status)
        if2 = Interface.objects.create(device=self.device, name="IF2", status=self.interface_status)
        cable = Cable(termination_a=if1, termination_b=if2, status=self.status)
        cable.save()

        self.assertEqual(CablePath.objects.count(), 2)

        result = disconnect_termination(if1)
        self.assertEqual(result, cable)

        # Cable itself survives; IF2's cable_termination row survives; IF1's is gone.
        self.assertTrue(Cable.objects.filter(pk=cable.pk).exists())
        if1.refresh_from_db()
        if2.refresh_from_db()
        self.assertIsNone(getattr(if1, "cable_termination", None))
        self.assertIsNotNone(if2.cable_termination)

        # No CablePath from IF1 (its cable is gone); IF2 has a partial path ending at the cable.
        if1_paths = CablePath.objects.filter(origin_type=ContentType.objects.get_for_model(Interface), origin_id=if1.pk)
        self.assertEqual(if1_paths.count(), 0)

        if2_path = CablePath.objects.get(origin_type=ContentType.objects.get_for_model(Interface), origin_id=if2.pk)
        self.assertIsNone(if2_path.destination)
        self.assertFalse(if2_path.is_active)
        self.assertEqual(if2_path.path, [object_to_path_node(cable)])

    def test_304_disconnect_termination_breakout_fanout_side(self):
        """
        Disconnecting one fanout-side port of a breakout cable should preserve the cable_paths on
        the surviving lanes (regression test for the old `peer.cable_paths.all().delete()` bug
        which nuked all trunk-side paths).

        Setup: 1:4 breakout where only lanes 1 and 2 are connected on the fan-out side. Disconnect
        the lane-1 fan-out port. Lane 2 should still resolve end-to-end on both sides; lane 1
        should now be partial on the trunk side and gone on the (disconnected) fan-out side.
        Lanes 3 and 4 are unconnected throughout and remain partial trunk-side paths.
        """
        breakout_type = CableType(
            name="Test disconnect 1:4 breakout",
            a_connectors=1,
            b_connectors=4,
            total_lanes=4,
        )
        breakout_type.validated_save()

        if_trunk = Interface.objects.create(device=self.device, name="Trunk", status=self.interface_status)
        if_lane1 = Interface.objects.create(device=self.device, name="Lane 1", status=self.interface_status)
        if_lane2 = Interface.objects.create(device=self.device, name="Lane 2", status=self.interface_status)

        # Create the trunk↔lane1 cable (this populates connector=1 join rows on both sides).
        cable = Cable(
            termination_a=if_trunk,
            termination_b=if_lane1,
            cable_type=breakout_type,
            status=self.status,
        )
        cable.save()

        # Add a join row for connector 2 (Cable.save only materializes connector 1 by default).
        cable.add_termination(if_lane2, "B", connector=2)

        # Sanity check pre-disconnect: lane 1 + lane 2 complete, lanes 3-4 partial.
        trunk_paths_pre = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=if_trunk.pk
        )
        self.assertEqual(trunk_paths_pre.count(), 4)
        self.assertEqual(trunk_paths_pre.get(peer_connector=1).destination, if_lane1)
        self.assertEqual(trunk_paths_pre.get(peer_connector=2).destination, if_lane2)
        self.assertTrue(trunk_paths_pre.get(peer_connector=3).is_split)
        self.assertTrue(trunk_paths_pre.get(peer_connector=4).is_split)

        # Disconnect lane 1's fan-out port.
        result = disconnect_termination(if_lane1)
        self.assertEqual(result, cable)

        # Cable itself survives.
        self.assertTrue(Cable.objects.filter(pk=cable.pk).exists())

        trunk_paths_post = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=if_trunk.pk
        )
        # Still 4 trunk-side paths (one per lane in the cable type's mapping).
        self.assertEqual(trunk_paths_post.count(), 4)

        # Lane 1 is now partial.
        lane1_trunk = trunk_paths_post.get(peer_connector=1)
        self.assertIsNone(lane1_trunk.destination)
        self.assertTrue(lane1_trunk.is_split)

        # Lane 2 SURVIVES — this is the regression-protected assertion.
        lane2_trunk = trunk_paths_post.get(peer_connector=2)
        self.assertEqual(lane2_trunk.destination, if_lane2, msg="Lane 2 trunk-side path was clobbered by disconnect")

        # Lanes 3 and 4 remain partial (unchanged).
        self.assertTrue(trunk_paths_post.get(peer_connector=3).is_split)
        self.assertTrue(trunk_paths_post.get(peer_connector=4).is_split)

        # The disconnected fan-out side has no CablePath at all.
        self.assertEqual(
            CablePath.objects.filter(
                origin_type=ContentType.objects.get_for_model(Interface), origin_id=if_lane1.pk
            ).count(),
            0,
        )
        # The other fan-out side still has its reverse-direction path.
        lane2_reverse = CablePath.objects.get(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=if_lane2.pk
        )
        self.assertEqual(lane2_reverse.destination, if_trunk)

    def test_get_connected_endpoints_unconnected_endpoint(self):
        """An endpoint with no cable returns an empty list."""
        lonely = Interface.objects.create(device=self.device, name="lonely", status=self.interface_status)
        self.assertEqual(lonely.get_connected_endpoints(), [])

    def test_get_connected_endpoints_simple_cable(self):
        """A simple cable: each endpoint resolves to a one-element list containing the peer."""
        if1 = Interface.objects.create(device=self.device, name="gce-simple-1", status=self.interface_status)
        if2 = Interface.objects.create(device=self.device, name="gce-simple-2", status=self.interface_status)
        Cable(termination_a=if1, termination_b=if2, status=self.status).save()
        self.assertEqual(if1.get_connected_endpoints(), [if2])
        self.assertEqual(if2.get_connected_endpoints(), [if1])

    def test_get_connected_endpoints_breakout_cable(self):
        """A breakout cable: the trunk side resolves to one destination per fanned-out lane."""
        breakout_type = CableType(
            name="get_connected_endpoints 1x4",
            a_connectors=1,
            b_connectors=4,
            total_lanes=4,
        )
        breakout_type.validated_save()

        trunk = Interface.objects.create(device=self.device, name="gce-trunk", status=self.interface_status)
        lane1 = Interface.objects.create(device=self.device, name="gce-lane1", status=self.interface_status)
        lane2 = Interface.objects.create(device=self.device, name="gce-lane2", status=self.interface_status)

        cable = Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout_type, status=self.status)
        cable.save()
        cable.add_termination(lane2, "B", connector=2)

        # Trunk side: one destination per resolved lane (lanes 3-4 unconnected → not included).
        self.assertEqual(set(trunk.get_connected_endpoints()), {lane1, lane2})
        # Each fan-out side resolves back to the trunk.
        self.assertEqual(lane1.get_connected_endpoints(), [trunk])
        self.assertEqual(lane2.get_connected_endpoints(), [trunk])

    #
    # Breakout child-interface position mapping (Interface.get_breakout_lane /
    # CableTermination.get_breakout_trunk_child_interfaces).
    #

    def _make_breakout_trunk(self, a_connectors=1, b_connectors=4, total_lanes=4, child_positions=(1, 2)):
        """Create a breakout cable whose A side is a trunk interface with named child interfaces.

        Returns `(trunk, children, far_terminations)` where `children` maps a position number to the
        child Interface `<trunk>.<position>` and `far_terminations` maps a B-side connector number to
        the Interface cabled there. Only connectors 1 and 2 of the fan-out side are cabled.
        """
        breakout_type = CableType(
            name=f"breakout {a_connectors}x{b_connectors}x{total_lanes}",
            a_connectors=a_connectors,
            b_connectors=b_connectors,
            total_lanes=total_lanes,
        )
        breakout_type.validated_save()

        trunk = Interface.objects.create(
            device=self.device,
            name="Ethernet1",
            type=InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS,
            status=self.interface_status,
        )
        children = {
            position: Interface.objects.create(
                device=self.device,
                name=f"Ethernet1.{position}",
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=self.interface_status,
                parent_interface=trunk,
                breakout_position=position,
            )
            for position in child_positions
        }
        far1 = Interface.objects.create(
            device=self.device, name="far-1", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        far2 = Interface.objects.create(
            device=self.device, name="far-2", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        cable = Cable(termination_a=trunk, termination_b=far1, cable_type=breakout_type, status=self.status)
        cable.save()
        cable.add_termination(far2, "B", connector=2)
        return trunk, children, {1: far1, 2: far2}

    def test_get_breakout_lane_forward(self):
        """A child interface resolves to its trunk-connector position and the far-side termination."""
        _, children, far_terminations = self._make_breakout_trunk()

        lane1 = children[1].get_breakout_lane()
        self.assertIsNotNone(lane1)
        self.assertEqual(lane1.position, 1)
        self.assertEqual(lane1.far_termination, far_terminations[1])

        lane2 = children[2].get_breakout_lane()
        self.assertEqual(lane2.position, 2)
        self.assertEqual(lane2.far_termination, far_terminations[2])

    def test_get_breakout_lane_unoccupied_far_connector(self):
        """A child mapping to a connector with no termination resolves, with far_termination None."""
        trunk, _, _ = self._make_breakout_trunk(child_positions=())
        child3 = Interface.objects.create(
            device=self.device,
            name="Ethernet1.3",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=3,
        )
        lane3 = child3.get_breakout_lane()
        self.assertIsNotNone(lane3)
        self.assertEqual(lane3.position, 3)
        self.assertIsNone(lane3.far_termination)

    def test_get_breakout_lane_position_out_of_range(self):
        """A breakout_position beyond the trunk connector's position count yields no lane."""
        trunk, _, _ = self._make_breakout_trunk(child_positions=())
        # 1x4 breakout → a_positions == 4, so position 5 is not carried by the trunk connector.
        child5 = Interface.objects.create(
            device=self.device,
            name="Ethernet1.5",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=5,
        )
        self.assertIsNone(child5.get_breakout_lane())

    def test_get_breakout_lane_no_position_set(self):
        """A child interface with no breakout_position has no breakout lane."""
        trunk, _, _ = self._make_breakout_trunk(child_positions=())
        child = Interface.objects.create(
            device=self.device,
            name="Ethernet1.mgmt",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
        )
        self.assertIsNone(child.get_breakout_lane())

    def test_get_breakout_lane_no_parent(self):
        """The trunk interface itself (no parent_interface) has no breakout lane."""
        trunk, _, _ = self._make_breakout_trunk(child_positions=())
        self.assertIsNone(trunk.get_breakout_lane())

    def test_get_breakout_lane_non_breakout_cable(self):
        """A child whose parent is on an ordinary (non-breakout) cable has no breakout lane."""
        parent = Interface.objects.create(
            device=self.device,
            name="Ethernet2",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        peer = Interface.objects.create(
            device=self.device, name="peer", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        Cable(termination_a=parent, termination_b=peer, status=self.status).save()
        child = Interface.objects.create(
            device=self.device,
            name="Ethernet2.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=parent,
            breakout_position=1,
        )
        self.assertIsNone(child.get_breakout_lane())

    def test_get_breakout_lane_parent_on_fanout_side(self):
        """A child whose parent terminates the fan-out (not trunk) side has no breakout lane."""
        breakout_type = CableType(name="fanout-parent 1x4", a_connectors=1, b_connectors=4, total_lanes=4)
        breakout_type.validated_save()
        trunk = Interface.objects.create(
            device=self.device,
            name="Ethernet3",
            type=InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS,
            status=self.interface_status,
        )
        fanout = Interface.objects.create(
            device=self.device,
            name="Ethernet4",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        Cable(termination_a=trunk, termination_b=fanout, cable_type=breakout_type, status=self.status).save()
        # `fanout` is on the B (fan-out) side, so its children do not map to trunk positions.
        child = Interface.objects.create(
            device=self.device,
            name="Ethernet4.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=fanout,
            breakout_position=1,
        )
        self.assertIsNone(child.get_breakout_lane())

    def test_get_breakout_connected_endpoint_direct(self):
        """When a lane's far termination is itself an endpoint, that endpoint is the connection."""
        _, children, far_terminations = self._make_breakout_trunk()
        self.assertEqual(children[1].get_breakout_connected_endpoint(), far_terminations[1])
        self.assertEqual(children[2].get_breakout_connected_endpoint(), far_terminations[2])

    def test_get_breakout_connected_endpoint_through_patch_panel(self):
        """The connection traverses past patch-panel front/rear ports to the ultimate endpoint.

        `get_breakout_lane().far_termination` is the one-hop FrontPort, whereas
        `get_breakout_connected_endpoint` follows the trunk's `CablePath` onward through the rear
        port and the second cable to the final interface.
        """
        breakout_type = CableType(name="patchpanel 1x4", a_connectors=1, b_connectors=4, total_lanes=4)
        breakout_type.validated_save()
        trunk = Interface.objects.create(
            device=self.device,
            name="Ethernet10",
            type=InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS,
            status=self.interface_status,
        )
        child = Interface.objects.create(
            device=self.device,
            name="Ethernet10.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=1,
        )
        rearport = RearPort.objects.create(device=self.device, name="PP Rear", positions=1)
        frontport = FrontPort.objects.create(
            device=self.device, name="PP Front", rear_port=rearport, rear_port_position=1
        )
        final = Interface.objects.create(
            device=self.device, name="final", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        # Breakout trunk -> patch-panel front port (B connector 1), then rear port -> final interface.
        Cable(termination_a=trunk, termination_b=frontport, cable_type=breakout_type, status=self.status).save()
        Cable(termination_a=rearport, termination_b=final, status=self.status).save()

        self.assertEqual(child.get_breakout_lane().far_termination, frontport)
        self.assertEqual(child.get_breakout_connected_endpoint(), final)

    def test_get_breakout_connected_endpoint_no_lane(self):
        """A child with no breakout lane (non-breakout parent cable) has no breakout connection."""
        parent = Interface.objects.create(
            device=self.device,
            name="Ethernet20",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        peer = Interface.objects.create(
            device=self.device,
            name="peer20",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        Cable(termination_a=parent, termination_b=peer, status=self.status).save()
        child = Interface.objects.create(
            device=self.device,
            name="Ethernet20.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=parent,
            breakout_position=1,
        )
        self.assertIsNone(child.get_breakout_connected_endpoint())

    def test_get_breakout_trunk_child_interfaces_reverse(self):
        """A fan-out-side termination resolves to the trunk's matching child interface."""
        _, children, far_terminations = self._make_breakout_trunk()

        mapping1 = far_terminations[1].get_breakout_trunk_child_interfaces()
        self.assertEqual(len(mapping1), 1)
        self.assertEqual(mapping1[0]["position"], 1)
        self.assertEqual(mapping1[0]["child_interface"], children[1])

        mapping2 = far_terminations[2].get_breakout_trunk_child_interfaces()
        self.assertEqual(mapping2[0]["position"], 2)
        self.assertEqual(mapping2[0]["child_interface"], children[2])

    def test_get_breakout_trunk_child_interfaces_missing_child(self):
        """When no child interface matches the position, trunk/position resolve but child is None."""
        trunk, _, far_terminations = self._make_breakout_trunk(child_positions=())
        mapping = far_terminations[1].get_breakout_trunk_child_interfaces()
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping[0]["trunk_interface"], trunk)
        self.assertEqual(mapping[0]["position"], 1)
        self.assertIsNone(mapping[0]["child_interface"])

    def test_get_breakout_trunk_child_interfaces_multi_position_connector(self):
        """A fan-out connector carrying multiple lanes maps to multiple trunk child interfaces."""
        # 1x2 over 4 lanes → b_positions == 2: connector B1 carries two trunk positions.
        _, children, far_terminations = self._make_breakout_trunk(
            a_connectors=1, b_connectors=2, total_lanes=4, child_positions=(1, 2, 3, 4)
        )
        cable_type = far_terminations[1].cable.cable_type
        expected_positions = sorted(e["a_position"] for e in cable_type.mapping if e["b_connector"] == 1)
        self.assertGreater(len(expected_positions), 1)  # guard: the connector really is multi-lane

        mapping = far_terminations[1].get_breakout_trunk_child_interfaces()
        self.assertEqual(sorted(entry["position"] for entry in mapping), expected_positions)
        self.assertEqual(
            {entry["child_interface"] for entry in mapping},
            {children[position] for position in expected_positions},
        )

    def test_get_breakout_trunk_child_interfaces_non_interface_trunk(self):
        """A breakout whose trunk peer is not an Interface yields no child mapping."""
        breakout_type = CableType(name="frontport-trunk 1x4", a_connectors=1, b_connectors=4, total_lanes=4)
        breakout_type.validated_save()
        rearport = RearPort.objects.create(device=self.device, name="RP", positions=1)
        trunk_frontport = FrontPort.objects.create(
            device=self.device, name="FP", rear_port=rearport, rear_port_position=1
        )
        far = Interface.objects.create(
            device=self.device, name="far", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        Cable(termination_a=trunk_frontport, termination_b=far, cable_type=breakout_type, status=self.status).save()
        self.assertEqual(far.get_breakout_trunk_child_interfaces(), [])

    def test_get_breakout_trunk_child_interfaces_called_on_trunk_side(self):
        """Calling the reverse helper on the trunk-side termination returns nothing (use forward)."""
        trunk, _, _ = self._make_breakout_trunk()
        self.assertEqual(trunk.get_breakout_trunk_child_interfaces(), [])

    def test_get_breakout_trunk_child_interfaces_non_breakout(self):
        """An ordinary cable yields no trunk child mapping."""
        if1 = Interface.objects.create(
            device=self.device,
            name="plain-1",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        if2 = Interface.objects.create(
            device=self.device,
            name="plain-2",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        Cable(termination_a=if1, termination_b=if2, status=self.status).save()
        self.assertEqual(if1.get_breakout_trunk_child_interfaces(), [])
        self.assertEqual(if2.get_breakout_trunk_child_interfaces(), [])

    def test_get_breakout_trunk_child_interface_for_endpoint_direct(self):
        """A leaf directly breakout-cabled to a trunk resolves the trunk's child interface."""
        trunk, children, far_terminations = self._make_breakout_trunk()
        leaf = far_terminations[1]
        # The leaf's connection endpoint is the trunk, and the lane maps back to child position 1.
        self.assertEqual(leaf.connected_endpoint, trunk)
        self.assertEqual(leaf.get_breakout_trunk_child_interface_for_endpoint(trunk), children[1])

    def test_get_breakout_trunk_child_interface_for_endpoint_through_patch_panel(self):
        """A leaf cabled to a breakout trunk *through* a patch panel still resolves the child interface.

        Mirrors the demo `_scenario_10` topology: the breakout cable is several hops away from the
        leaf (behind a front/rear pass-through), so the immediate-cable helper sees nothing, but the
        endpoint helper matches on the fully-traced path.
        """
        breakout_type = CableType(name="endpoint-patchpanel 1x4", a_connectors=1, b_connectors=4, total_lanes=4)
        breakout_type.validated_save()
        trunk = Interface.objects.create(
            device=self.device,
            name="Ethernet11/1",
            type=InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS,
            status=self.interface_status,
        )
        child = Interface.objects.create(
            device=self.device,
            name="Ethernet11/1.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=1,
        )
        rearport = RearPort.objects.create(device=self.device, name="PP Rear", positions=1)
        frontport = FrontPort.objects.create(
            device=self.device, name="PP Front", rear_port=rearport, rear_port_position=1
        )
        leaf = Interface.objects.create(
            device=self.device,
            name="Ethernet7/1",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        # trunk --breakout(B1)--> front port; rear port --cable--> leaf
        Cable(termination_a=trunk, termination_b=frontport, cable_type=breakout_type, status=self.status).save()
        Cable(termination_a=rearport, termination_b=leaf, status=self.status).save()

        # The leaf traces all the way to the trunk, but its own attached cable is not the breakout.
        self.assertEqual(leaf.connected_endpoint, trunk)
        self.assertEqual(leaf.get_breakout_trunk_child_interfaces(), [])
        # The endpoint helper resolves the trunk's child interface via the full path.
        self.assertEqual(leaf.get_breakout_trunk_child_interface_for_endpoint(trunk), child)

    def test_get_breakout_trunk_child_interface_for_endpoint_non_trunk(self):
        """A connection whose endpoint isn't a breakout trunk yields no child interface."""
        if1 = Interface.objects.create(
            device=self.device, name="ep-1", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        if2 = Interface.objects.create(
            device=self.device, name="ep-2", type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS, status=self.interface_status
        )
        Cable(termination_a=if1, termination_b=if2, status=self.status).save()
        self.assertIsNone(if1.get_breakout_trunk_child_interface_for_endpoint(if2))

    def test_breakout_position_requires_parent_interface(self):
        """Setting breakout_position without a parent interface is rejected by clean()."""
        orphan = Interface(
            device=self.device,
            name="orphan",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            breakout_position=1,
        )
        with self.assertRaises(ValidationError):
            orphan.validated_save()

    def test_breakout_position_unique_per_parent(self):
        """Two child interfaces of the same parent cannot claim the same breakout_position."""
        trunk = Interface.objects.create(
            device=self.device,
            name="trunk-unique",
            type=InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS,
            status=self.interface_status,
        )
        Interface.objects.create(
            device=self.device,
            name="trunk-unique.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=1,
        )
        duplicate = Interface(
            device=self.device,
            name="trunk-unique.1-dup",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=1,
        )
        with self.assertRaises(ValidationError):
            duplicate.validated_save()


class CableToCableTerminationSignalTestCase(TestCase):
    """Unit tests for the `CableToCableTermination` post_save/post_delete signal handler and the
    `defer_cable_path_rebuilds()` batching context manager."""

    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Signal Test Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            location=cls.location,
            device_type=device_type,
            role=device_role,
            name="Signal Test Device",
            status=device_status,
        )
        cls.iface_status = Status.objects.get_for_model(Interface).first()
        cls.cable_status = Status.objects.get_for_model(Cable).get(name="Connected")
        cls.if_a = Interface.objects.create(device=cls.device, name="if-a", status=cls.iface_status)
        cls.if_b = Interface.objects.create(device=cls.device, name="if-b", status=cls.iface_status)

    def test_post_save_signal_triggers_path_rebuild(self):
        """Creating a `CableToCableTermination` row outside the context manager triggers an
        immediate `rebuild_paths(cable)` via the post_save signal handler."""
        cable = Cable.objects.create(status=self.cable_status)
        # Cable.objects.create() doesn't go through Cable.save()'s _materialize flow because there
        # are no initial terminations — so no paths exist for it yet.
        self.assertEqual(CablePath.objects.filter(path__contains=cable).count(), 0)
        # Adding a row should trigger the signal → rebuild_paths → create a path for if_a.
        CableToCableTermination.objects.create(cable=cable, cable_end="A", interface=self.if_a)
        self.assertEqual(
            CablePath.objects.filter(
                origin_type=ContentType.objects.get_for_model(Interface), origin_id=self.if_a.pk
            ).count(),
            1,
        )

    def test_post_delete_signal_triggers_path_rebuild(self):
        """Deleting a `CableToCableTermination` row triggers `rebuild_paths(cable)` and
        re-traces (or removes) any paths that used it."""
        cable = Cable(termination_a=self.if_a, termination_b=self.if_b, status=self.cable_status)
        cable.save()
        # Cable creation builds the path; baseline.
        path = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=self.if_a.pk
        ).first()
        self.assertIsNotNone(path)
        self.assertEqual(path.destination_id, self.if_b.pk)
        # Drop the B-side join row directly; signal fires → path should be re-traced to partial.
        CableToCableTermination.objects.filter(cable=cable, cable_end="B").delete()
        path = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=self.if_a.pk
        ).first()
        self.assertIsNotNone(path)
        self.assertIsNone(path.destination_id)

    def test_defer_coalesces_per_row_signals_into_one_rebuild(self):
        """Inside `defer_cable_path_rebuilds()`, per-row signals queue dirty cables without
        triggering rebuilds; exactly one `rebuild_paths(cable)` fires per affected cable on exit."""
        cable = Cable.objects.create(status=self.cable_status)

        with mock.patch.object(dcim_signals, "rebuild_paths", wraps=dcim_signals.rebuild_paths) as spy:
            with defer_cable_path_rebuilds():
                CableToCableTermination.objects.create(cable=cable, cable_end="A", interface=self.if_a)
                CableToCableTermination.objects.create(cable=cable, cable_end="B", interface=self.if_b)
                # No rebuilds while batching.
                self.assertEqual(spy.call_count, 0)
            # Exactly one rebuild on exit, for the single affected cable.
            self.assertEqual(spy.call_count, 1)
            self.assertEqual(spy.call_args.args[0].pk, cable.pk)

    def test_defer_dedupes_multiple_changes_to_same_cable(self):
        """Multiple row changes on the same cable inside a single defer block flush to one
        rebuild — the dirty set is a set, not a list."""
        cable = Cable(termination_a=self.if_a, termination_b=self.if_b, status=self.cable_status)
        cable.save()

        with mock.patch.object(dcim_signals, "rebuild_paths", wraps=dcim_signals.rebuild_paths) as spy:
            with defer_cable_path_rebuilds():
                CableToCableTermination.objects.filter(cable=cable).delete()
                CableToCableTermination.objects.create(cable=cable, cable_end="A", interface=self.if_a)
                CableToCableTermination.objects.create(cable=cable, cable_end="B", interface=self.if_b)
            self.assertEqual(spy.call_count, 1)

    def test_defer_handles_multiple_cables(self):
        """Multiple cables touched in one defer block produce one rebuild per cable."""
        if_c = Interface.objects.create(device=self.device, name="if-c", status=self.iface_status)
        if_d = Interface.objects.create(device=self.device, name="if-d", status=self.iface_status)
        cable1 = Cable.objects.create(status=self.cable_status)
        cable2 = Cable.objects.create(status=self.cable_status)

        with mock.patch.object(dcim_signals, "rebuild_paths", wraps=dcim_signals.rebuild_paths) as spy:
            with defer_cable_path_rebuilds():
                CableToCableTermination.objects.create(cable=cable1, cable_end="A", interface=self.if_a)
                CableToCableTermination.objects.create(cable=cable1, cable_end="B", interface=self.if_b)
                CableToCableTermination.objects.create(cable=cable2, cable_end="A", interface=if_c)
                CableToCableTermination.objects.create(cable=cable2, cable_end="B", interface=if_d)
            self.assertEqual(spy.call_count, 2)
            rebuilt_cable_pks = {call.args[0].pk for call in spy.call_args_list}
            self.assertEqual(rebuilt_cable_pks, {cable1.pk, cable2.pk})

    def test_defer_is_nestable_outermost_exit_flushes(self):
        """Nested entries share the dirty set; only the outermost `__exit__` triggers the
        flush, so inner exits leave the queue intact."""
        cable = Cable.objects.create(status=self.cable_status)

        with mock.patch.object(dcim_signals, "rebuild_paths", wraps=dcim_signals.rebuild_paths) as spy:
            with defer_cable_path_rebuilds():
                CableToCableTermination.objects.create(cable=cable, cable_end="A", interface=self.if_a)
                with defer_cable_path_rebuilds():
                    CableToCableTermination.objects.create(cable=cable, cable_end="B", interface=self.if_b)
                    self.assertEqual(spy.call_count, 0)  # Inner block: no flush yet.
                self.assertEqual(spy.call_count, 0)  # Inner exit: still no flush (outer still active).
            self.assertEqual(spy.call_count, 1)  # Outer exit: single flush for the cable.

    def test_defer_rolls_back_on_exception(self):
        """An exception inside the context manager rolls back the transactional block: the
        queued row changes are undone and the flushed rebuild is skipped. Avoids the
        "rows committed, paths stale" inconsistency."""
        cable = Cable.objects.create(status=self.cable_status)
        # No join rows before; we'll add one inside the failing block and assert it's rolled back.
        self.assertEqual(CableToCableTermination.objects.filter(cable=cable).count(), 0)

        with mock.patch.object(dcim_signals, "rebuild_paths", wraps=dcim_signals.rebuild_paths) as spy:
            with self.assertRaises(RuntimeError):
                with defer_cable_path_rebuilds():
                    CableToCableTermination.objects.create(cable=cable, cable_end="A", interface=self.if_a)
                    raise RuntimeError("simulated failure inside defer block")
            self.assertEqual(spy.call_count, 0)  # flush skipped — transaction rolled back

        # The join row created inside the block doesn't survive the rollback.
        self.assertEqual(CableToCableTermination.objects.filter(cable=cable).count(), 0)

    def test_rebuild_paths_accepts_cabletocabletermination(self):
        """`rebuild_paths` resolves a `CableToCableTermination` input to its parent cable and
        applies Cable semantics."""
        cable = Cable(termination_a=self.if_a, termination_b=self.if_b, status=self.cable_status)
        cable.save()
        join_row = CableToCableTermination.objects.filter(cable=cable, cable_end="A").first()
        self.assertIsNotNone(join_row)
        # Sanity: a path already exists; rebuilding via the join row should leave one in place.
        original_path = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=self.if_a.pk
        ).first()
        rebuild_paths(join_row)
        rebuilt_path = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=self.if_a.pk
        ).first()
        self.assertIsNotNone(rebuilt_path)
        # Same end-state (origin → destination); PK may differ because rebuild deletes+recreates.
        self.assertEqual(rebuilt_path.destination_id, original_path.destination_id)

    def test_rebuild_paths_rejects_unsupported_input(self):
        """`rebuild_paths` raises `TypeError` for inputs that aren't a Cable, join row, or
        CableTermination subclass — used to silently no-op."""
        with self.assertRaisesRegex(TypeError, "expects a Cable, CableToCableTermination, or CableTermination"):
            rebuild_paths(self.device)  # Device isn't a valid path node.

    # `create_cablepath` direct-invocation branches not exercised by the standard cable-save flow.

    def test_create_cablepath_on_uncabled_node_with_rebuild_is_noop(self):
        """When the node has no `cable_termination` and `rebuild=True`, `create_cablepath` calls
        `rebuild_paths(node)` (a no-op for a node with no paths) and returns. The `rebuild=False`
        variant of this code path is exercised by signals; `rebuild=True` only happens when
        callers like the `trace_paths` management command pass an uncabled node directly."""
        uncabled = Interface.objects.create(device=self.device, name="uncabled-cp", status=self.iface_status)
        self.assertIsNone(uncabled.cable)
        create_cablepath(uncabled, rebuild=True)
        self.assertEqual(uncabled.cable_paths.count(), 0)

    def test_create_cablepath_breakout_dedupes_repeated_peer_connectors(self):
        """One CablePath per distinct peer_connector, not per mapping lane (1x2 with 4 lanes → 2 paths)."""
        breakout = CableType.objects.create(name="Test 1x2x4", a_connectors=1, b_connectors=2, total_lanes=4)
        # Sanity: at least one (a_connector, b_connector) pair repeats in the mapping.
        peer_connectors_seen = [entry["b_connector"] for entry in breakout.mapping]
        self.assertGreater(len(peer_connectors_seen), len(set(peer_connectors_seen)))

        trunk = Interface.objects.create(device=self.device, name="trunk-1x2x4", status=self.iface_status)
        lane1 = Interface.objects.create(device=self.device, name="lane1-1x2x4", status=self.iface_status)
        cable = Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout, status=self.cable_status)
        cable.save()
        # Trunk-side has one path per distinct peer_connector (2), not per mapping lane (4).
        trunk_paths = CablePath.objects.filter(
            origin_type=ContentType.objects.get_for_model(Interface), origin_id=trunk.pk
        )
        self.assertEqual(trunk_paths.count(), 2)
        self.assertEqual(set(trunk_paths.values_list("peer_connector", flat=True)), {1, 2})

    def test_create_cablepath_breakout_with_rebuild_true_invokes_rebuild_paths(self):
        """After fanning out a cable's paths, `create_cablepath(rebuild=True)` calls `rebuild_paths` on the origin."""
        breakout = CableType.objects.create(name="Test 1x2 rebuild", a_connectors=1, b_connectors=2, total_lanes=2)
        trunk = Interface.objects.create(device=self.device, name="trunk-rb", status=self.iface_status)
        lane1 = Interface.objects.create(device=self.device, name="lane1-rb", status=self.iface_status)
        Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout, status=self.cable_status).save()

        with mock.patch.object(dcim_signals, "rebuild_paths", wraps=dcim_signals.rebuild_paths) as spy:
            create_cablepath(trunk, rebuild=True)
        spy.assert_any_call(trunk)


class TracePathsCommandTestCase(TestCase):
    """
    Coverage for the `trace_paths` management command.

    Two concerns are exercised here:

    * Correctness: a normal (non-`--force`) run must (re)create *every* expected CablePath,
      including all fan-out lanes of a breakout cable.
    * Resilience: the command must run to completion rather than aborting partway when it encounters inconsistent or
      incorrect existing data — orphaned CablePath rows, or a cabling loop that was inadvertently committed.
    """

    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Trace Paths Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            location=cls.location,
            device_type=device_type,
            role=device_role,
            name="Trace Paths Device",
            status=device_status,
        )
        cls.interface_status = Status.objects.get_for_model(Interface).first()
        cls.cable_status = Status.objects.get_for_model(Cable).get(name="Connected")

        provider = Provider.objects.first()
        circuit_type = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()
        cls.circuit = Circuit.objects.create(
            provider=provider, circuit_type=circuit_type, cid="Trace Paths Circuit", status=circuit_status
        )

        cls.interface_ct = ContentType.objects.get_for_model(Interface)

    def run_command(self, *args):
        """Run `trace_paths` with the given args, returning its combined stdout/stderr output."""
        out = StringIO()
        err = StringIO()
        call_command("trace_paths", *args, stdout=out, stderr=err)
        return out.getvalue() + err.getvalue()

    def make_straight_cable(self, name):
        """Create `[a] --cable-- [b]` between two new interfaces; paths are traced on save."""
        a = Interface.objects.create(device=self.device, name=f"{name}-a", status=self.interface_status)
        b = Interface.objects.create(device=self.device, name=f"{name}-b", status=self.interface_status)
        Cable(termination_a=a, termination_b=b, status=self.cable_status).save()
        return a, b

    def make_breakout_trunk(self, name, b_connectors=4, total_lanes=4):
        """Create a 1xN breakout cable with a single connected fan-out lane.

        The trunk origin gets one CablePath per fan-out lane (one complete, the rest partial),
        which gives us a multi-lane origin to corrupt and re-trace.
        """
        breakout_type = CableType(
            name=f"{name}-type", a_connectors=1, b_connectors=b_connectors, total_lanes=total_lanes
        )
        breakout_type.validated_save()  # populates `mapping` via clean()
        trunk = Interface.objects.create(device=self.device, name=f"{name}-trunk", status=self.interface_status)
        lane1 = Interface.objects.create(device=self.device, name=f"{name}-lane1", status=self.interface_status)
        Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout_type, status=self.cable_status).save()
        return trunk, lane1

    def trunk_paths(self, trunk):
        return CablePath.objects.filter(origin_type=self.interface_ct, origin_id=trunk.pk)

    # --- Basic behavior -------------------------------------------------------------------------

    def test_noop_when_all_paths_present(self):
        """With every cabled origin already traced, a plain run retraces nothing and finishes.

        This is the common `nautobot-server post_upgrade` case (lots of cables, nothing missing),
        so it must skip *fully-traced* origins — including breakout origins, whose existing path
        count already equals their lane count. If any origin were re-examined we'd see "Retracing".
        """
        self.make_straight_cable("noop")
        self.make_breakout_trunk("noop-breakout")  # complete: trunk has all 4 lane paths
        before = CablePath.objects.count()
        self.assertGreaterEqual(before, 5)

        output = self.run_command()

        self.assertIn("Finished.", output)
        self.assertIn("Found no missing", output)
        self.assertNotIn("Retracing", output)
        self.assertEqual(CablePath.objects.count(), before)

    def test_regenerates_all_missing_paths(self):
        """After all CablePaths are dropped, a plain run rebuilds them for every cabled origin."""
        a, b = self.make_straight_cable("regen")
        expected = CablePath.objects.count()
        self.assertGreater(expected, 0)

        CablePath.objects.all().delete()
        output = self.run_command()

        self.assertIn("Finished.", output)
        self.assertEqual(CablePath.objects.count(), expected)
        path = CablePath.objects.get(origin_type=self.interface_ct, origin_id=a.pk)
        self.assertEqual(path.destination, b)

    def test_force_recreates_paths(self):
        """`--force --no-input` deletes and recreates all paths without prompting."""
        a, b = self.make_straight_cable("force")

        output = self.run_command("--force", "--no-input")

        self.assertIn("Deleting", output)
        self.assertIn("Finished.", output)
        path = CablePath.objects.get(origin_type=self.interface_ct, origin_id=a.pk)
        self.assertEqual(path.destination, b)

    def test_force_with_no_existing_paths_skips_prompt(self):
        """`--force` with zero existing paths takes the no-prompt branch and rebuilds cleanly."""
        a, _ = self.make_straight_cable("force-empty")
        CablePath.objects.all().delete()

        # No --no-input: with paths_count == 0 the command must not block on input().
        output = self.run_command("--force")

        self.assertIn("Finished.", output)
        self.assertEqual(CablePath.objects.filter(origin_type=self.interface_ct, origin_id=a.pk).count(), 1)

    def test_force_aborts_on_negative_confirmation(self):
        """`--force` without `--no-input` aborts (and deletes nothing) when the user declines."""
        self.make_straight_cable("abort")
        before = CablePath.objects.count()

        with mock.patch("builtins.input", return_value="no"):
            output = self.run_command("--force")

        self.assertIn("Aborting", output)
        self.assertEqual(CablePath.objects.count(), before)

    def test_force_proceeds_on_affirmative_confirmation(self):
        """`--force` without `--no-input` proceeds when the user confirms with "yes"."""
        a, _ = self.make_straight_cable("confirm")

        with mock.patch("builtins.input", return_value="yes"):
            output = self.run_command("--force")

        self.assertIn("Deleting", output)
        self.assertIn("Finished.", output)
        self.assertEqual(CablePath.objects.filter(origin_type=self.interface_ct, origin_id=a.pk).count(), 1)

    # --- Correctness: all expected paths are traced (the command's TODO) ------------------------

    def test_fills_in_missing_breakout_lanes(self):
        """A plain run must fill in breakout fan-out lanes that are missing from an origin that
        already has *some* lanes traced.

        This is the case called out by the TODO in the command: filtering origins on
        `cable_paths__isnull=True` only skips origins with *zero* paths, so a breakout trunk that
        is missing one lane (but has others) was wrongly considered "already traced" and skipped.
        """
        trunk, _ = self.make_breakout_trunk("partial")
        # Baseline: a 1:4 breakout produces one trunk-side path per lane.
        self.assertEqual(self.trunk_paths(trunk).count(), 4)

        # Simulate inconsistent data: two lanes never got traced.
        self.trunk_paths(trunk).filter(peer_connector__in=[3, 4]).delete()
        self.assertEqual(self.trunk_paths(trunk).count(), 2)

        output = self.run_command()

        self.assertIn("Finished.", output)
        self.assertEqual(self.trunk_paths(trunk).count(), 4)
        self.assertEqual(set(self.trunk_paths(trunk).values_list("peer_connector", flat=True)), {1, 2, 3, 4})

    # --- Resilience to inconsistent / incorrect existing data -----------------------------------

    def test_survives_orphaned_cablepath_rows(self):
        """Orphaned CablePath rows (origin/path referencing objects that no longer exist) don't
        break the command; a plain run leaves them untouched and `--force` clears them out."""
        a, b = self.make_straight_cable("orphan")
        # A CablePath whose origin and path point at nonexistent objects.
        orphan = CablePath.objects.create(
            origin_type=self.interface_ct,
            origin_id=uuid.uuid4(),
            path=[f"{self.interface_ct.pk}:{uuid.uuid4()}"],
            is_active=False,
            peer_connector=1,
        )

        # A plain run completes and leaves the orphan alone (it isn't a real cabled origin).
        plain_output = self.run_command()
        self.assertIn("Finished.", plain_output)
        self.assertTrue(CablePath.objects.filter(pk=orphan.pk).exists())

        # --force wipes everything (including the orphan) and rebuilds the real paths.
        force_output = self.run_command("--force", "--no-input")
        self.assertIn("Finished.", force_output)
        self.assertFalse(CablePath.objects.filter(pk=orphan.pk).exists())
        self.assertEqual(CablePath.objects.get(origin_type=self.interface_ct, origin_id=a.pk).destination, b)

    def test_survives_committed_cabling_loop(self):
        """A cabling loop that was committed without being traced must not abort the command."""
        # A healthy straight cable that must still get traced despite the loop elsewhere.
        good_a, good_b = self.make_straight_cable("loop-control")

        # Two terminations of the same circuit cabled directly together form a loop. Commit the
        # cabling with tracing suppressed so the loop lives in the DB with no CablePath rows.
        ct_a = CircuitTermination.objects.create(circuit=self.circuit, location=self.location, term_side="A")
        ct_z = CircuitTermination.objects.create(circuit=self.circuit, location=self.location, term_side="Z")
        with mock.patch("nautobot.dcim.signals.rebuild_paths"):
            Cable(termination_a=ct_a, termination_b=ct_z, status=self.cable_status).save()
        self.assertEqual(
            CablePath.objects.filter(origin_type=ContentType.objects.get_for_model(CircuitTermination)).count(), 0
        )

        # Force a full retrace so the command actually visits the looped circuit terminations.
        output = self.run_command("--force", "--no-input")

        self.assertIn("Finished.", output)
        self.assertIn("Skipped 2 circuit terminations with inconsistent data", output)
        # The healthy cable is traced even though the loop could not be.
        self.assertEqual(CablePath.objects.get(origin_type=self.interface_ct, origin_id=good_a.pk).destination, good_b)
