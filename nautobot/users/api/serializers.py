from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from nautobot.core.api import (
    ContentTypeField,
    NotesSerializerMixin,
    ValidatedModelSerializer,
)
from nautobot.users.models import ObjectPermission, Token


class UserSerializer(ValidatedModelSerializer):
    class Meta:
        model = get_user_model()
        exclude = ["user_permissions"]
        extra_kwargs = {"password": {"write_only": True, "required": False, "allow_null": True}}

    def validate(self, attrs):
        """Handle omission of a password by setting it to the unusable None value."""
        mock_password = False
        if "password" not in attrs and not self.partial:
            attrs["password"] = make_password(None)
            mock_password = True
        validated_data = super().validate(attrs)
        if mock_password:
            validated_data["password"] = None
        return validated_data

    def create(self, validated_data):
        """
        Extract the password from validated data and set it separately to ensure proper hash generation.
        """
        password = validated_data.pop("password")
        user = super().create(validated_data)
        user.set_password(password)
        user.save()

        return user

    def update(self, instance, validated_data):
        """
        Extract the password from validated data and set it separately to ensure proper hash generation.
        """
        update_password = False
        password = None
        if "password" in validated_data:
            update_password = True
            password = validated_data.pop("password")
        elif not self.partial:
            update_password = True
        super().update(instance, validated_data)
        if update_password:
            instance.set_password(password)
            instance.save()
        return instance


class GroupSerializer(ValidatedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="users-api:group-detail")
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        exclude = ["permissions"]


class TokenSerializer(ValidatedModelSerializer, NotesSerializerMixin):
    key = serializers.CharField(min_length=40, max_length=40, allow_blank=True, required=False, write_only=True)

    class Meta:
        model = Token
        fields = "__all__"
        extra_kwargs = {
            "user": {"required": False},
        }

    def validate_user(self, value):
        """Non-staff users cannot create tokens for other users; ownership is immutable after creation."""
        if self.instance is not None and value != self.instance.user:
            raise serializers.ValidationError("Token ownership cannot be changed after creation.")
        request_user = self.context["request"].user
        if not request_user.is_staff and value != request_user:
            raise serializers.ValidationError("Non-staff users cannot create tokens for other users.")
        return value

    def validate_key(self, value):
        """The key is immutable after creation."""
        if self.instance is not None and value and value != self.instance.key:
            raise serializers.ValidationError("Token key cannot be changed after creation.")
        return value

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)

        # Default user/key on creation when not provided. On edit, leave both fields untouched
        # if they weren't supplied so existing values are preserved.
        if not self.instance:
            if "user" not in validated:
                validated["user"] = self.context["request"].user
            if "key" not in validated:
                validated["key"] = Token.generate_key()

        return validated

    def to_representation(self, instance):
        """Reveal the raw key only on creation; strip it from retrieve/list/update responses.

        The `key` field is declared write_only so `super()` always omits it. We add it back to the
        response on creation actions so callers can capture the generated value once.
        """
        data = super().to_representation(instance)
        view = self.context.get("view")
        if view and getattr(view, "action", None) in {"create", "bulk_create"} and instance.key:
            data["key"] = instance.key
        return data


class ObjectPermissionSerializer(ValidatedModelSerializer):
    object_types = ContentTypeField(queryset=ContentType.objects.all(), many=True)

    class Meta:
        model = ObjectPermission
        fields = "__all__"


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        user = authenticate(
            self.context["request"],
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user:
            raise ValidationError("Invalid login credentials.")
        return {"user": user}
