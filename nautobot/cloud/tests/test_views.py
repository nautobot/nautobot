from django.contrib.contenttypes.models import ContentType

from nautobot.cloud.models import (
    CloudAccount,
    CloudAccountGroup,
    CloudNetwork,
    CloudResourceGroup,
    CloudResourceType,
    CloudService,
)
from nautobot.cloud.tests.utils import create_cloud_fixtures
from nautobot.core.testing import ViewTestCases
from nautobot.core.testing.utils import post_data
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import SecretsGroup, Status, Tag


class CloudAccountTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudAccount

    @classmethod
    def setUpTestData(cls):
        providers = Manufacturer.objects.all()
        statuses = Status.objects.get_for_model(CloudAccount)
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )
        for i in range(1, 4):
            CloudAccount.objects.create(
                name=f"Deletable Cloud Account {i}",
                account_number=f"{i}23456",
                provider=providers[0],
                status=statuses[0],
            )
        cls.form_data = {
            "name": "New Cloud Account",
            "account_number": "8928371982310",
            "provider": providers[1].pk,
            "cloud_account_group": CloudAccountGroup.objects.first().pk,
            "status": statuses[0].pk,
            "secrets_group": secrets_groups[1].pk,
            "description": "A new cloud account",
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudAccount)],
        }

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "status": statuses[1].pk,
            "secrets_group": secrets_groups[1].pk,
            "description": "New description",
        }

    def test_post_without_secrets_group(self):
        """Assert Secrets Group form field is not required: Fix for https://github.com/nautobot/nautobot/issues/6096"""
        self.add_permissions("cloud.add_cloudaccount", "dcim.view_manufacturer", "extras.view_status")
        form_data = {
            "name": "New Cloud Account 2",
            "account_number": "8928371982311",
            "provider": Manufacturer.objects.first().pk,
            "status": Status.objects.get_for_model(CloudAccount).first().pk,
            "description": "A new cloud account",
        }
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertTrue(CloudAccount.objects.filter(name="New Cloud Account 2").exists())


class CloudAccountGroupTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudAccountGroup
    allowed_number_of_tree_queries_per_view_type = {"retrieve": 1}

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("View Account Group")
        group_type, other_group_type = fixtures.account_group_types
        parent = CloudAccountGroup.objects.create(name="View Parent Group", cloud_resource_type=group_type)
        for i in range(1, 4):
            CloudAccountGroup.objects.create(name=f"Deletable Cloud Account Group {i}", cloud_resource_type=group_type)

        cls.form_data = {
            "name": "New Cloud Account Group",
            "parent": parent.pk,
            "cloud_resource_type": group_type.pk,
            "description": "A new cloud account group",
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudAccountGroup)],
        }

        cls.bulk_edit_data = {
            "cloud_resource_type": other_group_type.pk,
            "description": "New description",
        }


class CloudResourceGroupTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudResourceGroup

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("View Resource Group")
        rg_type, other_rg_type = fixtures.resource_group_types
        for i in range(1, 4):
            CloudResourceGroup.objects.create(
                name=f"Deletable Cloud Resource Group {i}",
                cloud_account=fixtures.accounts[0],
                cloud_resource_type=rg_type,
            )

        cls.form_data = {
            "name": "New Cloud Resource Group",
            "cloud_account": fixtures.accounts[1].pk,
            "cloud_resource_type": rg_type.pk,
            "provider_resource_id": "/subscriptions/0002/resourceGroups/new-cloud-resource-group",
            "description": "A new cloud resource group",
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudResourceGroup)],
        }

        cls.bulk_edit_data = {
            "cloud_resource_type": other_rg_type.pk,
            "description": "New description",
        }


class CloudNetworkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudNetwork
    custom_action_required_permissions = {
        "cloud:cloudnetwork_children": ["cloud.view_cloudnetwork"],
        "cloud:cloudnetwork_prefixes": ["cloud.view_cloudnetwork", "ipam.view_prefix"],
        "cloud:cloudnetwork_circuits": ["cloud.view_cloudnetwork", "circuits.view_circuit"],
        "cloud:cloudnetwork_cloud_services": ["cloud.view_cloudnetwork", "cloud.view_cloudservice"],
    }

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("View Network")
        network_type, subnet_type = fixtures.network_types
        status = fixtures.network_statuses[0]
        cloud_services = CloudService.objects.all()[:2]

        cn = CloudNetwork.objects.create(
            name="Deletable Cloud Network 1",
            cloud_resource_type=network_type,
            cloud_account=fixtures.accounts[0],
            status=status,
        )
        CloudNetwork.objects.create(
            name="Deletable Cloud Network 2",
            cloud_resource_type=network_type,
            cloud_account=fixtures.accounts[0],
            status=status,
        )
        CloudNetwork.objects.create(
            name="Deletable Cloud Network 3",
            cloud_resource_type=subnet_type,
            cloud_account=fixtures.accounts[0],
            status=status,
            parent=cn,
        )

        cls.form_data = {
            "name": "New Cloud Network",
            "description": "A new cloud network",
            "provider_resource_id": "arn:aws:ec2:us-east-1:000000000002:subnet/subnet-0002",
            "cloud_resource_type": subnet_type.pk,
            "cloud_account": fixtures.accounts[0].pk,
            "cloud_services": [cloud_services[0].pk, cloud_services[1].pk],
            "parent": cn.pk,
            "status": status.pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudNetwork)],
        }

        cls.bulk_edit_data = {
            "description": "New description",
            "status": fixtures.network_statuses[1].pk,
            "add_cloud_services": [cloud_services[1].pk],
            "remove_cloud_services": [cloud_services[0].pk],
        }


class CloudResourceTypeTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudResourceType
    custom_action_required_permissions = {
        "cloud:cloudresourcetype_services": ["cloud.view_cloudresourcetype", "cloud.view_cloudservice"],
        "cloud:cloudresourcetype_networks": ["cloud.view_cloudresourcetype", "cloud.view_cloudnetwork"],
    }

    @classmethod
    def setUpTestData(cls):
        providers = Manufacturer.objects.all()
        CloudResourceType.objects.create(name="Deletable Cloud Resource Type 1", provider=providers[0])
        CloudResourceType.objects.create(name="Deletable Cloud Resource Type 2", provider=providers[0])
        CloudResourceType.objects.create(name="Deletable Cloud Resource Type 3", provider=providers[0])

        cts = [
            ContentType.objects.get_for_model(CloudNetwork),
        ]

        cls.form_data = {
            "name": "New Cloud Resource Type",
            "provider": providers[1].pk,
            "description": "A new cloud resource type",
            "content_types": [cts[0].id],
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudResourceType)],
        }

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "content_types": [cts[0].id],
            "description": "New description",
        }


class CloudServiceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudService
    custom_action_required_permissions = {
        "cloud:cloudservice_cloud_networks": ["cloud.view_cloudservice", "cloud.view_cloudnetwork"],
    }

    @classmethod
    def setUpTestData(cls):
        fixtures = create_cloud_fixtures("View Service")
        service_type, other_service_type = fixtures.service_types
        status = fixtures.service_statuses[0]
        cloud_networks = CloudNetwork.objects.all()
        cloud_services = (
            CloudService.objects.create(
                name="Deletable Cloud Service 1", cloud_resource_type=service_type, status=status
            ),
            CloudService.objects.create(
                name="Deletable Cloud Service 2", cloud_resource_type=other_service_type, status=status
            ),
            CloudService.objects.create(
                name="Deletable Cloud Service 3",
                cloud_resource_type=service_type,
                cloud_account=fixtures.accounts[0],
                status=status,
            ),
        )
        cloud_services[0].cloud_networks.set([cloud_networks[0]])
        cloud_services[1].cloud_networks.set([cloud_networks[1]])
        cloud_services[2].cloud_networks.set([cloud_networks[2]])

        cls.form_data = {
            "name": "New Cloud Service",
            "description": "It is a new one",
            "cloud_networks": [cloud_networks[1].pk],
            "cloud_resource_type": other_service_type.pk,
            "cloud_account": fixtures.accounts[1].pk,
            "status": status.pk,
            "extra_config": '{"role": 1, "status": "greetings"}',
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudService)],
        }

        cls.bulk_edit_data = {
            "description": "testing",
            "status": fixtures.service_statuses[1].pk,
            "add_cloud_networks": [cloud_networks[2].pk],
            "remove_cloud_networks": [cloud_networks[0].pk],
        }
