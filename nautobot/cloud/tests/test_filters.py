from django.contrib.contenttypes.models import ContentType

from nautobot.cloud import filters, models
from nautobot.core.testing import FilterTestCases
from nautobot.extras.models import SecretsGroup


class CloudAccountTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = models.CloudAccount.objects.all()
    filterset = filters.CloudAccountFilterSet
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
        cls.cloud_accounts = list(models.CloudAccount.objects.all()[:4])
        for i in range(4):
            cls.cloud_accounts[i].secrets_group = secrets_groups[i]
            cls.cloud_accounts[i].validated_save()


class CloudTypeTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = models.CloudType.objects.all()
    filterset = filters.CloudTypeFilterSet
    generic_filter_tests = [
        ("description",),
        ("name",),
        ("provider", "provider__id"),
        ("provider", "provider__name"),
    ]

    def test_content_types(self):
        cn_ct = ContentType.objects.get_for_model(models.CloudNetwork)
        params = {"content_types": ["cloud.cloudnetwork"]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            models.CloudType.objects.filter(content_types=cn_ct),
        )


class CloudNetworkTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = models.CloudNetwork.objects.all()
    filterset = filters.CloudNetworkFilterSet
    generic_filter_tests = [
        ("cloud_account", "cloud_account__id"),
        ("cloud_account", "cloud_account__name"),
        ("cloud_type", "cloud_type__id"),
        ("cloud_type", "cloud_type__name"),
        ("description",),
        ("name",),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
    ]


class CloudNetworkPrefixAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudNetworkPrefixAssignment.objects.all()
    filterset = filters.CloudNetworkPrefixAssignmentFilterSet
    generic_filter_tests = [
        ("cloud_network", "cloud_network__id"),
        ("cloud_network", "cloud_network__name"),
        ("prefix", "prefix__id"),
    ]
