from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.models import Group
from django.db.models import Count
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import ViewSet

from nautobot.core.api.serializers import BulkOperationIntegerIDSerializer
from nautobot.core.api.views import ModelViewSet
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.utils.data import deepmerge
from nautobot.users import filters
from nautobot.users.models import ObjectPermission, Token
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

    @action(methods=["GET"], detail=False, url_path="my-profile")
    def my_profile(self, request):
        serializer = self.serializer_class(instance=request.user, context={"request": request})
        return Response(serializer.data)

    @method_decorator(ensure_csrf_cookie)
    @action(methods=["GET"], detail=False, permission_classes=[AllowAny])
    def session(self, request):
        from django.conf import settings as django_settings
        from nautobot.core.settings_funcs import sso_auth_enabled
        from social_django.context_processors import backends
        from django.urls import reverse

        serializer = self.serializer_class(instance=request.user, context={"request": request})

        _backends = []
        sso_enabled = sso_auth_enabled(django_settings.AUTHENTICATION_BACKENDS)

        social_auth_backends = backends(request)["backends"]
        if sso_enabled:
            for backend in social_auth_backends["backends"]:
                _backends.append(reverse("social:begin", kwargs={"backend": backend}))

        resp = {
            "user": serializer.data,
            "logged_in": request.user.is_authenticated,
            "sso_enabled": sso_enabled,
            "sso_user": (len(social_auth_backends["associated"]) > 0),
            "backends": _backends,
        }

        return Response(resp)


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
    queryset = RestrictedQuerySet(model=Token).select_related("user")
    serializer_class = serializers.TokenSerializer
    filterset_class = filters.TokenFilterSet

    @property
    def authentication_classes(self):
        """Inherit default authentication_classes and basic authentication."""
        classes = super().authentication_classes
        return classes + [BasicAuthentication]

    # TODO(timizuo): Move authenticate and logout to its own view;
    #  as it is not proper to be on this.
    @action(methods=["POST"], detail=False, permission_classes=[AllowAny])
    def authenticate(self, request):
        serializer = serializers.UserLoginSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user=user)
        return Response(status=200)

    @action(methods=["GET"], detail=False)
    def logout(self, request):
        logout(request)
        return Response(status=200)

    def get_queryset(self):
        """
        Limit users to their own Tokens.
        """
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)


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
