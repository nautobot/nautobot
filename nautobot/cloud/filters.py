from nautobot.cloud import models
from nautobot.core.filters import (
    BaseFilterSet,
    ContentTypeMultipleChoiceFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
)
from nautobot.dcim.models import Manufacturer
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import SecretsGroup
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.filters import PrefixFilter


class CloudAccountFilterSet(NautobotFilterSet):
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
        label="Provider (name or ID)",
    )
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
        label="Secrets group (name or ID)",
    )

    class Meta:
        model = models.CloudAccount
        fields = [
            "account_number",
            "description",
            "id",
            "name",
            "provider",
            "secrets_group",
            "tags",
        ]


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
        label="Provider (name or ID)",
    )
    content_types = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("cloud_resource_types").get_choices)

    class Meta:
        model = models.CloudResourceType
        fields = ["id", "name", "description", "tags"]


class CloudNetworkFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
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
        label="Cloud resource type (name or ID)",
    )
    cloud_account = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
        label="Cloud account (name or ID)",
    )
    cloud_services = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudService.objects.all(),
        label="Cloud services (name or ID)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
        label="Parent cloud network (name or ID)",
    )
    prefixes = PrefixFilter()

    class Meta:
        model = models.CloudNetwork
        fields = ["id", "name", "description", "tags"]


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
        label="Cloud network (name or ID)",
    )
    prefix = PrefixFilter()

    class Meta:
        model = models.CloudNetworkPrefixAssignment
        fields = ["id"]


class CloudServiceFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
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
        label="Cloud account (name or ID)",
    )
    cloud_networks = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
        label="Cloud networks (name or ID)",
    )
    cloud_resource_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudResourceType.objects.all(),
        label="Cloud resource type (name or ID)",
    )

    class Meta:
        model = models.CloudService
        fields = ["id", "name", "description", "cloud_account", "cloud_networks", "cloud_resource_type", "tags"]


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
        label="Cloud network (name or ID)",
    )
    cloud_service = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudService.objects.all(),
        label="Cloud service (name or ID)",
    )

    class Meta:
        model = models.CloudServiceNetworkAssignment
        fields = ["id"]
