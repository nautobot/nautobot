"""Tests for GraphQL Relationship caching to prevent N+1 queries."""

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import override_settings
from graphql import parse, execute

from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras.models import Relationship, RelationshipAssociation, Role, Status
from nautobot.virtualization.models import VirtualMachine, Cluster, ClusterType


class GraphQLRelationshipCacheTestCase(TestCase):
    """Test that relationship caching prevents N+1 queries."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data with relationships."""
        super().setUpTestData()

        # Create statuses and roles
        cls.device_status = Status.objects.get_for_model(Device).first()
        cls.device_role = Role.objects.get_for_model(Device).first()
        cls.vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cls.location_status = Status.objects.get_for_model(Location).first()

        # Create location
        cls.location_type = LocationType.objects.get(name="Campus")
        cls.location = Location.objects.create(
            name="Test Location",
            location_type=cls.location_type,
            status=cls.location_status
        )

        # Create 10 devices
        cls.devices = []
        for i in range(10):
            device = Device.objects.create(
                name=f"Device-{i}",
                location=cls.location,
                role=cls.device_role,
                status=cls.device_status,
            )
            cls.devices.append(device)

        # Create 10 VMs
        cls.cluster_type = ClusterType.objects.first()
        if not cls.cluster_type:
            cls.cluster_type = ClusterType.objects.create(name="Test Cluster Type")
        cls.cluster = Cluster.objects.create(name="Test Cluster", cluster_type=cls.cluster_type)
        cls.vms = []
        for i in range(10):
            vm = VirtualMachine.objects.create(
                name=f"VM-{i}",
                cluster=cls.cluster,
                status=cls.vm_status,
            )
            cls.vms.append(vm)

        # Create a many-to-many relationship: Device -> VirtualMachine
        cls.rel_device_vm = Relationship(
            label="Device to VMs",
            key="device_to_vms",
            source_type=ContentType.objects.get_for_model(Device),
            destination_type=ContentType.objects.get_for_model(VirtualMachine),
            type="many-to-many",
        )
        cls.rel_device_vm.validated_save()

        # Create associations: each device -> 2 VMs
        for i, device in enumerate(cls.devices):
            for j in range(2):
                vm_idx = (i * 2 + j) % len(cls.vms)
                RelationshipAssociation.objects.create(
                    relationship=cls.rel_device_vm,
                    source=device,
                    destination=cls.vms[vm_idx],
                )

    def execute_query(self, query, variables=None):
        """Execute a GraphQL query."""
        from graphene_django.settings import graphene_settings
        schema = graphene_settings.SCHEMA.graphql_schema
        document = parse(query)
        request = self.client_class().request()
        request.user = self.user
        if variables:
            return execute(schema=schema, document=document, context_value=request, variable_values=variables)
        else:
            return execute(schema=schema, document=document, context_value=request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], DEBUG=True)
    def test_relationship_query_count(self):
        """Test that querying relationships doesn't cause N+1 queries."""
        query = """
            query {
                devices {
                    id
                    name
                    rel_device_to_vms {
                        id
                        name
                    }
                }
            }
        """

        connection.queries_log.clear()
        result = self.execute_query(query)

        self.assertIsNone(result.errors, f"GraphQL errors: {result.errors}")
        self.assertEqual(len(result.data["devices"]), len(self.devices))

        # Count queries - should be significantly less than N+1
        # With caching: expect ~10-15 queries instead of 20+ (10 devices * 2 queries each)
        query_count = len(connection.queries)
        self.assertLess(
            query_count,
            20,
            f"Too many queries: {query_count}. Expected < 20 with caching."
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_relationship_results_correctness(self):
        """Test that relationship caching returns correct results."""
        query = """
            query {
                devices {
                    id
                    name
                    rel_device_to_vms {
                        id
                        name
                    }
                }
            }
        """

        result = self.execute_query(query)
        self.assertIsNone(result.errors, f"GraphQL errors: {result.errors}")

        # Verify each device has the correct VMs
        for device_data in result.data["devices"]:
            device = Device.objects.get(id=device_data["id"])

            # Get expected VMs for this device
            expected_vms = VirtualMachine.objects.filter(
                destination_for_associations__relationship=self.rel_device_vm,
                destination_for_associations__source_id=device.id
            ).values_list("id", flat=True)

            actual_vm_ids = {vm["id"] for vm in device_data["rel_device_to_vms"]}
            expected_vm_ids = {str(vm_id) for vm_id in expected_vms}

            self.assertEqual(
                actual_vm_ids,
                expected_vm_ids,
                f"Device {device.name} has incorrect VMs"
            )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_single_device_query(self):
        """Test that single device queries work correctly."""
        query = """
            query($deviceId: ID!) {
                device(id: $deviceId) {
                    id
                    name
                    rel_device_to_vms {
                        id
                        name
                    }
                }
            }
        """

        result = self.execute_query(query, variables={"deviceId": str(self.devices[0].id)})

        self.assertIsNone(result.errors, f"GraphQL errors: {result.errors}")
        self.assertIsNotNone(result.data["device"])
        self.assertEqual(result.data["device"]["name"], self.devices[0].name)
        self.assertIsInstance(result.data["device"]["rel_device_to_vms"], list)
