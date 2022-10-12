from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.dcim.models import Location, LocationType, Site
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VirtualMachine, ClusterType, Cluster


class ClusterTestCase(TestCase):
    def test_cluster_validation(self):
        active = Status.objects.get(name="Active")
        cluster_type = ClusterType.objects.create(name="Test Cluster Type 1")
        site_1 = Site.objects.create(name="Test Site 1", status=active)
        site_2 = Site.objects.create(name="Test Site 2", status=active)
        location_type = LocationType.objects.create(name="Location Type 1")
        location = Location.objects.create(name="Location 1", location_type=location_type, site=site_1)
        cluster = Cluster(name="Test Cluster 1", type=cluster_type, site=site_1, location=location)
        with self.assertRaises(ValidationError) as cm:
            cluster.validated_save()
        self.assertIn('Clusters may not associate to locations of type "Location Type 1"', str(cm.exception))

        location_type.content_types.add(ContentType.objects.get_for_model(Cluster))
        cluster.site = site_2
        with self.assertRaises(ValidationError) as cm:
            cluster.validated_save()
        self.assertIn('Location "Location 1" does not belong to site "Test Site 2"', str(cm.exception))


class VirtualMachineTestCase(TestCase):
    def setUp(self):
        statuses = Status.objects.get_for_model(VirtualMachine)

        cluster_type = ClusterType.objects.create(name="Test Cluster Type 1", slug="test-cluster-type-1")
        self.cluster = Cluster.objects.create(name="Test Cluster 1", type=cluster_type)
        self.status = statuses.get(slug="active")

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

        tenant = Tenant.objects.create(name="Test Tenant 1", slug="test-tenant-1")
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
