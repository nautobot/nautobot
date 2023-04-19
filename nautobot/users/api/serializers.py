from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from nautobot.core.api import (
    ContentTypeField,
    ValidatedModelSerializer,
)
from nautobot.users.models import ObjectPermission, Token


class UserSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:user-detail")

    class Meta:
        model = get_user_model()
        exclude = ["user_permissions"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        """
        Extract the password from validated data and set it separately to ensure proper hash generation.
        """
        password = validated_data.pop("password")
        user = super().create(validated_data)
        user.set_password(password)
        user.save()

        return user


class GroupSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:group-detail")
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        exclude = ["permissions"]


class TokenSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:token-detail")
    key = serializers.CharField(min_length=40, max_length=40, allow_blank=True, required=False)

    class Meta:
        model = Token
        exclude = ["user"]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if "key" not in data:
            data["key"] = Token.generate_key()
        data["user"] = self.context["request"].user
        return data


class ObjectPermissionSerializer(ValidatedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-api:objectpermission-detail")
    object_types = ContentTypeField(queryset=ContentType.objects.all(), many=True)

    class Meta:
        model = ObjectPermission
        fields = "__all__"
