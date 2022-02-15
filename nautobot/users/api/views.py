from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.status import HTTP_201_CREATED
from rest_framework.viewsets import ViewSet

from nautobot.core.api.views import ModelViewSet
from nautobot.users import filters
from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.utils import deepmerge
from . import serializers
from . import authentication


class UsersRootView(APIRootView):
    """
    Users API root view
    """

    def get_view_name(self):
        return "Users"


#
# Users and groups
#


class UserViewSet(ModelViewSet):
    queryset = RestrictedQuerySet(model=get_user_model()).prefetch_related("groups").order_by("username")
    serializer_class = serializers.UserSerializer
    filterset_class = filters.UserFilterSet


class GroupViewSet(ModelViewSet):
    queryset = RestrictedQuerySet(model=Group).annotate(user_count=Count("user")).order_by("name")
    serializer_class = serializers.GroupSerializer
    filterset_class = filters.GroupFilterSet


#
# REST API tokens
#


class TokenViewSet(ModelViewSet):
    queryset = RestrictedQuerySet(model=Token).prefetch_related("user")
    serializer_class = serializers.TokenSerializer
    filterset_class = filters.TokenFilterSet

    def get_queryset(self):
        """
        Limit users to their own Tokens.
        """
        queryset = super().get_queryset()
        # Workaround for schema generation (drf_yasg)
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return queryset.filter(user=self.request.user)

    @action(
        detail=False,
        methods=["post"],
        authentication_classes=[authentication.TokenProvisionAuthentication],
        permission_classes=[],
    )
    def provision(self, request):
        """
        Non-authenticated REST API endpoint via which a user may create a Token.
        """
        # Create a new Token for the User
        token = Token.objects.create(user=request.user)
        data = serializers.TokenSerializer(token, context={"request": request}).data
        return Response(data, status=HTTP_201_CREATED)


#
# ObjectPermissions
#


class ObjectPermissionViewSet(ModelViewSet):
    queryset = ObjectPermission.objects.prefetch_related("object_types", "groups", "users")
    serializer_class = serializers.ObjectPermissionSerializer
    filterset_class = filters.ObjectPermissionFilterSet


#
# User preferences
#


class UserConfigViewSet(ViewSet):
    """
    An API endpoint via which a user can update his or her own config data (user preferences), but no one else's.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Return the config_data for the currently authenticated User.
        """
        return Response(request.user.config_data)

    def patch(self, request):
        """
        Update the config_data for the currently authenticated User.
        """
        # TODO: How can we validate this data?
        user = request.user
        user.config_data = deepmerge(user.config_data, request.data)
        user.save()

        return Response(user.config_data)
