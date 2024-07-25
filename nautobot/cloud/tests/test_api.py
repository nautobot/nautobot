from nautobot.cloud import models
from nautobot.core.testing import APIViewTestCases
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import Prefix


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
        models.CloudAccount.objects.create(
            name="Deletable Account 1", account_number="12345", provider=manufacturers[0]
        )
        models.CloudAccount.objects.create(
            name="Deletable Account 2", account_number="23467", provider=manufacturers[0]
        )
        models.CloudAccount.objects.create(
            name="Deletable Account 3", account_number="345678", provider=manufacturers[0]
        )
        cls.create_data = [
            {
                "name": "Account 1",
                "account_number": "1238910123",
                "provider": manufacturers[0].pk,
                "secrets_group": secrets_groups[0].pk,
            },
            {
                "name": "Account 2",
                "account_number": "5123121012",
                "provider": manufacturers[1].pk,
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "name": "Account 3",
                "account_number": "6782109915",
                "provider": manufacturers[3].pk,
                "secrets_group": secrets_groups[2].pk,
                "description": "This is cloud account 3",
            },
            {
                "name": "Account 4",
                "account_number": "0989076098",
                "provider": manufacturers[4].pk,
            },
        ]
        cls.bulk_update_data = {
            "provider": manufacturers[2].pk,
            "secrets_group": secrets_groups[1].pk,
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
                "content_types": [],
            },
        ]


class CloudNetworkTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudNetwork

    @classmethod
    def setUpTestData(cls):
        cloud_network_parent = models.CloudNetwork.objects.filter(parent__isnull=True).first()
        cloud_accounts = models.CloudAccount.objects.all()[:3]
        cloud_resource_types = models.CloudResourceType.objects.get_for_model(models.CloudNetwork).all()[:3]
        models.CloudNetwork.objects.create(
            name="Deletable Cloud Network 1",
            cloud_resource_type=cloud_resource_types[0],
            cloud_account=cloud_accounts[0],
        )
        models.CloudNetwork.objects.create(
            name="Deletable Cloud Network 2",
            cloud_resource_type=cloud_resource_types[0],
            cloud_account=cloud_accounts[0],
        )
        models.CloudNetwork.objects.create(
            name="Deletable Cloud Network 3",
            cloud_resource_type=cloud_resource_types[0],
            cloud_account=cloud_accounts[0],
        )
        cls.create_data = [
            {
                "name": "Test VPC",
                "description": "A VPC is one example object that a CloudNetwork might represent",
                "cloud_resource_type": cloud_resource_types[0].pk,
                "cloud_account": cloud_accounts[0].pk,
                "extra_config": {},
            },
            {
                "name": "Test VNET",
                "description": "A VNET is another example object that a CloudNetwork might be",
                "cloud_resource_type": cloud_resource_types[1].pk,
                "cloud_account": cloud_accounts[1].pk,
                "extra_config": {
                    "alpha": 1,
                    "beta": False,
                },
            },
            {
                "name": "Test subnet",
                "cloud_resource_type": cloud_resource_types[0].pk,
                "cloud_account": cloud_accounts[0].pk,
                "parent": cloud_network_parent.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "A new description",
            "cloud_resource_type": cloud_resource_types[1].pk,
            "cloud_account": cloud_accounts[1].pk,
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


class CloudServiceTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudService

    @classmethod
    def setUpTestData(cls):
        cloud_accounts = models.CloudAccount.objects.all()
        cloud_resource_types = models.CloudResourceType.objects.get_for_model(models.CloudService).all()

        models.CloudService.objects.create(
            name="Deletable Service 1",
            description="It really is deletable",
            cloud_account=cloud_accounts[0],
            cloud_resource_type=cloud_resource_types[0],
        )
        models.CloudService.objects.create(
            name="Deletable Service 2",
            cloud_resource_type=cloud_resource_types[1],
        )
        models.CloudService.objects.create(
            name="Deletable Service 3",
            cloud_resource_type=cloud_resource_types[2],
        )
        cls.create_data = [
            {
                "name": "Cloud Service 1",
                "description": "The first cloud service",
                "cloud_account": cloud_accounts[0].pk,
                "cloud_resource_type": cloud_resource_types[0].pk,
                "extra_config": {"status": "hey"},
            },
            {
                "name": "Cloud Service 2",
                "cloud_account": cloud_accounts[1].pk,
                "cloud_resource_type": cloud_resource_types[1].pk,
                "extra_config": {"status": "hello"},
            },
            {
                "name": "Cloud Service 3",
                "cloud_account": cloud_accounts[2].pk,
                "cloud_resource_type": cloud_resource_types[2].pk,
                "extra_config": {"status": "greetings", "role": 1},
            },
            {
                "name": "Cloud Service 4",
                "cloud_resource_type": cloud_resource_types[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "cloud_resource_type": cloud_resource_types[1].pk,
            "description": "testing",
        }
