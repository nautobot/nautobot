from django.contrib.auth import get_user_model
from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer

__all__ = [
    "NestedUserSerializer",
]


class NestedUserSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:user-detail")

    class Meta:
        model = get_user_model()
        fields = ["id", "url", "username"]
