from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status
from nautobot.ipam.factory import VLANGroupFactory
from nautobot.ipam.models import IPAddress, IPAddressToInterface, VLAN
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VirtualMachine, ClusterType, Cluster, VMInterface


class ClusterTestCase(TestCase):  # TODO: change to BaseModelTestCase
    def test_cluster_validation(self):
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        location_type = LocationType.objects.create(name="Location Type 1")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location.objects.create(name="Location 1", location_type=location_type, status=location_status)
        cluster = Cluster(name="Test Cluster 1", cluster_type=cluster_type, location=location)
        with self.assertRaises(ValidationError) as cm:
            cluster.validated_save()
        self.assertIn('Clusters may not associate to locations of type "Location Type 1"', str(cm.exception))

        location_type.content_types.add(ContentType.objects.get_for_model(Cluster))


class VirtualMachineTestCase(TestCase):  # TODO: change to BaseModelTestCase
    def setUp(self):
        statuses = Status.objects.get_for_model(VirtualMachine)

        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        self.cluster = Cluster.objects.create(name="Test Cluster 1", cluster_type=cluster_type)
        self.status = statuses[0]
        self.int_status = Status.objects.get_for_model(VMInterface).first()

    def test_vm_duplicate_name_per_cluster(self):
        vm1 = VirtualMachine(
            cluster=self.cluster,
            name="Test VM 1",
            status=self.status,
        )
        vm1.save()

        vm2 = VirtualMachine(
            cluster=vm1.cluster,
            name=vm1.name,
            status=self.status,
        )

        # Two VMs assigned to the same Cluster and no Tenant should fail validation
        with self.assertRaises(ValidationError):
            vm2.full_clean()

        tenant = Tenant.objects.first()
        vm1.tenant = tenant
        vm1.save()
        vm2.tenant = tenant

        # Two VMs assigned to the same Cluster and the same Tenant should fail validation
        with self.assertRaises(ValidationError):
            vm2.full_clean()

        vm2.tenant = None

        # Two VMs assigned to the same Cluster and different Tenants should pass validation
        vm2.full_clean()
        vm2.save()

    def test_primary_ip_validation_logic(self):
        vm1 = VirtualMachine(
            cluster=self.cluster,
            name="Test VM 1",
            status=self.status,
        )
        vm1.save()
        vm_interface = VMInterface.objects.create(name="Int1", virtual_machine=vm1, status=self.int_status)
        ips = list(IPAddress.objects.filter(ip_version=4)[:5]) + list(IPAddress.objects.filter(ip_version=6)[:5])
        vm_interface.add_ip_addresses(ips)
        vm1.primary_ip4 = vm_interface.ip_addresses.all().filter(ip_version=6).first()
        with self.assertRaises(ValidationError) as cm:
            vm1.validated_save()
        self.assertIn(
            f"{vm_interface.ip_addresses.all().filter(ip_version=6).first()} is not an IPv4 address",
            str(cm.exception),
        )
        vm1.primary_ip4 = None
        vm1.primary_ip6 = vm_interface.ip_addresses.all().filter(ip_version=4).first()
        with self.assertRaises(ValidationError) as cm:
            vm1.validated_save()
        self.assertIn(
            f"{vm_interface.ip_addresses.all().filter(ip_version=4).first()} is not an IPv6 address",
            str(cm.exception),
        )
        vm1.primary_ip4 = vm_interface.ip_addresses.all().filter(ip_version=4).first()
        vm1.primary_ip6 = vm_interface.ip_addresses.all().filter(ip_version=6).first()
        vm1.validated_save()


class VMInterfaceTestCase(TestCase):  # TODO: change to BaseModelTestCase
    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroupFactory.create(location=location)
        cls.vlan = VLAN.objects.create(
            name="VLAN 1", vid=100, location=location, status=vlan_status, vlan_group=vlan_group
        )
        clustertype = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="Test Cluster 1", cluster_type=clustertype)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cls.virtualmachine = VirtualMachine.objects.create(cluster=cluster, name="Test VM 1", status=vm_status)
        cls.int_status = Status.objects.get_for_model(VMInterface).first()

    def test_tagged_vlan_raise_error_if_mode_not_set_to_tagged(self):
        interface = VMInterface.objects.create(
            virtual_machine=self.virtualmachine, name="Interface 1", status=self.int_status
        )
        with self.assertRaises(ValidationError) as err:
            interface.tagged_vlans.add(self.vlan)
        self.assertEqual(
            err.exception.message_dict["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
        )

    def test_add_ip_addresses(self):
        """Test the `add_ip_addresses` helper method on `VMInterface`"""
        vm_interface = VMInterface.objects.create(
            name="Int1", virtual_machine=self.virtualmachine, status=self.int_status
        )
        ips = list(IPAddress.objects.all()[:10])

        # baseline (no vm_interface to ip address relationships exists)
        self.assertFalse(IPAddressToInterface.objects.filter(vm_interface=vm_interface).exists())

        # add single instance
        count = vm_interface.add_ip_addresses(ips[-1])
        self.assertEqual(count, 1)
        self.assertEqual(IPAddressToInterface.objects.filter(ip_address=ips[-1], vm_interface=vm_interface).count(), 1)

        # add multiple instances
        count = vm_interface.add_ip_addresses(ips[:5])
        self.assertEqual(count, 5)
        self.assertEqual(IPAddressToInterface.objects.filter(vm_interface=vm_interface).count(), 6)
        for ip in ips[:5]:
            self.assertEqual(IPAddressToInterface.objects.filter(ip_address=ip, vm_interface=vm_interface).count(), 1)

    def test_remove_ip_addresses(self):
        """Test the `remove_ip_addresses` helper method on `VMInterface`"""
        vm_interface = VMInterface.objects.create(
            name="Int1", virtual_machine=self.virtualmachine, status=self.int_status
        )
        ips = list(IPAddress.objects.all()[:10])

        # baseline (no vm_interface to ip address relationships exists)
        self.assertFalse(IPAddressToInterface.objects.filter(vm_interface=vm_interface).exists())

        vm_interface.add_ip_addresses(ips)
        self.assertEqual(IPAddressToInterface.objects.filter(vm_interface=vm_interface).count(), 10)

        # remove single instance
        count = vm_interface.remove_ip_addresses(ips[-1])
        self.assertEqual(count, 1)
        self.assertEqual(IPAddressToInterface.objects.filter(vm_interface=vm_interface).count(), 9)

        # remove multiple instances
        count = vm_interface.remove_ip_addresses(ips[:5])
        self.assertEqual(count, 5)
        self.assertEqual(IPAddressToInterface.objects.filter(vm_interface=vm_interface).count(), 4)

        count = vm_interface.remove_ip_addresses(ips)
        self.assertEqual(count, 4)
        self.assertEqual(IPAddressToInterface.objects.filter(vm_interface=vm_interface).count(), 0)

        # Test the pre_delete signal for IPAddressToInterface instances
        vm_interface.add_ip_addresses(ips)
        self.virtualmachine.primary_ip4 = vm_interface.ip_addresses.all().filter(ip_version=4).first()
        self.virtualmachine.primary_ip6 = vm_interface.ip_addresses.all().filter(ip_version=6).first()
        self.virtualmachine.save()

        vm_interface.remove_ip_addresses(self.virtualmachine.primary_ip4)
        self.virtualmachine.refresh_from_db()
        self.assertEqual(self.virtualmachine.primary_ip4, None)
        vm_interface.remove_ip_addresses(self.virtualmachine.primary_ip6)
        self.virtualmachine.refresh_from_db()
        self.assertEqual(self.virtualmachine.primary_ip6, None)
