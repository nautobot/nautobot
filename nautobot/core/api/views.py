import itertools
import logging
import platform
from collections import OrderedDict
import re

from django import __version__ as DJANGO_VERSION, forms
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http.response import HttpResponseBadRequest
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import NoReverseMatch, reverse as django_reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet as ModelViewSet_
from rest_framework.viewsets import ReadOnlyModelViewSet as ReadOnlyModelViewSet_
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ParseError
from drf_spectacular.plumbing import get_relative_url, set_query_parameters
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularSwaggerView, SpectacularRedocView

from graphql import get_default_backend
from graphql.execution import ExecutionResult
from graphql.type.schema import GraphQLSchema
from graphql.execution.middleware import MiddlewareManager
from graphene_django.settings import graphene_settings
from graphene_django.views import GraphQLView, instantiate_middleware, HttpError

from nautobot.core.api import BulkOperationSerializer
from nautobot.core.celery import app as celery_app
from nautobot.core.exceptions import FilterSetFieldNotFound
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.data import is_uuid
from nautobot.core.utils.filtering import get_all_lookup_expr_for_field, get_filterset_parameter_form_field
from nautobot.core.utils.lookup import get_form_for_model, get_route_for_model
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.utils.requests import ensure_content_type_and_field_name_in_query_params
from nautobot.extras.registry import registry
from . import serializers

HTTP_ACTIONS = {
    "GET": "view",
    "OPTIONS": None,
    "HEAD": "view",
    "POST": "add",
    "PUT": "change",
    "PATCH": "change",
    "DELETE": "delete",
}

#
# Mixins
#


class NautobotAPIVersionMixin:
    """Add Nautobot-specific handling to the base APIView class."""

    def finalize_response(self, request, response, *args, **kwargs):
        """Returns the final response object."""
        response = super().finalize_response(request, response, *args, **kwargs)
        try:
            # Add the API version to the response, if available
            response["API-Version"] = request.version
        except AttributeError:
            pass
        return response


class BulkUpdateModelMixin:
    """
    Support bulk modification of objects using the list endpoint for a model. Accepts a PATCH action with a list of one
    or more JSON objects, each specifying the UUID of an object to be updated as well as the attributes to be set.
    For example:

    PATCH /api/dcim/locations/
    [
        {
            "id": "1f554d07-d099-437d-8d48-7d6e35ec8fa3",
            "name": "New name"
        },
        {
            "id": "1f554d07-d099-437d-8d48-7d6e65ec8fa3",
            "status": "planned"
        }
    ]
    """

    bulk_operation_serializer_class = BulkOperationSerializer

    def bulk_update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = self.bulk_operation_serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        qs = self.get_queryset().filter(pk__in=[o["id"] for o in serializer.data])

        # Map update data by object ID
        update_data = {obj.pop("id"): obj for obj in request.data}

        data = self.perform_bulk_update(qs, update_data, partial=partial)

        # 2.0 TODO: this should be wrapped with a paginator so as to match the same format as the list endpoint,
        # i.e. `{"results": [{instance}, {instance}, ...]}` instead of bare list `[{instance}, {instance}, ...]`
        return Response(data, status=status.HTTP_200_OK)

    def perform_bulk_update(self, objects, update_data, partial):
        with transaction.atomic():
            data_list = []
            for obj in objects:
                data = update_data.get(str(obj.id))
                serializer = self.get_serializer(obj, data=data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                data_list.append(serializer.data)

            return data_list

    def bulk_partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.bulk_update(request, *args, **kwargs)


class BulkDestroyModelMixin:
    """
    Support bulk deletion of objects using the list endpoint for a model. Accepts a DELETE action with a list of one
    or more JSON objects, each specifying the UUID of an object to be deleted. For example:

    DELETE /api/dcim/locations/
    [
        {"id": "3f01f169-49b9-42d5-a526-df9118635d62"},
        {"id": "c27d6c5b-7ea8-41e7-b9dd-c065efd5d9cd"}
    ]
    """

    bulk_operation_serializer_class = BulkOperationSerializer

    @extend_schema(
        request=BulkOperationSerializer(many=True),
    )
    def bulk_destroy(self, request, *args, **kwargs):
        serializer = self.bulk_operation_serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        qs = self.get_queryset().filter(pk__in=[o["id"] for o in serializer.data])

        self.perform_bulk_destroy(qs)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_bulk_destroy(self, objects):
        with transaction.atomic():
            for obj in objects:
                self.perform_destroy(obj)


#
# Viewsets
#


class ModelViewSetMixin:
    logger = logging.getLogger(__name__ + ".ModelViewSet")

    # TODO: can't set lookup_value_regex globally; some models/viewsets (ContentType, Group) have integer rather than
    #       UUID PKs and also do NOT support composite-keys.
    #       The impact of NOT setting this is that per the OpenAPI schema, only UUIDs are permitted for most ViewSets;
    #       however, "secretly" due to our custom get_object() implementation below, you can actually also specify a
    #       composite_key value instead of a UUID. We're not currently documenting/using this feature, so OK for now
    # lookup_value_regex = r"[^/]+"

    def get_object(self):
        """Extend rest_framework.generics.GenericAPIView.get_object to allow "pk" lookups to use a composite-key."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            f"Expected view {self.__class__.__name__} to be called with a URL keyword argument named "
            f'"{lookup_url_kwarg}". Fix your URL conf, or set the `.lookup_field` attribute on the view correctly.'
        )

        if lookup_url_kwarg == "pk" and hasattr(queryset.model, "composite_key"):
            # Support lookup by either PK (UUID) or composite_key
            lookup_value = self.kwargs["pk"]
            if is_uuid(lookup_value):
                obj = get_object_or_404(queryset, pk=lookup_value)
            else:
                obj = get_object_or_404(queryset, composite_key=lookup_value)
        else:
            # Default DRF lookup behavior, just in case a viewset has overridden `lookup_url_kwarg` for its own needs
            obj = get_object_or_404(queryset, **{self.lookup_field: self.kwargs[lookup_url_kwarg]})

        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer(self, *args, **kwargs):
        # If a list of objects has been provided, initialize the serializer with many=True
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if "text/csv" in self.request.accepted_media_type:
            # CSV rendering should always use depth 1
            context["depth"] = 1
        elif self.request.method == "GET":
            # Only allow the depth to be greater than 0 in GET requests
            depth = 0
            try:
                depth = int(self.request.query_params.get("depth", 0))
            except ValueError:
                self.logger.warning("The depth parameter must be an integer between 0 and 10")

            context["depth"] = depth
        else:
            # Use depth=0 in all write type requests.
            context["depth"] = 0

        return context

    def restrict_queryset(self, request, *args, **kwargs):
        """
        Restrict the view's queryset to allow only the permitted objects for the given request.

        Subclasses (such as nautobot.extras.api.views.JobModelViewSet) may wish to override this.

        Called by initial(), below.
        """
        # Restrict the view's QuerySet to allow only the permitted objects for the given user, if applicable
        if request.user.is_authenticated:
            http_action = HTTP_ACTIONS[request.method]
            if http_action:
                self.queryset = self.queryset.restrict(request.user, http_action)

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.

        Override of internal Django Rest Framework API.
        """
        super().initial(request, *args, **kwargs)

        # Django Rest Framework stores the raw API version string e.g. "1.2" as request.version.
        # For convenience we split it out into integer major/minor versions as well.
        major, minor = request.version.split(".")
        request.major_version = int(major)
        request.minor_version = int(minor)

        self.restrict_queryset(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ProtectedError as e:
            protected_objects = list(e.protected_objects)
            msg = f"Unable to delete object. {len(protected_objects)} dependent objects were found: "
            msg += ", ".join([f"{obj} ({obj.pk})" for obj in protected_objects])
            self.logger.warning(msg)
            return self.finalize_response(request, Response({"detail": msg}, status=409), *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        # In the case of certain errors, we might not even get to the point of setting request.accepted_media_type
        if hasattr(request, "accepted_media_type") and "text/csv" in request.accepted_media_type:
            filename = f"{settings.BRANDING_PREPENDED_FILENAME}{self.queryset.model.__name__.lower()}_data.csv"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return super().finalize_response(request, response, *args, **kwargs)


class ModelViewSet(
    NautobotAPIVersionMixin,
    BulkUpdateModelMixin,
    BulkDestroyModelMixin,
    ModelViewSetMixin,
    ModelViewSet_,
):
    """
    Extend DRF's ModelViewSet to support bulk update and delete functions.
    """

    logger = logging.getLogger(__name__ + ".ModelViewSet")

    def _validate_objects(self, instance):
        """
        Check that the provided instance or list of instances are matched by the current queryset. This confirms that
        any newly created or modified objects abide by the attributes granted by any applicable ObjectPermissions.
        """
        if isinstance(instance, list):
            # Check that all instances are still included in the view's queryset
            conforming_count = self.queryset.filter(pk__in=[obj.pk for obj in instance]).count()
            if conforming_count != len(instance):
                raise ObjectDoesNotExist
        else:
            # Check that the instance is matched by the view's queryset
            self.queryset.get(pk=instance.pk)

    def perform_create(self, serializer):
        model = self.queryset.model
        self.logger.info(f"Creating new {model._meta.verbose_name}")

        # Enforce object-level permissions on save()
        try:
            with transaction.atomic():
                instance = serializer.save()
                self._validate_objects(instance)
        except ObjectDoesNotExist:
            raise PermissionDenied()

    def perform_update(self, serializer):
        model = self.queryset.model
        self.logger.info(f"Updating {model._meta.verbose_name} {serializer.instance} (PK: {serializer.instance.pk})")

        # Enforce object-level permissions on save()
        try:
            with transaction.atomic():
                instance = serializer.save()
                self._validate_objects(instance)
        except ObjectDoesNotExist:
            raise PermissionDenied()

    def perform_destroy(self, instance):
        model = self.queryset.model
        self.logger.info(f"Deleting {model._meta.verbose_name} {instance} (PK: {instance.pk})")

        return super().perform_destroy(instance)


class ReadOnlyModelViewSet(NautobotAPIVersionMixin, ModelViewSetMixin, ReadOnlyModelViewSet_):
    """
    Extend DRF's ReadOnlyModelViewSet to support queryset restriction.
    """


#
# Views
#


class APIRootView(NautobotAPIVersionMixin, APIView):
    """
    This is the root of the REST API. API endpoints are arranged by app and model name; e.g. `/api/dcim/locations/`.
    """

    _ignore_model_permissions = True

    def get_view_name(self):
        return "API Root"

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        return Response(
            OrderedDict(
                (
                    (
                        "circuits",
                        reverse("circuits-api:api-root", request=request, format=format),
                    ),
                    (
                        "dcim",
                        reverse("dcim-api:api-root", request=request, format=format),
                    ),
                    (
                        "extras",
                        reverse("extras-api:api-root", request=request, format=format),
                    ),
                    ("graphql", reverse("graphql-api", request=request, format=format)),
                    (
                        "ipam",
                        reverse("ipam-api:api-root", request=request, format=format),
                    ),
                    (
                        "plugins",
                        reverse("plugins-api:api-root", request=request, format=format),
                    ),
                    ("status", reverse("api-status", request=request, format=format)),
                    (
                        "tenancy",
                        reverse("tenancy-api:api-root", request=request, format=format),
                    ),
                    (
                        "users",
                        reverse("users-api:api-root", request=request, format=format),
                    ),
                    (
                        "virtualization",
                        reverse(
                            "virtualization-api:api-root",
                            request=request,
                            format=format,
                        ),
                    ),
                )
            )
        )


class StatusView(NautobotAPIVersionMixin, APIView):
    """
    A lightweight read-only endpoint for conveying the current operational status.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "django-version": {"type": "string"},
                    "installed-apps": {"type": "object"},
                    "nautobot-version": {"type": "string"},
                    "plugins": {"type": "object"},
                    "python-version": {"type": "string"},
                    "celery-workers-running": {"type": "integer"},
                },
            }
        }
    )
    def get(self, request):
        # Gather the version numbers from all installed Django apps
        installed_apps = {}
        for app_config in apps.get_app_configs():
            app = app_config.module
            version = getattr(app, "VERSION", getattr(app, "__version__", None))
            if version:
                if isinstance(version, tuple):
                    version = ".".join(str(n) for n in version)
            installed_apps[app_config.name] = version
        installed_apps = dict(sorted(installed_apps.items()))

        # Gather installed plugins
        plugins = {}
        for plugin_name in settings.PLUGINS:
            plugin_name = plugin_name.rsplit(".", 1)[-1]
            plugin_config = apps.get_app_config(plugin_name)
            plugins[plugin_name] = getattr(plugin_config, "version", None)
        plugins = dict(sorted(plugins.items()))

        # Gather Celery workers
        workers = celery_app.control.inspect().active()  # list or None
        worker_count = len(workers) if workers is not None else 0

        return Response(
            {
                "django-version": DJANGO_VERSION,
                "installed-apps": installed_apps,
                "nautobot-version": settings.VERSION,
                "plugins": plugins,
                "python-version": platform.python_version(),
                "celery-workers-running": worker_count,
            }
        )


class APIVersioningGetSchemaURLMixin:
    """Mixin to override the way that Swagger/Redoc views request the schema JSON from the server."""

    def _get_schema_url(self, request):
        schema_url = self.url or get_relative_url(reverse(self.url_name, request=request))
        return set_query_parameters(
            url=schema_url,
            lan=request.GET.get("lang"),
            # Default in drf-spectacular here is `version=request.GET.get("version")`, which assumes that the
            # query parameter to both views is called "version".
            # 1. We should use `request.version` instead of `request.GET.get("version") as that also allows
            # for accept-header versioning in the initial request, not just query-parameter versioning
            # 2. We need to pass `api_version` rather than `version` as the query parameter since that's what
            # Nautobot API versioning expects.
            api_version=request.version,
        )


class NautobotSpectacularSwaggerView(APIVersioningGetSchemaURLMixin, SpectacularSwaggerView):
    """
    Extend SpectacularSwaggerView to support Nautobot's ?api_version=<version> query parameter and page styling.
    """

    class FakeOpenAPIRenderer(OpenApiJsonRenderer):
        """For backwards-compatibility with drf-yasg, allow `?format=openapi` as a way to request the schema JSON."""

        format = "openapi"

    renderer_classes = SpectacularSwaggerView.renderer_classes + [FakeOpenAPIRenderer]

    template_name = "swagger_ui.html"

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        """Fix up the rendering of the Swagger UI to work with Nautobot's UI."""
        if not request.user.is_authenticated and get_settings_or_config("HIDE_RESTRICTED_UI"):
            doc_url = reverse("api_docs")
            login_url = reverse(settings.LOGIN_URL)
            return redirect(f"{login_url}?next={doc_url}")

        # For backward compatibility wtih drf-yasg, `/api/docs/?format=openapi` is a redirect to the JSON schema.
        if request.GET.get("format") == "openapi":
            return redirect("schema_json", permanent=True)

        # drf-spectacular uses "settings" in the rendering context as a way to inject custom JavaScript if desired,
        # which of course conflicts with Nautobot's use of "settings" as a representation of django.settings.
        # So we need to intercept it and fix it up.
        response = super().get(request, *args, **kwargs)
        response.data["swagger_settings"] = response.data["settings"]
        del response.data["settings"]

        # Add additional data so drf-spectacular will use the Token keyword in authorization header.
        response.data["schema_auth_names"] = ["tokenAuth"]
        return response


class NautobotSpectacularRedocView(APIVersioningGetSchemaURLMixin, SpectacularRedocView):
    """Extend SpectacularRedocView to support Nautobot's ?api_version=<version> query parameter."""


#
# GraphQL
#


class GraphQLDRFAPIView(NautobotAPIVersionMixin, APIView):
    """
    API View for GraphQL to integrate properly with DRF authentication mechanism.
    The code is a stripped down version of graphene-django default View
    https://github.com/graphql-python/graphene-django/blob/main/graphene_django/views.py#L57
    """

    permission_classes = [AllowAny]
    graphql_schema = None
    executor = None
    backend = None
    middleware = None
    root_value = None

    def __init__(self, schema=None, executor=None, middleware=None, root_value=None, backend=None):
        self.schema = schema
        self.executor = executor
        self.middleware = middleware
        self.root_value = root_value
        self.backend = backend

    def get_root_value(self, request):
        return self.root_value

    def get_middleware(self, request):
        return self.middleware

    def get_context(self, request):
        return request

    def get_backend(self, request):
        return self.backend

    @extend_schema(
        request=serializers.GraphQLAPISerializer,
        description="Query the database using a GraphQL query",
        responses={
            200: {"type": "object", "properties": {"data": {"type": "object"}}},
            400: {
                "type": "object",
                "properties": {"errors": {"type": "array", "items": {"type": "object"}}},
            },
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            data = self.parse_body(request)
            result, status_code = self.get_response(request, data)

            return Response(
                result,
                status=status_code,
            )

        except HttpError as e:
            return Response(
                {"errors": [GraphQLView.format_error(e)]},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def init_graphql(self):
        if not self.schema:
            self.schema = graphene_settings.SCHEMA

        if self.backend is None:
            self.backend = get_default_backend()

        self.graphql_schema = self.graphql_schema or self.schema

        if self.middleware is not None:
            if isinstance(self.middleware, MiddlewareManager):
                self.middleware = graphene_settings.MIDDLEWARE
            else:
                self.middleware = list(instantiate_middleware(self.middleware))

        self.executor = self.executor
        self.root_value = self.root_value

        assert isinstance(self.graphql_schema, GraphQLSchema), "A Schema is required to be provided to GraphQLAPIView."

    def get_response(self, request, data):
        """Extract the information from the request, execute the GraphQL query and form the response.

        Args:
            request (HttpRequest): Request Object from Django
            data (dict): Parsed content of the body of the request.

        Returns:
            response (dict), status_code (int): Payload of the response to send and the status code.
        """
        query, variables, operation_name, _id = GraphQLView.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(request, data, query, variables, operation_name)

        status_code = 200
        if execution_result:
            response = {}

            if execution_result.errors:
                response["errors"] = [GraphQLView.format_error(e) for e in execution_result.errors]

            if execution_result.invalid:
                status_code = 400
            else:
                response["data"] = execution_result.data

            result = response
        else:
            result = None

        return result, status_code

    def parse_body(self, request):
        """Analyze the request and based on the content type,
        extract the query from the body as a string or as a JSON payload.

        Args:
            request (HttpRequest): Request object from Django

        Returns:
            dict: GraphQL query
        """
        content_type = GraphQLView.get_content_type(request)

        if content_type == "application/graphql":
            return {"query": request.body.decode()}

        elif content_type == "application/json":
            try:
                return request.data
            except ParseError:
                raise HttpError(HttpResponseBadRequest("Request body contained Invalid JSON."))

        return {}

    def execute_graphql_request(self, request, data, query, variables, operation_name):
        """Execute a GraphQL request and return the result

        Args:
            request (HttpRequest): Request object from Django
            data (dict): Parsed content of the body of the request.
            query (dict): GraphQL query
            variables (dict): Optional variables for the GraphQL query
            operation_name (str): GraphQL operation name: query, mutations etc..

        Returns:
            ExecutionResult: Execution result object from GraphQL with response or error message.
        """

        self.init_graphql()
        if not query:
            raise HttpError(HttpResponseBadRequest("Must provide query string."))

        try:
            backend = self.get_backend(request)
            document = backend.document_from_string(self.graphql_schema, query)
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

        operation_type = document.get_operation_type(operation_name)
        if operation_type and operation_type != "query":
            raise HttpError(
                HttpResponseBadRequest(f"'{operation_type}' is not a supported operation, Only query are supported.")
            )

        try:
            extra_options = {}
            if self.executor:
                # We only include it optionally since
                # executor is not a valid argument in all backends
                extra_options["executor"] = self.executor

            options = {
                "root_value": self.get_root_value(request),
                "variable_values": variables,
                "operation_name": operation_name,
                "context_value": self.get_context(request),
                "middleware": self.get_middleware(request),
            }
            options.update(extra_options)

            operation_type = document.get_operation_type(operation_name)
            return document.execute(**options)
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)


#
# UI Views
#


class GetMenuAPIView(NautobotAPIVersionMixin, APIView):
    """API View that returns the nav-menu content applicable to the requesting user."""

    permission_classes = [IsAuthenticated]

    def format_and_remove_hidden_menu(self, request, data, hide_restricted_ui):
        """
        Formats the menu data and removes hidden menu items based on user permissions.

        Args:
            request: The request object.
            data (Union[dict, str]): The menu data to format and filter. Can be either a dictionary or a string.
            hide_restricted_ui (bool): Flag indicating whether to hide restricted menu items.

        Returns:
            Union[dict, str]: The formatted menu data without hidden items. Returns a dict if `data` is a
            `dict`, otherwise returns a string.

        Example:
            Input:
            {
                "Devices": {
                    "permission": [...],
                    "weight": "",
                    "data": "data value"
                },
            }

            Output:
            {"Devices": "data value"}
        """
        if isinstance(data, dict):
            return_value = {}
            for name, value in data.items():
                if not hide_restricted_ui or any(
                    request.user.has_perm(permission) for permission in value["permissions"]
                ):
                    return_value[name] = self.format_and_remove_hidden_menu(request, value["data"], hide_restricted_ui)
            return return_value
        return data

    @extend_schema(exclude=True)
    def get(self, request):
        """Get the menu data for the requesting user.

        Returns the following data-structure (as not all context in registry["nav_menu"] is relevant to the UI):

        {
            "Inventory": {
                "Devices": {
                    "Devices": "/dcim/devices/",
                    "Device Types": "/dcim/device-types/",
                    ...
                    "Connections": {
                        "Cables": "/dcim/cables/",
                        "Console Connections": "/dcim/console-connections/",
                        ...
                    },
                    ...
                },
                "Organization": {
                    ...
                },
                ...
            },
            "Networks": {
                ...
            },
            "Security": {
                ...
            },
            "Automation": {
                ...
            },
            "Platform": {
                ...
            },
        }
        """
        base_menu = registry["new_ui_nav_menu"]
        HIDE_RESTRICTED_UI = get_settings_or_config("HIDE_RESTRICTED_UI")
        formatted_data = self.format_and_remove_hidden_menu(request, base_menu, HIDE_RESTRICTED_UI)
        return Response(formatted_data)


class GetObjectCountsView(NautobotAPIVersionMixin, APIView):
    """
    Enumerate the models listed on the Nautobot home page and return data structure
    containing verbose_name_plural, url and count.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        object_counts = {
            "Inventory": [
                {"model": "dcim.rack"},
                {"model": "dcim.devicetype"},
                {"model": "dcim.device"},
                {"model": "dcim.virtualchassis"},
                {"model": "dcim.deviceredundancygroup"},
                {"model": "dcim.cable"},
            ],
            "Networks": [
                {"model": "ipam.vrf"},
                {"model": "ipam.prefix"},
                {"model": "ipam.ipaddress"},
                {"model": "ipam.vlan"},
            ],
            "Security": [{"model": "extras.secret"}],
            "Platform": [
                {"model": "extras.gitrepository"},
                {"model": "extras.relationship"},
                {"model": "extras.computedfield"},
                {"model": "extras.customfield"},
                {"model": "extras.customlink"},
                {"model": "extras.tag"},
                {"model": "extras.status"},
                {"model": "extras.role"},
            ],
        }
        HIDE_RESTRICTED_UI = get_settings_or_config("HIDE_RESTRICTED_UI")

        for entry in itertools.chain(*object_counts.values()):
            app_label, model_name = entry["model"].split(".")
            model = apps.get_model(app_label, model_name)
            permission = get_permission_for_model(model, "view")
            if HIDE_RESTRICTED_UI and not request.user.has_perm(permission):
                continue
            data = {"name": model._meta.verbose_name_plural}
            try:
                data["url"] = django_reverse(get_route_for_model(model, "list"))
            except NoReverseMatch:
                logger = logging.getLogger(__name__)
                route = get_route_for_model(model, "list")
                logger.warning(f"Handled expected exception when generating filter field: {route}")
            manager = model.objects
            if request.user.has_perm(permission):
                if hasattr(manager, "restrict"):
                    data["count"] = model.objects.restrict(request.user).count()
                else:
                    data["count"] = model.objects.count()
            entry.update(data)

        return Response(object_counts)


class GetSettingsView(NautobotAPIVersionMixin, APIView):
    """
    This view exposes Nautobot settings.

    Get settings by providing one or more `name` in the query parameters.

    Example:

    - /api/settings/?name=FOO            # Returns the setting with name 'FOO'
    - /api/settings/?name=FOO&name=BAR   # Returns the setting with these names 'FOO' and 'BAR
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        # As of now, we just have `allowed_settings` settings. Because the purpose of this API is limited for the time being,
        # we may need more access to serializable and non-serializable settings data as the new UI expands. As a result,
        # exposing all settings data would be desirable in the future.
        # NOTE: When exposing all settings, include a way to limit settings which can be exposed for security concerns
        # e.g `SECRET_KEY`, `NAPALM_PASSWORD` e.t.c. also `allowed_settings` can be moved into settings.py
        allowed_settings = ["FEEDBACK_BUTTON_ENABLED"]
        # Filter out settings_names not allowed to be exposed to the API
        valid_settings = [name for name in request.GET.getlist("name") if name in allowed_settings]

        invalid_settings = [name for name in request.GET.getlist("name") if name not in allowed_settings]
        if invalid_settings:
            return Response(
                {"error": f"Invalid settings names specified: {', '.join(invalid_settings)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        res = {settings_name: get_settings_or_config(settings_name) for settings_name in valid_settings}
        return Response(res)


#
# Lookup Expr
#


class GetFilterSetFieldLookupExpressionChoicesAPIView(NautobotAPIVersionMixin, APIView):
    """API View that gets all lookup expression choices for a FilterSet field."""

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        try:
            field_name, model = ensure_content_type_and_field_name_in_query_params(request.GET)
            data = get_all_lookup_expr_for_field(model, field_name)
        except FilterSetFieldNotFound:
            return Response("field_name not found", status=404)
        except ValidationError as err:
            return Response(err.args[0], status=err.code)

        # Needs to be returned in this format because this endpoint is used by
        # DynamicModelChoiceField which requires the response of an api in this exact format
        return Response(
            {
                "count": len(data),
                "next": None,
                "previous": None,
                "results": data,
            }
        )


class GetFilterSetFieldDOMElementAPIView(NautobotAPIVersionMixin, APIView):
    """API View that gets the DOM element representation of a FilterSet field."""

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        try:
            field_name, model = ensure_content_type_and_field_name_in_query_params(request.GET)
        except ValidationError as err:
            return Response(err.args[0], status=err.code)
        try:
            form_field = get_filterset_parameter_form_field(model, field_name)
        except FilterSetFieldNotFound:
            return Response("field_name not found", 404)

        try:
            model_form = get_form_for_model(model)
            model_form_instance = model_form(auto_id="id_for_%s")
        except Exception as err:
            # Cant determine the exceptions to handle because any exception could be raised,
            # e.g InterfaceForm would raise a ObjectDoesNotExist Error since no device was provided
            # While other forms might raise other errors, also if model_form is None a TypeError would be raised.
            logger = logging.getLogger(__name__)
            logger.debug(f"Handled expected exception when generating filter field: {err}")

            # Create a temporary form and get a BoundField for the specified field
            # This is necessary to generate the HTML representation using as_widget()
            TempForm = type("TempForm", (forms.Form,), {field_name: form_field})
            model_form_instance = TempForm(auto_id="id_for_%s")

        bound_field = form_field.get_bound_field(model_form_instance, field_name)
        if request.META.get("HTTP_ACCEPT") == "application/json":
            data = {
                "field_type": form_field.__class__.__name__,
                "attrs": bound_field.field.widget.attrs,
                # `is_required` is redundant here as it's not used in filterset;
                # Just leaving it here because this would help when building create/edit form for new UI,
                # This logic(as_json representation) should be extracted into a helper function at that time
                "is_required": bound_field.field.widget.is_required,
            }
            if hasattr(bound_field.field.widget, "choices"):
                data["choices"] = list(bound_field.field.widget.choices)
        else:
            data = bound_field.as_widget()
        return Response(data)


class NewUIReadyRoutesAPIView(NautobotAPIVersionMixin, APIView):
    """API View that returns a list of new UI-ready routes."""

    permission_classes = [IsAuthenticated]

    def to_javascript_regex(self, regex_pattern):
        """
        Convert a Python regex pattern into JavaScript regex format.

        Args:
            regex_pattern (str): The Python regex pattern to convert.

        Returns:
            str: The JavaScript-compatible regex pattern.
        """
        # Remove named groups (?P<...>)
        pattern = re.sub(r"\?P<[a-z]+>", "", regex_pattern)

        # Escape `/` with `\`
        pattern = pattern.replace("/", "\\/")

        # Replace `/Z` with `$`
        pattern = pattern.replace(r"\Z", "$")

        return pattern

    @extend_schema(exclude=True)
    def get(self, request):
        url_regex_patterns = registry["new_ui_ready_routes"]
        return Response([self.to_javascript_regex(pattern) for pattern in url_regex_patterns])
