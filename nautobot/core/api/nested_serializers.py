from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.extras import models


class NestedRoleSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="extras-api:role-detail")

    class Meta:
        model = models.Role
        fields = ["id", "url", "name", "slug"]
