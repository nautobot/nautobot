from nautobot.cloud import filters
from nautobot.cloud.models import CloudAccount
from nautobot.extras.api.views import NautobotModelViewSet

from . import serializers

#
# Cloud Account
#


class CloudAccountViewSet(NautobotModelViewSet):
    queryset = CloudAccount.objects.select_related("provider", "secrets_group")
    serializer_class = serializers.CloudAccountSerializer
    filterset_class = filters.CloudAccountFilterSet
