import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from nautobot.core.api.fields import ContentTypeField
from nautobot.core.api.serializers import WritableNestedSerializer
from nautobot.core.models.dynamic_groups import DynamicGroup, DynamicGroupMembership

__all__ = (
    "NestedDynamicGroupSerializer",
    "NestedDynamicGroupMembershipSerializer",
)


logger = logging.getLogger(__name__)


class NestedDynamicGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroup-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.all(),
    )

    class Meta:
        model = DynamicGroup
        fields = ["id", "url", "name", "slug", "content_type"]


class NestedDynamicGroupMembershipSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:dynamicgroupmembership-detail")
    group = NestedDynamicGroupSerializer()
    parent_group = NestedDynamicGroupSerializer()

    class Meta:
        model = DynamicGroupMembership
        fields = ["id", "url", "group", "parent_group", "operator", "weight"]
