from constance.test import override_config

from nautobot.core.testing import TestCase
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.virtualization.forms import VirtualMachineForm
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine


class VirtualMachineFormTestCase(TestCase):
    @override_config(PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT=False)
    def test_create_virtual_machine_with_unassigned_primary_ip(self):
        namespace = Namespace.objects.create(name="Primary IP Test Namespace")
        Prefix.objects.create(
            prefix="198.51.100.0/24", namespace=namespace, status=Status.objects.get_for_model(Prefix).first()
        )
        ip = IPAddress.objects.create(
            address="198.51.100.1/24", namespace=namespace, status=Status.objects.get_for_model(IPAddress).first()
        )
        cluster = Cluster.objects.create(
            name="Primary IP Test Cluster", cluster_type=ClusterType.objects.create(name="Primary IP Test Type")
        )
        form = VirtualMachineForm(
            data={
                "name": "Primary IP Test VM",
                "status": Status.objects.get_for_model(VirtualMachine).first().pk,
                "cluster": cluster.pk,
                "unassigned_primary_ip4": ip.pk,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        virtual_machine = form.save()
        virtual_machine.refresh_from_db()
        self.assertEqual(virtual_machine.primary_ip4, ip)
