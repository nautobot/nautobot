from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from nautobot.core.api.fields import ContentTypeField
from nautobot.core.api.nested_serializers import NestedDynamicGroupSerializer, NestedDynamicGroupMembershipSerializer
from nautobot.core.api.serializers import ValidatedModelSerializer
from nautobot.core.models.dynamic_groups import DynamicGroup, DynamicGroupMembership
from nautobot.extras.api.serializers import NautobotModelSerializer
from nautobot.extras.utils import FeatureQuery

#
# Dynamic Groups
#


class DynamicGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="core-api:dynamicgroup-detail")
    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
    )
    # Read-only because m2m is hard. Easier to just create # `DynamicGroupMemberships` explicitly
    # using their own endpoint at /api/core/dynamic-group-memberships/.
    children = NestedDynamicGroupMembershipSerializer(source="dynamic_group_memberships", read_only=True, many=True)

    class Meta:
        model = DynamicGroup
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "content_type",
            "filter",
            "children",
        ]
        extra_kwargs = {"filter": {"read_only": False}}


class DynamicGroupMembershipSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="core-api:dynamicgroupmembership-detail")
    group = NestedDynamicGroupSerializer()
    parent_group = NestedDynamicGroupSerializer()

    class Meta:
        model = DynamicGroupMembership
        fields = ["url", "group", "parent_group", "operator", "weight"]
