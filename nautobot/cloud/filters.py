import django_filters

from nautobot.cloud import models
from nautobot.core.filters import (
    BaseFilterSet,
    ContentTypeMultipleChoiceFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.dcim.filter_mixins import LocatableModelFilterSetMixin
from nautobot.dcim.models import Manufacturer
from nautobot.extras.filter_mixins import RoleModelFilterSetMixin, StatusModelFilterSetMixin
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import SecretsGroup
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.filter_mixins import PrefixFilter
from nautobot.ipam.models import IPAddress
from nautobot.tenancy.filter_mixins import TenancyModelFilterSetMixin


class CloudAccountFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "account_number": "icontains",
            "provider__name": "icontains",
        },
    )
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="provider",
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
    )
    cloud_account_group = TreeNodeMultipleChoiceFilter(
        queryset=models.CloudAccountGroup.objects.all(),
        to_field_name="name",
        label="Cloud account group, including its descendants (name or ID)",
    )
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = models.CloudAccount
        fields = [
            "account_number",
            "cloud_account_group",
            "description",
            "id",
            "name",
            "provider",
            "secrets_group",
            "tags",
        ]


class CloudAccountGroupFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "cloud_resource_type__name": "icontains",
        },
    )
    parent = TreeNodeMultipleChoiceFilter(
        queryset=models.CloudAccountGroup.objects.all(),
        to_field_name="name",
        label="Parent cloud account group, including its descendants (name or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has children",
    )
    cloud_resource_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceType.objects.all(),
        to_field_name="name",
    )
    cloud_accounts = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
        to_field_name="name",
    )
    has_cloud_accounts = RelatedMembershipBooleanFilter(
        field_name="cloud_accounts",
        label="Has cloud accounts",
    )

    class Meta:
        model = models.CloudAccountGroup
        fields = ["id", "name", "description", "tags"]


class CloudResourceGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "provider_resource_id": "icontains",
            "cloud_account__name": "icontains",
            "cloud_resource_type__name": "icontains",
        },
    )
    cloud_account = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
        to_field_name="name",
    )
    cloud_account_group = TreeNodeMultipleChoiceFilter(
        field_name="cloud_account__cloud_account_group",
        queryset=models.CloudAccountGroup.objects.all(),
        to_field_name="name",
        label="Cloud account group, including its descendants (name or ID)",
    )
    cloud_resource_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceType.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = models.CloudResourceGroup
        fields = ["id", "name", "description", "provider_resource_id", "tags"]


class CloudResourceTypeFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "provider__name": "icontains",
        },
    )
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="provider",
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
    )
    content_types = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("cloud_resource_types").get_choices)

    class Meta:
        model = models.CloudResourceType
        fields = ["id", "name", "description", "tags"]


class CloudNetworkFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
    TenancyModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "provider_resource_id": "icontains",
            "parent__name": "icontains",
            "parent__description": "icontains",
            "cloud_account__name": "icontains",
            "cloud_account__description": "icontains",
            "cloud_resource_type__name": "icontains",
            "cloud_resource_type__description": "icontains",
        },
    )
    cloud_resource_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceType.objects.all(),
    )
    cloud_account = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
    )
    cloud_account_group = TreeNodeMultipleChoiceFilter(
        field_name="cloud_account__cloud_account_group",
        queryset=models.CloudAccountGroup.objects.all(),
        to_field_name="name",
        label="Cloud account group, including its descendants (name or ID)",
    )
    cloud_resource_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceGroup.objects.all(),
        to_field_name="name",
    )
    cloud_services = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudService.objects.all(),
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
        label="Parent cloud network (name or ID)",
    )
    prefixes = PrefixFilter()

    class Meta:
        model = models.CloudNetwork
        fields = ["id", "name", "description", "provider_resource_id", "tags"]


class CloudNetworkPrefixAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "cloud_network__name": "icontains",
            "cloud_network__description": "icontains",
            # TODO: add prefix search, currently implemented as a custom search() method on PrefixFilterSet
        }
    )
    cloud_network = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
    )
    prefix = PrefixFilter()

    class Meta:
        model = models.CloudNetworkPrefixAssignment
        fields = ["id"]


class CloudServiceFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
    TenancyModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "provider_resource_id": "icontains",
            "cloud_account__name": "icontains",
            "cloud_account__description": "icontains",
            "cloud_networks__name": "icontains",
            "cloud_networks__description": "icontains",
            "cloud_resource_type__name": "icontains",
            "cloud_resource_type__description": "icontains",
        }
    )
    cloud_account = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
    )
    cloud_account_group = TreeNodeMultipleChoiceFilter(
        field_name="cloud_account__cloud_account_group",
        queryset=models.CloudAccountGroup.objects.all(),
        to_field_name="name",
        label="Cloud account group, including its descendants (name or ID)",
    )
    cloud_resource_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceGroup.objects.all(),
        to_field_name="name",
    )
    cloud_networks = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
    )
    cloud_resource_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceType.objects.all(),
    )
    ip_addresses = django_filters.ModelMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
        label="IP addresses (ID)",
    )
    has_ip_addresses = RelatedMembershipBooleanFilter(
        field_name="ip_addresses",
        label="Has IP addresses",
    )

    class Meta:
        model = models.CloudService
        fields = [
            "id",
            "name",
            "description",
            "provider_resource_id",
            "cloud_account",
            "cloud_networks",
            "cloud_resource_type",
            "tags",
        ]


class CloudServiceNetworkAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "cloud_network__name": "icontains",
            "cloud_network__description": "icontains",
            "cloud_network__cloud_account__name": "icontains",
            "cloud_network__cloud_account__description": "icontains",
            "cloud_network__cloud_resource_type__name": "icontains",
            "cloud_network__cloud_resource_type__description": "icontains",
            "cloud_service__name": "icontains",
            "cloud_service__description": "icontains",
            "cloud_service__cloud_account__name": "icontains",
            "cloud_service__cloud_account__description": "icontains",
            "cloud_service__cloud_resource_type__name": "icontains",
            "cloud_service__cloud_resource_type__description": "icontains",
        }
    )
    cloud_network = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
    )
    cloud_service = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudService.objects.all(),
    )

    class Meta:
        model = models.CloudServiceNetworkAssignment
        fields = ["id"]


class CloudServiceIPAddressAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "cloud_service__name": "icontains",
            "cloud_service__description": "icontains",
        }
    )
    cloud_service = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudService.objects.all(),
    )
    ip_address = django_filters.ModelMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
    )

    class Meta:
        model = models.CloudServiceIPAddressAssignment
        fields = ["id"]
