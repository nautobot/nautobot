from django.contrib.contenttypes.models import ContentType

from nautobot.cloud import models
from nautobot.core.api import NautobotModelSerializer, ValidatedModelSerializer
from nautobot.core.api.fields import ContentTypeField
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)
from nautobot.extras.utils import FeatureQuery

#
# Cloud Account
#


class CloudAccountSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudAccount
        fields = "__all__"


class CloudResourceTypeSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("cloud_resource_types").get_query()),
        many=True,
    )

    class Meta:
        model = models.CloudResourceType
        fields = "__all__"


class CloudNetworkSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudNetwork
        fields = "__all__"


class CloudNetworkPrefixAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.CloudNetworkPrefixAssignment
        fields = "__all__"


class CloudServiceSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudService
        fields = "__all__"


class CloudServiceNetworkAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.CloudServiceNetworkAssignment
        fields = "__all__"
