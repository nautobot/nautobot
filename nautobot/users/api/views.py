from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import ViewSet

from nautobot.core.api.views import ModelViewSet
from nautobot.users import filters
from nautobot.users.models import ObjectPermission
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.utils import deepmerge
from . import serializers


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
