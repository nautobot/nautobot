from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

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
        queryset=ContentType.objects.filter(Q(app_label="cloud", model="cloudaccount")),
        many=True,
    )

    class Meta:
        model = CloudType
        fields = "__all__"
