from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.cloud import models
from nautobot.core.api import NautobotModelSerializer, ValidatedModelSerializer
from nautobot.core.api.fields import ContentTypeField
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)

#
# Cloud Account
#


class CloudAccountSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudAccount
        fields = "__all__"


class CloudTypeSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(Q(app_label="cloud", model="cloudnetwork")),
        many=True,
    )

    class Meta:
        model = models.CloudType
        fields = "__all__"


class CloudNetworkSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudNetwork
        fields = "__all__"


class CloudNetworkPrefixAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.CloudNetworkPrefixAssignment
        fields = "__all__"
