from nautobot.cloud import models
from nautobot.core.api import NautobotModelSerializer, ValidatedModelSerializer
from nautobot.core.api.fields import ContentTypeField
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)
from nautobot.extras.utils import CloudTypeModelsQuery

#
# Cloud Account
#


class CloudAccountSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudAccount
        fields = "__all__"


class CloudTypeSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    content_types = ContentTypeField(
        queryset=CloudTypeModelsQuery().as_queryset(),
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
