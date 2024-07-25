from django.contrib.contenttypes.models import ContentType

from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudResourceType, CloudService
from nautobot.core.testing import ViewTestCases
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import SecretsGroup, Tag


class CloudAccountTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudAccount

    @classmethod
    def setUpTestData(cls):
        providers = Manufacturer.objects.all()
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )
        CloudAccount.objects.create(name="Deletable Cloud Account 1", account_number="123456", provider=providers[0])
        CloudAccount.objects.create(name="Deletable Cloud Account 2", account_number="234567", provider=providers[0])
        CloudAccount.objects.create(name="Deletable Cloud Account 3", account_number="345678", provider=providers[0])
        cls.form_data = {
            "name": "New Cloud Account",
            "account_number": "8928371982310",
            "provider": providers[1].pk,
            "secrets_group": secrets_groups[1].pk,
            "description": "A new cloud account",
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudAccount)],
        }

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "secrets_group": secrets_groups[1].pk,
            "description": "New description",
            "comments": "New comments",
        }


class CloudNetworkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudNetwork

    @classmethod
    def setUpTestData(cls):
        cloud_services = CloudService.objects.all()[:2]
        cloud_network_ct = ContentType.objects.get_for_model(CloudNetwork)

        cloud_resource_types = CloudResourceType.objects.get_for_model(CloudNetwork)
        cloud_accounts = CloudAccount.objects.all()
        cloud_resource_type_1 = cloud_resource_types[0]
        cloud_resource_type_2 = cloud_resource_types[1]

        cloud_resource_type_1.content_types.add(cloud_network_ct)
        cloud_resource_type_2.content_types.add(cloud_network_ct)

        cn = CloudNetwork.objects.create(
            name="Deletable Cloud Network 1", cloud_resource_type=cloud_resource_type_1, cloud_account=cloud_accounts[0]
        )
        CloudNetwork.objects.create(
            name="Deletable Cloud Network 2", cloud_resource_type=cloud_resource_type_1, cloud_account=cloud_accounts[0]
        )
        CloudNetwork.objects.create(
            name="Deletable Cloud Network 3",
            cloud_resource_type=cloud_resource_type_1,
            cloud_account=cloud_accounts[0],
            parent=cn,
        )

        cls.form_data = {
            "name": "New Cloud Network",
            "description": "A new cloud network",
            "cloud_resource_type": cloud_resource_type_2.pk,
            "cloud_account": cloud_accounts[1].pk,
            "cloud_services": [cloud_services[0].pk, cloud_services[1].pk],
            "parent": cn.pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudNetwork)],
        }

        cls.bulk_edit_data = {
            "description": "New description",
            "cloud_resource_type": cloud_resource_types[1].pk,
            "cloud_account": cloud_accounts[1].pk,
            "add_cloud_services": [cloud_services[1].pk],
            "remove_cloud_services": [cloud_services[0].pk],
        }


class CloudResourceTypeTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudResourceType

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

    @classmethod
    def setUpTestData(cls):
        cloud_resource_types = CloudResourceType.objects.get_for_model(CloudService)
        cloud_networks = CloudNetwork.objects.all()
        cloud_accounts = CloudAccount.objects.all()
        cloud_services = (
            CloudService.objects.create(name="Deletable Cloud Service 1", cloud_resource_type=cloud_resource_types[0]),
            CloudService.objects.create(name="Deletable Cloud Service 2", cloud_resource_type=cloud_resource_types[1]),
            CloudService.objects.create(
                name="Deletable Cloud Service 3",
                cloud_resource_type=cloud_resource_types[2],
                cloud_account=cloud_accounts[0],
            ),
        )
        cloud_services[0].cloud_networks.set([cloud_networks[0]])
        cloud_services[1].cloud_networks.set([cloud_networks[1]])
        cloud_services[2].cloud_networks.set([cloud_networks[2]])

        cls.form_data = {
            "name": "New Cloud Service",
            "description": "It is a new one",
            "cloud_networks": [cloud_networks[1].pk],
            "cloud_resource_type": cloud_resource_types[1].pk,
            "cloud_account": cloud_accounts[1].pk,
            "extra_config": '{"role": 1, "status": "greetings"}',
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudService)],
        }

        cls.bulk_edit_data = {
            "cloud_account": cloud_accounts[2].pk,
            "description": "testing",
            "add_cloud_networks": [cloud_networks[2].pk],
            "remove_cloud_networks": [cloud_networks[0].pk],
        }
