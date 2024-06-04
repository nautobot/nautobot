from nautobot.cloud.models import CloudAccount
from nautobot.core.testing import ViewTestCases
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import SecretsGroup, Tag


class CircuitTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CloudAccount

    @classmethod
    def setUpTestData(cls):
        providers = Manufacturer.objects.all()
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )
        cls.form_data = {
            "name": "New Cloud Account",
            "account_number": "8928371982310",
            "cid": "Circuit X",
            "provider": providers[1].pk,
            "secrets_group": secrets_groups[1].pk,
            "description": "A new circuit",
            "tags": [t.pk for t in Tag.objects.get_for_model(CloudAccount)],
        }

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "secrets_group": secrets_groups[1].pk,
            "description": "New description",
            "comments": "New comments",
        }
