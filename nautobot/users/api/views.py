from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.db.models import Count
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from nautobot.core.api.serializers import BulkOperationIntegerIDSerializer
from nautobot.core.api.views import ModelViewSet
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.utils.data import deepmerge
from nautobot.users import filters
from nautobot.users.models import ObjectPermission, Token

from . import serializers

#
# Users and groups
#


class UserViewSet(ModelViewSet):
    queryset = RestrictedQuerySet(model=get_user_model()).order_by("username")
    serializer_class = serializers.UserSerializer
    filterset_class = filters.UserFilterSet


@extend_schema_view(
    bulk_destroy=extend_schema(request=BulkOperationIntegerIDSerializer(many=True)),
)
class GroupViewSet(ModelViewSet):
    queryset = RestrictedQuerySet(model=Group).annotate(user_count=Count("user")).order_by("name")
    serializer_class = serializers.GroupSerializer
    bulk_operation_serializer_class = BulkOperationIntegerIDSerializer
    filterset_class = filters.GroupFilterSet


#
# REST API tokens
#


class TokenViewSet(ModelViewSet):
    queryset = RestrictedQuerySet(model=Token).select_related("user")  # pylint: disable=not-callable  # no idea why?
    serializer_class = serializers.TokenSerializer
    filterset_class = filters.TokenFilterSet

    @property
    def authentication_classes(self):
        """Inherit default authentication_classes and basic authentication."""
        classes = super().authentication_classes
        return [*classes, BasicAuthentication]

    def get_queryset(self):
        """
        Limit users to their own Tokens.
        """
        queryset = super().get_queryset()
        if not isinstance(self.request.user, AnonymousUser):
            return queryset.filter(user=self.request.user)
        return queryset.none()


#
# ObjectPermissions
#


class ObjectPermissionViewSet(ModelViewSet):
    queryset = ObjectPermission.objects.all()
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

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        """
        Return the config_data for the currently authenticated User.
        """
        return Response(request.user.config_data)

    @extend_schema(request=OpenApiTypes.OBJECT)
    def patch(self, request):
        """
        Update the config_data for the currently authenticated User.
        """
        # TODO: How can we validate this data?
        user = request.user
        user.config_data = deepmerge(user.config_data, request.data)
        user.save()

        return Response(user.config_data)
