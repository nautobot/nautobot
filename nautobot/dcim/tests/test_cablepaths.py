from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.dcim.models import (
    Cable,
    CablePath,
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
from nautobot.dcim.utils import disconnect_termination, object_to_path_node
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
        path1 = self.assertPathExists(
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
        path2 = self.assertPathExists(
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
        path3 = self.assertPathExists(
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
        path4 = self.assertPathExists(
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
        interface1.refresh_from_db()
        interface2.refresh_from_db()
        interface3.refresh_from_db()
        interface4.refresh_from_db()
        self.assertPathIsSet(interface1, path1)
        self.assertPathIsSet(interface2, path2)
        self.assertPathIsSet(interface3, path3)
        self.assertPathIsSet(interface4, path4)

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
        ).order_by("connector")
        # One CablePath per fan-out lane.
        self.assertEqual(trunk_paths.count(), 4)

        lane1_path = trunk_paths.get(connector=1)
        self.assertEqual(lane1_path.destination, if_lane1)
        self.assertFalse(lane1_path.is_split, msg=f"Lane 1 should be complete, got {lane1_path}")
        self.assertTrue(lane1_path.is_active)

        for connector in (2, 3, 4):
            partial = trunk_paths.get(connector=connector)
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
        self.assertEqual(trunk_paths_pre.get(connector=1).destination, if_lane1)
        self.assertEqual(trunk_paths_pre.get(connector=2).destination, if_lane2)
        self.assertTrue(trunk_paths_pre.get(connector=3).is_split)
        self.assertTrue(trunk_paths_pre.get(connector=4).is_split)

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
        lane1_trunk = trunk_paths_post.get(connector=1)
        self.assertIsNone(lane1_trunk.destination)
        self.assertTrue(lane1_trunk.is_split)

        # Lane 2 SURVIVES — this is the regression-protected assertion.
        lane2_trunk = trunk_paths_post.get(connector=2)
        self.assertEqual(lane2_trunk.destination, if_lane2, msg="Lane 2 trunk-side path was clobbered by disconnect")

        # Lanes 3 and 4 remain partial (unchanged).
        self.assertTrue(trunk_paths_post.get(connector=3).is_split)
        self.assertTrue(trunk_paths_post.get(connector=4).is_split)

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
