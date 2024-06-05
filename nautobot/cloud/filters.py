from nautobot.cloud import models
from nautobot.core.filters import (
    ContentTypeMultipleChoiceFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
)
from nautobot.dcim.models import Manufacturer
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import SecretsGroup


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
    content_types = ContentTypeMultipleChoiceFilter(choices=(("cloud", "cloudaccount"),))

    class Meta:
        model = models.CloudType
        fields = ["id", "name", "description"]


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
        fields = ["id", "name", "description"]
