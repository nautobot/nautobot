from nautobot.cloud.models import CloudAccount
from nautobot.core.api import NautobotModelSerializer

#
# Cloud Account
#


class CloudAccountSerializer(NautobotModelSerializer):
    class Meta:
        model = CloudAccount
        fields = "__all__"
