from django.contrib.contenttypes.models import ContentType

from nautobot.cloud import filters, models
from nautobot.core.testing import FilterTestCases
from nautobot.dcim.models import Location
from nautobot.extras.models import SecretsGroup


class TreeFilterTestMixin:
    """Assert that a tree-aware filter also matches objects related to descendants of the given tree nodes."""

    def assert_tree_filter(self, filter_name, lookup, nodes):
        expected_nodes = []
        for node in nodes:
            expected_nodes += node.descendants(include_self=True)
        expected = self.queryset.filter(**{f"{lookup}__in": expected_nodes}).distinct()
        for values in ([node.pk for node in nodes], [node.name for node in nodes]):
            self.assertQuerySetEqualAndNotEmpty(
                self.filterset({filter_name: values}, self.queryset).qs, expected, ordered=False
            )


class CloudAccountTestCase(
    TreeFilterTestMixin, FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin
):
    queryset = models.CloudAccount.objects.all()
    filterset = filters.CloudAccountFilterSet
    tenancy_related_name = "cloud_accounts"
    generic_filter_tests = [
        ("account_number",),
        ("description",),
        ("name",),
        ("provider", "provider__id"),
        ("provider", "provider__name"),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
        ("status", "status__id"),
        ("status", "status__name"),
    ]

    def test_cloud_account_group(self):
        groups = list(models.CloudAccountGroup.objects.filter(cloud_accounts__isnull=False).distinct()[:2])
        self.assert_tree_filter("cloud_account_group", "cloud_account_group", groups)

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
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            models.CloudResourceType.objects.filter(content_types=cn_ct),
        )


class CloudNetworkTestCase(
    TreeFilterTestMixin, FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin
):
    queryset = models.CloudNetwork.objects.all()
    filterset = filters.CloudNetworkFilterSet
    tenancy_related_name = "cloud_networks"
    generic_filter_tests = [
        ("cloud_account", "cloud_account__id"),
        ("cloud_account", "cloud_account__name"),
        ("cloud_resource_group", "cloud_resource_group__id"),
        ("cloud_resource_group", "cloud_resource_group__name"),
        ("cloud_services", "cloud_services__id"),
        ("cloud_services", "cloud_services__name"),
        ("cloud_resource_type", "cloud_resource_type__id"),
        ("cloud_resource_type", "cloud_resource_type__name"),
        ("description",),
        ("name",),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
        ("prefixes", "prefixes__id"),
        ("provider_resource_id",),
        ("role", "role__id"),
        ("role", "role__name"),
        ("status", "status__id"),
        ("status", "status__name"),
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

    def test_cloud_account_group(self):
        groups = list(
            models.CloudAccountGroup.objects.filter(cloud_accounts__cloud_networks__isnull=False).distinct()[:2]
        )
        self.assert_tree_filter("cloud_account_group", "cloud_account__cloud_account_group", groups)

    def test_location(self):
        locations = list(Location.objects.filter(cloud_networks__isnull=False).distinct()[:2])
        self.assert_tree_filter("location", "location", locations)

    def test_prefixes_filter_by_string(self):
        """Test filtering by prefix strings as an alternative to pk."""
        prefix = self.queryset.filter(prefixes__isnull=False).first().prefixes.first()
        params = {"prefixes": [prefix.prefix]}
        self.assertQuerySetEqualAndNotEmpty(
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
        self.assertQuerySetEqualAndNotEmpty(
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


class CloudServiceTestCase(
    TreeFilterTestMixin, FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin
):
    queryset = models.CloudService.objects.all()
    filterset = filters.CloudServiceFilterSet
    tenancy_related_name = "cloud_services"
    generic_filter_tests = [
        ("cloud_account", "cloud_account__id"),
        ("cloud_account", "cloud_account__name"),
        ("cloud_resource_group", "cloud_resource_group__id"),
        ("cloud_resource_group", "cloud_resource_group__name"),
        ("cloud_networks", "cloud_networks__id"),
        ("cloud_networks", "cloud_networks__name"),
        ("cloud_resource_type", "cloud_resource_type__id"),
        ("cloud_resource_type", "cloud_resource_type__name"),
        ("description",),
        ("ip_addresses", "ip_addresses__id"),
        ("name",),
        ("provider_resource_id",),
        ("role", "role__id"),
        ("role", "role__name"),
        ("status", "status__id"),
        ("status", "status__name"),
    ]

    def test_cloud_account_group(self):
        groups = list(
            models.CloudAccountGroup.objects.filter(cloud_accounts__cloud_services__isnull=False).distinct()[:2]
        )
        self.assert_tree_filter("cloud_account_group", "cloud_account__cloud_account_group", groups)

    def test_location(self):
        locations = list(Location.objects.filter(cloud_services__isnull=False).distinct()[:2])
        self.assert_tree_filter("location", "location", locations)


class CloudAccountGroupTestCase(TreeFilterTestMixin, FilterTestCases.FilterTestCase):
    queryset = models.CloudAccountGroup.objects.all()
    filterset = filters.CloudAccountGroupFilterSet
    generic_filter_tests = [
        ("cloud_accounts", "cloud_accounts__id"),
        ("cloud_accounts", "cloud_accounts__name"),
        ("cloud_resource_type", "cloud_resource_type__id"),
        ("cloud_resource_type", "cloud_resource_type__name"),
        ("description",),
        ("name",),
    ]

    @classmethod
    def setUpTestData(cls):
        groups = list(models.CloudAccountGroup.objects.all()[:3])
        for group, account in zip(groups, models.CloudAccount.objects.all()[:3]):
            account.cloud_account_group = group
            account.save()

    def test_parent(self):
        parents = list(models.CloudAccountGroup.objects.filter(children__isnull=False).distinct()[:2])
        self.assert_tree_filter("parent", "parent", parents)


class CloudResourceGroupTestCase(TreeFilterTestMixin, FilterTestCases.FilterTestCase):
    queryset = models.CloudResourceGroup.objects.all()
    filterset = filters.CloudResourceGroupFilterSet
    generic_filter_tests = [
        ("cloud_account", "cloud_account__id"),
        ("cloud_account", "cloud_account__name"),
        ("cloud_resource_type", "cloud_resource_type__id"),
        ("cloud_resource_type", "cloud_resource_type__name"),
        ("description",),
        ("name",),
        ("provider_resource_id",),
    ]

    def test_location(self):
        locations = list(Location.objects.filter(cloud_resource_groups__isnull=False).distinct()[:2])
        self.assert_tree_filter("location", "location", locations)


class CloudServiceIPAddressAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.CloudServiceIPAddressAssignment.objects.all()
    filterset = filters.CloudServiceIPAddressAssignmentFilterSet
    generic_filter_tests = [
        ("cloud_service", "cloud_service__id"),
        ("cloud_service", "cloud_service__name"),
        ("ip_address", "ip_address__id"),
    ]
