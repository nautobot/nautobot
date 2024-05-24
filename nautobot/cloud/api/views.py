from nautobot.cloud import filters
from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.extras.api.views import NautobotModelViewSet

from . import serializers

#
# Cloud Account
#


class CloudAccountViewSet(NautobotModelViewSet):
    queryset = CloudAccount.objects.select_related("provider", "secrets_group")
    serializer_class = serializers.CloudAccountSerializer
    filterset_class = filters.CloudAccountFilterSet


class CloudTypeViewSet(NautobotModelViewSet):
    queryset = CloudType.objects.select_related("provider")
    serializer_class = serializers.CloudTypeSerializer
    filterset_class = filters.CloudTypeFilterSet
