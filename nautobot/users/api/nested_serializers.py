from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from nautobot.core.api import ContentTypeField, WritableNestedSerializer
from nautobot.users.models import ObjectPermission, Token

__all__ = [
    "NestedGroupSerializer",
    "NestedObjectPermissionSerializer",
    "NestedTokenSerializer",
    "NestedUserSerializer",
]


class NestedGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:group-detail")

    class Meta:
        model = Group
        fields = ["id", "url", "name"]


class NestedUserSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:user-detail")

    class Meta:
        model = get_user_model()
        fields = ["id", "url", "username"]


class NestedTokenSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:token-detail")

    class Meta:
        model = Token
        fields = ["id", "url", "display", "key", "write_enabled"]


class NestedObjectPermissionSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:objectpermission-detail")
    object_types = ContentTypeField(queryset=ContentType.objects.all(), many=True)
    groups = serializers.SerializerMethodField(read_only=True)
    users = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ObjectPermission
        fields = [
            "id",
            "url",
            "name",
            "enabled",
            "object_types",
            "groups",
            "users",
            "actions",
        ]

    def get_groups(self, obj):
        return [g.name for g in obj.groups.all()]

    def get_users(self, obj):
        return [u.username for u in obj.users.all()]
