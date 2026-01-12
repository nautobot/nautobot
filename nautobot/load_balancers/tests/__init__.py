"""Unit tests for nautobot_load_balancer_models app."""

import datetime

from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS
from django.utils.timezone import make_aware

from nautobot.cloud.models import CloudResourceType, CloudService
from nautobot.dcim.models import (
    Device,
    DeviceRedundancyGroup,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    VirtualChassis,
)
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.load_balancers import choices, models
from nautobot.tenancy.models import Tenant, TenantGroup


# pylint: disable=too-many-statements
def generate_test_data(db=DEFAULT_DB_ALIAS):  # pylint: disable=invalid-name
    """Generate test data for the Load Balancer Models app."""
    objects = {}

    objects["status"], _ = Status.objects.using(db).get_or_create(name="Active")
    objects["status"].content_types.add(
        *ContentType.objects.using(db).filter(app_label="ipam").values_list("pk", flat=True)
    )
    objects["tenant_group1"], _ = TenantGroup.objects.using(db).get_or_create(name="Test Tenant Group 1")
    objects["tenant_group2"], _ = TenantGroup.objects.using(db).get_or_create(name="Test Tenant Group 2")
    objects["tenant1"], _ = Tenant.objects.using(db).get_or_create(
        name="Test Load Balancers Tenant 1", defaults={"tenant_group": objects["tenant_group1"]}
    )
    objects["tenant2"], _ = Tenant.objects.using(db).get_or_create(
        name="Test Load Balancers Tenant 2", defaults={"tenant_group": objects["tenant_group2"]}
    )
    objects["namespace"], _ = Namespace.objects.using(db).get_or_create(name="Test Load Balancers Namespace")
    objects["prefix"], _ = Prefix.objects.using(db).get_or_create(
        prefix="10.0.0.0/24", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )
    objects["source_nat_pool1"], _ = Prefix.objects.using(db).get_or_create(
        prefix="172.16.0.0/24", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )
    objects["source_nat_pool2"], _ = Prefix.objects.using(db).get_or_create(
        prefix="172.17.0.0/24", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )
    objects["ip_address"], _ = IPAddress.objects.using(db).get_or_create(
        host="10.0.0.40", mask_length="32", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )

    # Create Devices
    objects["status"].content_types.add(
        *ContentType.objects.using(db).filter(app_label="dcim").values_list("pk", flat=True)
    )
    role, _ = Role.objects.using(db).get_or_create(name="Test Role")
    role.content_types.add(ContentType.objects.using(db).get(app_label="dcim", model="device"))
    manufacturer, _ = Manufacturer.objects.using(db).get_or_create(name="Test Manufacturer")
    device_type, _ = DeviceType.objects.using(db).get_or_create(model="Test DeviceType", manufacturer=manufacturer)
    location_type, _ = LocationType.objects.using(db).get_or_create(name="Test LocationType")
    location, _ = Location.objects.using(db).get_or_create(
        name="Test Location", defaults={"location_type": location_type, "status": objects["status"]}
    )
    objects["device1"], _ = Device.objects.using(db).get_or_create(
        name="Test Device 1",
        defaults={
            "device_type": device_type,
            "location": location,
            "role": role,
            "status": objects["status"],
        },
    )
    objects["device2"], _ = Device.objects.using(db).get_or_create(
        name="Test Device 2",
        defaults={
            "device_type": device_type,
            "location": location,
            "role": role,
            "status": objects["status"],
        },
    )

    # Create Device Redundancy Groups
    objects["device_redundancy_group1"], _ = DeviceRedundancyGroup.objects.using(db).get_or_create(
        name="Test Device Redundancy Group 1", defaults={"status": objects["status"]}
    )
    objects["device_redundancy_group2"], _ = DeviceRedundancyGroup.objects.using(db).get_or_create(
        name="Test Device Redundancy Group 2", defaults={"status": objects["status"]}
    )

    # Create Cloud Services
    cloud_provider, _ = Manufacturer.objects.using(db).get_or_create(name="Test Cloud Provider")
    cloud_resource_type, _ = CloudResourceType.objects.using(db).get_or_create(
        name="Test Cloud Resource Type", defaults={"provider": cloud_provider}
    )
    cloud_resource_type.content_types.add(ContentType.objects.using(db).get(app_label="cloud", model="cloudservice"))
    objects["cloud_service1"], _ = CloudService.objects.using(db).get_or_create(
        name="Test Cloud Service 1", defaults={"cloud_resource_type": cloud_resource_type}
    )
    objects["cloud_service2"], _ = CloudService.objects.using(db).get_or_create(
        name="Test Cloud Service 2", defaults={"cloud_resource_type": cloud_resource_type}
    )

    # Create Virtual Chassis
    objects["virtual_chassis1"], _ = VirtualChassis.objects.using(db).get_or_create(name="Test Virtual Chassis 1")
    objects["virtual_chassis2"], _ = VirtualChassis.objects.using(db).get_or_create(name="Test Virtual Chassis 2")

    objects["vips"] = [
        IPAddress.objects.using(db).get_or_create(
            host=f"10.0.0.{i}", mask_length="32", namespace=objects["namespace"], defaults={"status": objects["status"]}
        )[0]
        for i in range(1, 33)
    ]

    # Create some Health Check Monitors
    objects["health_check_monitors"] = (
        models.HealthCheckMonitor.objects.using(db).create(
            name="HTTP Monitor 1",
            health_check_type=choices.HealthCheckTypeChoices.HTTP,
            port=8080,
            interval=30,
            retry=2,
            timeout=30,
            tenant=objects["tenant1"],
        ),
        models.HealthCheckMonitor.objects.using(db).create(
            name="HTTPS Monitor 1",
            health_check_type=choices.HealthCheckTypeChoices.HTTPS,
            port=8443,
            interval=20,
            retry=1,
            timeout=20,
            tenant=objects["tenant2"],
        ),
        models.HealthCheckMonitor.objects.using(db).create(
            name="ICMP Monitor 1",
            health_check_type=choices.HealthCheckTypeChoices.PING,
            interval=10,
            retry=0,
            timeout=10,
        ),
        models.HealthCheckMonitor.objects.using(db).create(
            name="HTTP Monitor 2",
            health_check_type=choices.HealthCheckTypeChoices.HTTP,
            port=8081,
            interval=30,
            retry=2,
            timeout=30,
            tenant=objects["tenant2"],
        ),
        models.HealthCheckMonitor.objects.using(db).create(
            name="HTTPS Monitor 2",
            health_check_type=choices.HealthCheckTypeChoices.HTTPS,
            port=9443,
            interval=20,
            retry=1,
            timeout=20,
            tenant=None,
        ),
        models.HealthCheckMonitor.objects.using(db).create(
            name="ICMP Monitor 2",
            health_check_type=choices.HealthCheckTypeChoices.PING,
            interval=10,
            retry=0,
            timeout=10,
        ),
    )

    # Create some Certificate Profiles
    objects["certificate_profiles"] = (
        models.CertificateProfile.objects.using(db).create(
            name="Certificate Profile 1",
            certificate_type=choices.CertificateTypeChoices.TYPE_CLIENT,
            certificate_file_path="/path/to/certificate.crt",
            chain_file_path="/path/to/chain.pem",
            key_file_path="/path/to/key.key",
            expiration_date=make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
            cipher="AES_128_GCM_SHA256",
            tenant=objects["tenant1"],
        ),
        models.CertificateProfile.objects.using(db).create(
            name="Certificate Profile 2",
            certificate_type=choices.CertificateTypeChoices.TYPE_SERVER,
            certificate_file_path="",
            chain_file_path="",
            key_file_path="",
            expiration_date=make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
            cipher="AES_256_GCM_SHA384",
            tenant=objects["tenant2"],
        ),
        models.CertificateProfile.objects.using(db).create(
            name="Certificate Profile 3",
            certificate_type=choices.CertificateTypeChoices.TYPE_MTLS,
            expiration_date=make_aware(datetime.datetime.now()),
        ),
        models.CertificateProfile.objects.using(db).create(
            name="Certificate Profile 4",
            certificate_type=choices.CertificateTypeChoices.TYPE_CLIENT,
            certificate_file_path="/path/to/certificate.crt",
            chain_file_path="/path/to/chain.pem",
            key_file_path="/path/to/key.key",
            expiration_date=make_aware(datetime.datetime.now()),
            cipher="AES_128_GCM_SHA256",
            tenant=None,
        ),
        models.CertificateProfile.objects.using(db).create(
            name="Certificate Profile 5",
            certificate_type=choices.CertificateTypeChoices.TYPE_SERVER,
            certificate_file_path="certificate.crt",
            chain_file_path="chain.pem",
            key_file_path="key.key",
            tenant=None,
        ),
        models.CertificateProfile.objects.using(db).create(
            name="Certificate Profile 6",
            certificate_type=choices.CertificateTypeChoices.TYPE_MTLS,
            certificate_file_path="",
            chain_file_path="",
            key_file_path="",
            expiration_date=None,
            tenant=None,
        ),
    )

    # Create 3 Load Balancer Pool instances for the generic delete tests to use
    models.LoadBalancerPool.objects.using(db).create(
        name="LBP1",
        load_balancing_algorithm=choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
    )
    models.LoadBalancerPool.objects.using(db).create(
        name="LBP2",
        load_balancing_algorithm=choices.LoadBalancingAlgorithmChoices.LEAST_CONNECTIONS,
    )
    models.LoadBalancerPool.objects.using(db).create(
        name="LBP3",
        load_balancing_algorithm=choices.LoadBalancingAlgorithmChoices.URL_HASH,
    )

    # Create 3 additional Load Balancer Pool instances for Load Balancer Pool Members to use
    objects["load_balancer_pools"] = (
        models.LoadBalancerPool.objects.using(db).create(
            name="LBP4_with_members",
            load_balancing_algorithm=choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
            health_check_monitor=objects["health_check_monitors"][0],
            tenant=objects["tenant1"],
        ),
        models.LoadBalancerPool.objects.using(db).create(
            name="LBP5_with_members",
            load_balancing_algorithm=choices.LoadBalancingAlgorithmChoices.LEAST_CONNECTIONS,
            health_check_monitor=objects["health_check_monitors"][1],
            tenant=objects["tenant2"],
        ),
        models.LoadBalancerPool.objects.using(db).create(
            name="LBP6_with_members",
            load_balancing_algorithm=choices.LoadBalancingAlgorithmChoices.URL_HASH,
            health_check_monitor=objects["health_check_monitors"][2],
        ),
    )

    # Create 3 Virtual Server instances for the generic delete tests to use
    models.VirtualServer.objects.using(db).create(
        name="VS1",
        vip=objects["vips"][-1],
        device_redundancy_group=objects["device_redundancy_group2"],
        load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_LAYER4,
        protocol=choices.ProtocolChoices.PROTOCOL_UDP,
        port=500,
    )
    models.VirtualServer.objects.using(db).create(
        name="VS2",
        vip=objects["vips"][-2],
        cloud_service=objects["cloud_service1"],
        load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_LAYER4,
        protocol=choices.ProtocolChoices.PROTOCOL_TCP,
        port=25000,
    )
    models.VirtualServer.objects.using(db).create(
        name="VS3",
        vip=objects["vips"][-3],
        cloud_service=objects["cloud_service2"],
        load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_DNS,
        protocol=choices.ProtocolChoices.PROTOCOL_DNS,
    )

    # Create 5 additional Virtual Server instances for the Load Balancer to use
    objects["virtual_servers"] = (
        models.VirtualServer.objects.using(db).create(
            name="VS4",
            vip=objects["vips"][1],
            load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_LAYER4,
            protocol=choices.ProtocolChoices.PROTOCOL_TCP,
            port=80,
            load_balancer_pool=objects["load_balancer_pools"][0],
            source_nat_type=choices.SourceNATTypeChoices.TYPE_POOL,
            source_nat_pool=objects["source_nat_pool1"],
            health_check_monitor=objects["health_check_monitors"][0],
            tenant=objects["tenant1"],
            virtual_chassis=objects["virtual_chassis1"],
        ),
        models.VirtualServer.objects.using(db).create(
            name="VS5",
            vip=objects["vips"][2],
            load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_LAYER4,
            protocol=choices.ProtocolChoices.PROTOCOL_TCP,
            load_balancer_pool=objects["load_balancer_pools"][1],
            port=443,
            source_nat_type=choices.SourceNATTypeChoices.TYPE_AUTO,
            source_nat_pool=objects["source_nat_pool1"],
            health_check_monitor=objects["health_check_monitors"][1],
            tenant=objects["tenant2"],
            virtual_chassis=objects["virtual_chassis2"],
        ),
        models.VirtualServer.objects.using(db).create(
            name="VS6",
            vip=objects["vips"][3],
            load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_DNS,
            protocol=choices.ProtocolChoices.PROTOCOL_DNS,
            load_balancer_pool=objects["load_balancer_pools"][2],
            port=0,
            source_nat_type=choices.SourceNATTypeChoices.TYPE_STATIC,
            source_nat_pool=objects["source_nat_pool2"],
            health_check_monitor=objects["health_check_monitors"][2],
            device=objects["device1"],
        ),
        models.VirtualServer.objects.using(db).create(
            name="VS7", vip=objects["vips"][4], port=25, device=objects["device2"]
        ),
        models.VirtualServer.objects.using(db).create(
            name="VS8", vip=objects["vips"][5], port=5432, device_redundancy_group=objects["device_redundancy_group1"]
        ),
        models.VirtualServer.objects.using(db).create(
            name="VS9",
            vip=objects["vips"][1],
            load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_LAYER7,
            protocol=choices.ProtocolChoices.PROTOCOL_HTTPS,
            port=443,
            load_balancer_pool=objects["load_balancer_pools"][0],
            source_nat_type=choices.SourceNATTypeChoices.TYPE_POOL,
            source_nat_pool=objects["source_nat_pool1"],
            health_check_monitor=objects["health_check_monitors"][0],
            tenant=objects["tenant1"],
            virtual_chassis=objects["virtual_chassis1"],
        ),
    )

    objects["ip1"], _ = IPAddress.objects.using(db).get_or_create(
        host="10.0.0.41", mask_length="32", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )
    objects["ip2"], _ = IPAddress.objects.using(db).get_or_create(
        host="10.0.0.42", mask_length="32", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )
    objects["ip3"], _ = IPAddress.objects.using(db).get_or_create(
        host="10.0.0.43", mask_length="32", namespace=objects["namespace"], defaults={"status": objects["status"]}
    )

    # Add Load Balancer Pool Member to Status content types
    objects["status"].content_types.add(ContentType.objects.db_manager(db).get_for_model(models.LoadBalancerPoolMember))

    # Create 3 Load Balancer Pool Member instances for the generic delete tests to use
    models.LoadBalancerPoolMember.objects.using(db).create(
        load_balancer_pool=objects["load_balancer_pools"][0],
        ip_address=objects["ip1"],
        label="Test Load Balancer Pool Member 1",
        port=80,
        status=objects["status"],
        tenant=objects["tenant1"],
    )
    models.LoadBalancerPoolMember.objects.using(db).create(
        load_balancer_pool=objects["load_balancer_pools"][1],
        ip_address=objects["ip2"],
        label="Test Load Balancer Pool Member 2",
        port=8080,
        status=objects["status"],
        tenant=objects["tenant2"],
    )
    models.LoadBalancerPoolMember.objects.using(db).create(
        load_balancer_pool=objects["load_balancer_pools"][2],
        ip_address=objects["ip3"],
        label="Test Load Balancer Pool Member 3",
        port=443,
        status=objects["status"],
    )

    objects["load_balancer_pool_members"] = (
        models.LoadBalancerPoolMember.objects.using(db).create(
            load_balancer_pool=objects["load_balancer_pools"][0],
            ip_address=objects["ip2"],
            label="Test Load Balancer Pool Member 1",
            port=80,
            status=objects["status"],
            health_check_monitor=objects["health_check_monitors"][0],
        ),
        models.LoadBalancerPoolMember.objects.using(db).create(
            load_balancer_pool=objects["load_balancer_pools"][1],
            ip_address=objects["ip3"],
            label="Test Load Balancer Pool Member 2",
            port=161,
            status=objects["status"],
            health_check_monitor=objects["health_check_monitors"][1],
        ),
        models.LoadBalancerPoolMember.objects.using(db).create(
            load_balancer_pool=objects["load_balancer_pools"][2],
            ip_address=objects["ip1"],
            label="Test Load Balancer Pool Member 3",
            port=25,
            status=objects["status"],
            health_check_monitor=objects["health_check_monitors"][2],
        ),
    )

    # Create 3 VirtualServerCertificateProfileAssignment instances for the generic delete tests to use
    models.VirtualServerCertificateProfileAssignment.objects.using(db).create(
        virtual_server=objects["virtual_servers"][0],
        certificate_profile=objects["certificate_profiles"][0],
    )
    models.VirtualServerCertificateProfileAssignment.objects.using(db).create(
        virtual_server=objects["virtual_servers"][1],
        certificate_profile=objects["certificate_profiles"][1],
    )
    models.VirtualServerCertificateProfileAssignment.objects.using(db).create(
        virtual_server=objects["virtual_servers"][2],
        certificate_profile=objects["certificate_profiles"][2],
    )

    # A few additional to test the UI
    models.VirtualServerCertificateProfileAssignment.objects.using(db).create(
        virtual_server=objects["virtual_servers"][0],
        certificate_profile=objects["certificate_profiles"][1],
    )
    models.VirtualServerCertificateProfileAssignment.objects.using(db).create(
        virtual_server=objects["virtual_servers"][1],
        certificate_profile=objects["certificate_profiles"][2],
    )

    # Create 3 LoadBalancerPoolMemberCertificateProfileAssignment instances for the generic delete tests to use
    models.LoadBalancerPoolMemberCertificateProfileAssignment.objects.using(db).create(
        load_balancer_pool_member=objects["load_balancer_pool_members"][0],
        certificate_profile=objects["certificate_profiles"][0],
    )
    models.LoadBalancerPoolMemberCertificateProfileAssignment.objects.using(db).create(
        load_balancer_pool_member=objects["load_balancer_pool_members"][1],
        certificate_profile=objects["certificate_profiles"][1],
    )
    models.LoadBalancerPoolMemberCertificateProfileAssignment.objects.using(db).create(
        load_balancer_pool_member=objects["load_balancer_pool_members"][2],
        certificate_profile=objects["certificate_profiles"][2],
    )

    # A few additional to test the UI
    models.LoadBalancerPoolMemberCertificateProfileAssignment.objects.using(db).create(
        load_balancer_pool_member=objects["load_balancer_pool_members"][0],
        certificate_profile=objects["certificate_profiles"][1],
    )
    models.LoadBalancerPoolMemberCertificateProfileAssignment.objects.using(db).create(
        load_balancer_pool_member=objects["load_balancer_pool_members"][1],
        certificate_profile=objects["certificate_profiles"][2],
    )

    return objects


# pylint: disable=too-few-public-methods
class LoadBalancerModelsTestCaseMixin:
    """Base test case for load_balancers."""

    @classmethod
    def setUpTestData(cls):  # pylint: disable=invalid-name
        """Setup test data."""
        for key, value in generate_test_data().items():
            setattr(cls, key, value)
