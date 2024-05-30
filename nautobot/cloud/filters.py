from nautobot.core.filters import (
    ContentTypeMultipleChoiceFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
)
from nautobot.dcim.models import Manufacturer
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import SecretsGroup

from .models import CloudAccount, CloudType


class CloudAccountFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
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
        model = CloudAccount
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
        model = CloudType
        fields = ["id", "name", "description"]
