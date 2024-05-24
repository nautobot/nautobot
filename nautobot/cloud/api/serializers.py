from django.contrib.contenttypes.models import ContentType

from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.core.api import NautobotModelSerializer
from nautobot.core.api.fields import ContentTypeField

#
# Cloud Account
#


class CloudAccountSerializer(NautobotModelSerializer):
    class Meta:
        model = CloudAccount
        fields = "__all__"


class CloudTypeSerializer(NautobotModelSerializer):
    content_types = ContentTypeField(
        queryset=ContentType.objects.all(),
        many=True,
    )

    class Meta:
        model = CloudType
        fields = "__all__"
