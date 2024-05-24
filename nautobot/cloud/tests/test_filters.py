from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.cloud.filters import CloudAccountFilterSet, CloudTypeFilterSet
from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.core.testing import FilterTestCases
from nautobot.dcim.models.devices import Device
from nautobot.dcim.models.racks import RackGroup
from nautobot.extras.models import SecretsGroup


class CloudAccountTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = CloudAccount.objects.all()
    filterset = CloudAccountFilterSet
    generic_filter_tests = [
        ("account_number",),
        ("description",),
        ("provider", "provider__id"),
        ("provider", "provider__name"),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
            SecretsGroup.objects.create(name="Secrets Group 4"),
        )
        cls.cloud_accounts = list(CloudAccount.objects.all()[:4])
        for i, _ in enumerate(cls.cloud_accounts):
            cls.cloud_accounts[i].secrets_group = secrets_groups[i]
            cls.cloud_accounts[i].validated_save()


class CloudTypeTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = CloudType.objects.all()
    filterset = CloudTypeFilterSet
    generic_filter_tests = [
        ("description",),
        ("name",),
        ("provider", "provider__id"),
        ("provider", "provider__name"),
    ]

    def test_content_types(self):
        cts = [
            ContentType.objects.get_for_model(Device),
            ContentType.objects.get_for_model(RackGroup),
        ]
        for idx, cloud_type in enumerate(CloudType.objects.all()[:5]):
            cloud_type.content_types.add(cts[idx % 2])

        params = {"content_types": ["dcim.device", "dcim.rackgroup"]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            CloudType.objects.filter(Q(content_types__in=cts[0])).filter(Q(content_types__in=cts[1])).count(),
        )
