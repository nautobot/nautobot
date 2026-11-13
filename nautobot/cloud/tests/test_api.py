from nautobot.cloud import models
from nautobot.cloud.tests.utils import create_cloud_fixtures
from nautobot.core.testing import APIViewTestCases
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import SecretsGroup, Status
from nautobot.ipam.models import IPAddress, Prefix


class CloudAccountTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudAccount

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )
        manufacturers = Manufacturer.objects.all()
        statuses = Status.objects.get_for_model(models.CloudAccount)
        for i in range(1, 4):
            models.CloudAccount.objects.create(
                name=f"Deletable Account {i}", account_number=f"{i}2345", provider=manufacturers[0], status=statuses[0]
            )
        cloud_account_group = models.CloudAccountGroup.objects.first()
        cls.create_data = [
            {
                "name": "Account 1",
                "account_number": "1238910123",
                "provider": manufacturers[0].pk,
                "secrets_group": secrets_groups[0].pk,
                "status": statuses[0].pk,
            },
            {
                "name": "Account 2",
                "account_number": "5123121012",
                "provider": manufacturers[1].pk,
                "secrets_group": secrets_groups[1].pk,
                "status": statuses[1].pk,
                "cloud_account_group": cloud_account_group.pk,
            },
            {
                "name": "Account 3",
                "account_number": "6782109915",
                "provider": manufacturers[3].pk,
                "secrets_group": secrets_groups[2].pk,
                "description": "This is cloud account 3",
                "status": statuses[0].pk,
            },
            {
                "name": "Account 4",
                "account_number": "0989076098",
                "provider": manufacturers[4].pk,
                "status": statuses[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "provider": manufacturers[2].pk,
            "secrets_group": secrets_groups[1].pk,
            "status": statuses[1].pk,
        }


class CloudAccountGroupTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudAccountGroup

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("API Account Group")
        group_type, other_group_type = fixtures.account_group_types
        parent = models.CloudAccountGroup.objects.create(name="API Parent Group", cloud_resource_type=group_type)
        for i in range(1, 4):
            models.CloudAccountGroup.objects.create(name=f"Deletable Group {i}", cloud_resource_type=group_type)
        cls.create_data = [
            {"name": "Group 1", "cloud_resource_type": group_type.pk},
            {"name": "Group 2", "cloud_resource_type": group_type.pk, "parent": parent.pk},
            {
                "name": "Group 3",
                "cloud_resource_type": other_group_type.pk,
                "description": "An organizational unit",
                "extra_config": {"organizationalUnitId": "ou-1234"},
            },
        ]
        cls.bulk_update_data = {
            "description": "Updated description",
            "cloud_resource_type": other_group_type.pk,
        }


class CloudResourceGroupTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudResourceGroup

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("API Resource Group")
        rg_type, other_rg_type = fixtures.resource_group_types
        for i in range(1, 4):
            models.CloudResourceGroup.objects.create(
                name=f"Deletable Resource Group {i}", cloud_account=fixtures.accounts[0], cloud_resource_type=rg_type
            )
        cls.create_data = [
            {
                "name": "rg-network",
                "cloud_account": fixtures.accounts[0].pk,
                "cloud_resource_type": rg_type.pk,
                "provider_resource_id": "/subscriptions/0001/resourceGroups/rg-network",
            },
            {
                "name": "rg-network",
                "cloud_account": fixtures.accounts[1].pk,
                "cloud_resource_type": rg_type.pk,
            },
            {
                "name": "rg-apps",
                "cloud_account": fixtures.accounts[1].pk,
                "cloud_resource_type": other_rg_type.pk,
                "description": "Application resources",
            },
        ]
        cls.bulk_update_data = {
            "description": "Updated description",
        }


class CloudResourceTypeTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudResourceType
    bulk_update_data = {
        "description": "Some generic description of multiple types. Not very useful.",
    }

    @classmethod
    def setUpTestData(cls):
        manufacturers = Manufacturer.objects.all()
        models.CloudResourceType.objects.create(name="Deletable Type 1", provider=manufacturers[0])
        models.CloudResourceType.objects.create(name="Deletable Type 2", provider=manufacturers[0])
        models.CloudResourceType.objects.create(name="Deletable Type 3", provider=manufacturers[0])
        cls.create_data = [
            {
                "name": "Type 1",
                "provider": manufacturers[0].pk,
                "content_types": ["cloud.cloudnetwork"],
                "description": "An example description",
            },
            {
                "name": "Type 2",
                "provider": manufacturers[1].pk,
                "content_types": [],
            },
            {
                "name": "Type 3",
                "provider": manufacturers[3].pk,
                "content_types": ["cloud.cloudnetwork"],
            },
            {
                "name": "Type 4",
                "provider": manufacturers[4].pk,
                "description": "An example description",
                "content_types": ["cloud.cloudaccountgroup", "cloud.cloudresourcegroup"],
            },
        ]


class CloudNetworkTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudNetwork

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("API Network")
        network_type, subnet_type = fixtures.network_types
        status = fixtures.network_statuses[0]
        resource_group = models.CloudResourceGroup.objects.create(
            name="API rg-network",
            cloud_account=fixtures.accounts[0],
            cloud_resource_type=fixtures.resource_group_types[0],
        )
        cloud_network_parent = models.CloudNetwork.objects.create(
            name="API Parent Network",
            cloud_resource_type=network_type,
            cloud_account=fixtures.accounts[0],
            status=status,
        )
        for i in range(1, 4):
            models.CloudNetwork.objects.create(
                name=f"Deletable Cloud Network {i}",
                cloud_resource_type=network_type,
                cloud_account=fixtures.accounts[0],
                status=status,
            )
        cls.create_data = [
            {
                "name": "Test VPC",
                "description": "A VPC is one example object that a CloudNetwork might represent",
                "cloud_resource_type": network_type.pk,
                "cloud_account": fixtures.accounts[0].pk,
                "status": status.pk,
                "provider_resource_id": "arn:aws:ec2:us-east-1:000000000001:vpc/vpc-0001",
                "extra_config": {},
            },
            {
                "name": "Test VNET",
                "description": "A VNET is another example object that a CloudNetwork might be",
                "cloud_resource_type": network_type.pk,
                "cloud_account": fixtures.accounts[0].pk,
                "cloud_resource_group": resource_group.pk,
                "status": fixtures.network_statuses[1].pk,
                "extra_config": {
                    "alpha": 1,
                    "beta": False,
                },
            },
            {
                "name": "Test subnet",
                "cloud_resource_type": subnet_type.pk,
                "cloud_account": fixtures.accounts[0].pk,
                "parent": cloud_network_parent.pk,
                "status": status.pk,
            },
            {
                "name": "Test VPC",
                "cloud_resource_type": network_type.pk,
                "cloud_account": fixtures.accounts[1].pk,
                "status": status.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "A new description",
            "status": fixtures.network_statuses[1].pk,
            "extra_config": {"A": 1, "B": 2, "C": 3},
        }


class CloudNetworkPrefixAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudNetworkPrefixAssignment

    @classmethod
    def setUpTestData(cls):
        prefixes = list(Prefix.objects.all()[:3])
        cls.create_data = [
            {
                "cloud_network": models.CloudNetwork.objects.exclude(prefixes=prefixes[0]).first().pk,
                "prefix": prefixes[0].pk,
            },
            {
                "cloud_network": models.CloudNetwork.objects.exclude(prefixes=prefixes[1]).first().pk,
                "prefix": prefixes[1].pk,
            },
            {
                "cloud_network": models.CloudNetwork.objects.exclude(prefixes=prefixes[2]).first().pk,
                "prefix": prefixes[2].pk,
            },
        ]


class CloudServiceNetworkAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudServiceNetworkAssignment

    @classmethod
    def setUpTestData(cls):
        cloud_networks = models.CloudNetwork.objects.all()[:3]
        cls.create_data = [
            {
                "cloud_network": cloud_networks[0].pk,
                "cloud_service": models.CloudService.objects.exclude(cloud_networks=cloud_networks[0]).first().pk,
            },
            {
                "cloud_network": cloud_networks[1].pk,
                "cloud_service": models.CloudService.objects.exclude(cloud_networks=cloud_networks[1]).first().pk,
            },
            {
                "cloud_network": cloud_networks[2].pk,
                "cloud_service": models.CloudService.objects.exclude(cloud_networks=cloud_networks[2]).first().pk,
            },
        ]


class CloudServiceIPAddressAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudServiceIPAddressAssignment

    @classmethod
    def setUpTestData(cls):
        ip_addresses = IPAddress.objects.all()[:3]
        cls.create_data = [
            {
                "ip_address": ip_address.pk,
                "cloud_service": models.CloudService.objects.exclude(ip_addresses=ip_address).first().pk,
            }
            for ip_address in ip_addresses
        ]


class CloudServiceTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudService

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("API Service")
        service_type, other_service_type = fixtures.service_types
        status = fixtures.service_statuses[0]
        resource_group = models.CloudResourceGroup.objects.create(
            name="API rg-apps", cloud_account=fixtures.accounts[0], cloud_resource_type=fixtures.resource_group_types[0]
        )
        models.CloudService.objects.create(
            name="Deletable Service 1",
            description="It really is deletable",
            cloud_account=fixtures.accounts[0],
            cloud_resource_type=service_type,
            status=status,
        )
        models.CloudService.objects.create(name="Deletable Service 2", cloud_resource_type=service_type, status=status)
        models.CloudService.objects.create(
            name="Deletable Service 3", cloud_resource_type=other_service_type, status=status
        )
        cls.create_data = [
            {
                "name": "Cloud Service 1",
                "description": "The first cloud service",
                "cloud_account": fixtures.accounts[0].pk,
                "cloud_resource_type": service_type.pk,
                "status": status.pk,
                "extra_config": {"status": "hey"},
            },
            {
                "name": "Cloud Service 2",
                "cloud_account": fixtures.accounts[0].pk,
                "cloud_resource_group": resource_group.pk,
                "cloud_resource_type": other_service_type.pk,
                "status": status.pk,
                "provider_resource_id": "//sqladmin.googleapis.com/projects/project-1/instances/cloud-service-2",
                "extra_config": {"status": "hello"},
            },
            {
                "name": "Cloud Service 3",
                "cloud_account": fixtures.accounts[2].pk,
                "cloud_resource_type": other_service_type.pk,
                "status": fixtures.service_statuses[1].pk,
                "extra_config": {"status": "greetings", "role": 1},
            },
            {
                "name": "Cloud Service 4",
                "cloud_resource_type": service_type.pk,
                "status": status.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "testing",
            "status": fixtures.service_statuses[1].pk,
        }
