from nautobot.cloud import models
from nautobot.core.testing import APIViewTestCases
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import SecretsGroup


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


class CloudTypeTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudType
    bulk_update_data = {
        "description": "Some generic description of multiple types. Not very useful.",
    }

    @classmethod
    def setUpTestData(cls):
        manufacturers = Manufacturer.objects.all()
        cls.create_data = [
            {
                "name": "Account 1",
                "provider": manufacturers[0].pk,
                "content_types": ["ipam.prefix", "ipam.vlangroup", "ipam.vlan"],
                "description": "An example description",
            },
            {
                "name": "Account 2",
                "provider": manufacturers[1].pk,
                "content_types": ["ipam.prefix", "ipam.vlangroup"],
            },
            {
                "name": "Account 3",
                "provider": manufacturers[3].pk,
                "content_types": ["ipam.prefix"],
            },
            {
                "name": "Account 4",
                "provider": manufacturers[4].pk,
                "description": "An example description",
                "content_types": ["ipam.vlan"],
            },
        ]


class CloudNetworkTest(APIViewTestCases.APIViewTestCase):
    model = models.CloudNetwork

    @classmethod
    def setUpTestData(cls):
        cls.create_data = [
            {
                "name": "Test VPC",
                "description": "A VPC is one example object that a CloudNetwork might represent",
                "cloud_type": models.CloudType.objects.first().pk,
                "cloud_account": models.CloudAccount.objects.first().pk,
                "extra_config": {},
            },
            {
                "name": "Test VNET",
                "description": "A VNET is another example object that a CloudNetwork might be",
                "cloud_type": models.CloudType.objects.last().pk,
                "cloud_account": models.CloudAccount.objects.last().pk,
                "extra_config": {
                    "alpha": 1,
                    "beta": False,
                },
            },
            {
                "name": "Test subnet",
                "cloud_type": models.CloudType.objects.first().pk,
                "cloud_account": models.CloudAccount.objects.first().pk,
                "parent": models.CloudNetwork.objects.filter(parent__isnull=True).first().pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "A new description",
            "cloud_type": models.CloudType.objects.last().pk,
            "cloud_account": models.CloudAccount.objects.last().pk,
            "extra_config": {"A": 1, "B": 2, "C": 3},
        }
