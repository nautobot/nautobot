from django.contrib.contenttypes.models import ContentType

from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudService, CloudType
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


class CloudTypeTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudType

    @classmethod
    def setUpTestData(cls):
        providers = Manufacturer.objects.all()
        CloudType.objects.create(name="Deletable Cloud Type 1", provider=providers[0])
        CloudType.objects.create(name="Deletable Cloud Type 2", provider=providers[0])
        CloudType.objects.create(name="Deletable Cloud Type 3", provider=providers[0])

        cts = [
            ContentType.objects.get_for_model(CloudNetwork),
        ]

        cls.form_data = {
            "name": "New Cloud Type",
            "provider": providers[1].pk,
            "description": "A new cloud type",
            "content_types": [cts[0].id],
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudType)],
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
        cloud_types = CloudType.objects.all()
        cloud_networks = CloudNetwork.objects.all()
        cloud_accounts = CloudNetwork.objects.all()
        CloudService.objects.create(name="Deletable Cloud Service 1", cloud_type=cloud_types[0], cloud_network=cloud_networks[0])
        CloudService.objects.create(name="Deletable Cloud Service 2", cloud_type=cloud_types[0], cloud_network=cloud_networks[0])
        CloudService.objects.create(name="Deletable Cloud Service 3", cloud_type=cloud_types[0], cloud_network=cloud_networks[0])


        cls.form_data = {
            "name": "New Cloud Service",
            "cloud_type": cloud_types[1].pk,
            "cloud_network": cloud_networks[1].pk,
            "cloud_account": cloud_accounts[1].pk,
            "extra_config": {},
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudService)],
        }

        cls.bulk_edit_data = {
            "cloud_network": cloud_networks[2].pk,
            "cloud_account": cloud_accounts[2].pk,
        }
