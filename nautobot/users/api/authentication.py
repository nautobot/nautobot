from django.contrib.auth import authenticate
from rest_framework import authentication, exceptions

from . import serializers


class TokenProvisionAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        serializer = serializers.TokenProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Authenticate the user account based on the provided credentials
        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise exceptions.AuthenticationFailed("Invalid username/password")

        return (user, None)
