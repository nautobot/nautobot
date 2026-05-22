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
    key = serializers.CharField(min_length=40, max_length=40, allow_blank=True, required=False)

    class Meta:
        model = Token
        exclude = ["user"]

    def to_internal_value(self, data):
        # Capture raw user input before super() strips it (Meta.exclude removes "user").
        raw_user_input = data.get("user") if isinstance(data, dict) else None

        validated = super().to_internal_value(data)

        if "key" not in validated and not self.instance:
            validated["key"] = Token.generate_key()

        request_user = self.context["request"].user

        # Mirror TokenUIViewSet.form_save: staff/superusers may explicitly assign ownership;
        # non-staff users are always restricted to themselves regardless of input.
        if request_user.is_staff or request_user.is_superuser:
            if raw_user_input:
                User = get_user_model()
                try:
                    validated["user"] = User.objects.get(pk=raw_user_input)
                except (User.DoesNotExist, ValueError, TypeError) as exc:
                    raise ValidationError({"user": f"User {raw_user_input!r} does not exist."}) from exc
            elif not self.instance:
                validated["user"] = request_user
            # else: editing without an explicit user= → preserve existing instance.user
        else:
            validated["user"] = request_user

        return validated


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
