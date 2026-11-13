from django.contrib.contenttypes.models import ContentType

from nautobot.cloud import models
from nautobot.core.api import NautobotModelSerializer, TreeModelSerializerMixin, ValidatedModelSerializer
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


class CloudAccountGroupSerializer(TaggedModelSerializerMixin, TreeModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudAccountGroup
        fields = "__all__"
        # The (parent, name) uniqueness is enforced by the model's full_clean(), since parent is optional.
        validators = []


class CloudResourceGroupSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudResourceGroup
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
        # The scoped name uniqueness is enforced by the model's full_clean(), since some scope fields are optional.
        validators = []


class CloudNetworkPrefixAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.CloudNetworkPrefixAssignment
        fields = "__all__"


class CloudServiceSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.CloudService
        fields = "__all__"
        # The scoped name uniqueness is enforced by the model's full_clean(), since some scope fields are optional.
        validators = []


class CloudServiceNetworkAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.CloudServiceNetworkAssignment
        fields = "__all__"


class CloudServiceIPAddressAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.CloudServiceIPAddressAssignment
        fields = "__all__"
