import django_filters

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
from nautobot.ipam.models import Prefix


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


class CloudTypeFilterSet(NautobotFilterSet):
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
    content_types = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("cloud_types").get_choices)

    class Meta:
        model = models.CloudType
        fields = ["id", "name", "description", "tags"]


class CloudNetworkFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    cloud_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudType.objects.all(),
        label="Cloud type (name or ID)",
    )
    cloud_account = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
        label="Cloud account (name or ID)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
        label="Parent cloud network (name or ID)",
    )

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
    # Prefix doesn't have an appropriate natural key for NaturalKeyOrPKMultipleChoiceFilter
    prefix = django_filters.ModelMultipleChoiceFilter(queryset=Prefix.objects.all())

    class Meta:
        model = models.CloudNetworkPrefixAssignment
        fields = ["id"]


class CloudServiceFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "cloud_account__name": "icontains",
            "cloud_account__description": "icontains",
            "cloud_network__name": "icontains",
            "cloud_network__description": "icontains",
            "cloud_type__name": "icontains",
            "cloud_type__description": "icontains",
        }
    )
    cloud_account = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudAccount.objects.all(),
        label="Cloud account (name or ID)",
    )
    cloud_network = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudNetwork.objects.all(),
        label="Cloud network (name or ID)",
    )
    cloud_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CloudType.objects.all(),
        label="Cloud type (name or ID)",
    )

    class Meta:
        model = models.CloudService
        fields = ["id", "name", "cloud_account", "cloud_network", "cloud_type", "tags"]
