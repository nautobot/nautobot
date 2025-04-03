from django.contrib.contenttypes.models import ContentType

from nautobot.cloud import filters, models
from nautobot.core.testing import FilterTestCases
from nautobot.extras.models import SecretsGroup


class CloudAccountTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudAccount.objects.all()
    filterset = filters.CloudAccountFilterSet
    generic_filter_tests = [
        ("account_number",),
        ("description",),
        ("name",),
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


class CloudResourceTypeTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudResourceType.objects.all()
    filterset = filters.CloudResourceTypeFilterSet
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
            models.CloudResourceType.objects.filter(content_types=cn_ct),
        )


class CloudNetworkTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudNetwork.objects.all()
    filterset = filters.CloudNetworkFilterSet
    generic_filter_tests = [
        ("cloud_account", "cloud_account__id"),
        ("cloud_account", "cloud_account__name"),
        ("cloud_services", "cloud_services__id"),
        ("cloud_services", "cloud_services__name"),
        ("cloud_resource_type", "cloud_resource_type__id"),
        ("cloud_resource_type", "cloud_resource_type__name"),
        ("description",),
        ("name",),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
        ("prefixes", "prefixes__id"),
    ]
    exclude_q_filter_predicates = [
        "parent__name",
        "parent__description",
    ]

    def _get_relevant_filterset_queryset(self, queryset, *filter_params):
        queryset = super()._get_relevant_filterset_queryset(queryset, *filter_params)
        if "name" in filter_params or "description" in filter_params:
            # Only select an instance with no children as otherwise the search will also match the children,
            # due to `parent__name` and `parent__description` also being search parameters
            queryset = queryset.filter(children__isnull=True)
        return queryset

    def test_prefixes_filter_by_string(self):
        """Test filtering by prefix strings as an alternative to pk."""
        prefix = self.queryset.filter(prefixes__isnull=False).first().prefixes.first()
        params = {"prefixes": [prefix.prefix]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(prefixes__network=prefix.network, prefixes__prefix_length=prefix.prefix_length),
            ordered=False,
        )


class CloudNetworkPrefixAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudNetworkPrefixAssignment.objects.all()
    filterset = filters.CloudNetworkPrefixAssignmentFilterSet
    generic_filter_tests = [
        ("cloud_network", "cloud_network__id"),
        ("cloud_network", "cloud_network__name"),
        ("prefix", "prefix__id"),
    ]

    def test_prefix_filter_by_string(self):
        """Test filtering by prefix strings as an alternative to pk."""
        prefix = self.queryset.first().prefix
        params = {"prefix": [prefix.prefix]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(prefix__network=prefix.network, prefix__prefix_length=prefix.prefix_length),
            ordered=False,
        )


class CloudServiceNetworkAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudServiceNetworkAssignment.objects.all()
    filterset = filters.CloudServiceNetworkAssignmentFilterSet
    generic_filter_tests = [
        ("cloud_network", "cloud_network__id"),
        ("cloud_network", "cloud_network__name"),
        ("cloud_service", "cloud_service__id"),
        ("cloud_service", "cloud_service__name"),
    ]
    exclude_q_filter_predicates = [
        "cloud_network__cloud_account__name",
        "cloud_network__cloud_account__description",
        "cloud_network__cloud_resource_type__name",
        "cloud_network__cloud_resource_type__description",
        "cloud_service__cloud_account__name",
        "cloud_service__cloud_account__description",
        "cloud_service__cloud_resource_type__name",
        "cloud_service__cloud_resource_type__description",
    ]


class CloudServiceTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudService.objects.all()
    filterset = filters.CloudServiceFilterSet
    generic_filter_tests = [
        ("cloud_account", "cloud_account__id"),
        ("cloud_account", "cloud_account__name"),
        ("cloud_networks", "cloud_networks__id"),
        ("cloud_networks", "cloud_networks__name"),
        ("cloud_resource_type", "cloud_resource_type__id"),
        ("cloud_resource_type", "cloud_resource_type__name"),
        ("description",),
        ("name",),
    ]
