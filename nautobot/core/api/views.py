import logging
import platform
from collections import OrderedDict

from django import __version__ as DJANGO_VERSION
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http.response import HttpResponseBadRequest
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django_rq.queues import get_connection as get_rq_connection
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
from rq.worker import Worker as RQWorker

from graphql import get_default_backend
from graphql.execution import ExecutionResult
from graphql.type.schema import GraphQLSchema
from graphql.execution.middleware import MiddlewareManager
from graphene_django.settings import graphene_settings
from graphene_django.views import GraphQLView, instantiate_middleware, HttpError

from nautobot.core.celery import app as celery_app
from nautobot.core.api import BulkOperationSerializer
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.utilities.api import get_serializer_for_model
from nautobot.utilities.utils import (
    get_all_lookup_expr_for_field,
    get_filterset_parameter_form_field,
    get_form_for_model,
    FilterSetFieldNotFound,
    ensure_content_type_and_field_name_inquery_params,
)
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


class BulkCreateModelMixin:
    """
    Bulk create multiple model instances by using the
    Serializers ``many=True`` ability from Django REST >= 2.2.5.

    .. note::
        This mixin uses the same method to create model instances
        as ``CreateModelMixin`` because both non-bulk and bulk
        requests will use ``POST`` request method.
    """

    def bulk_create(self, request, *args, **kwargs):
        return self.perform_bulk_create(request)

    def perform_bulk_create(self, request):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            # 2.0 TODO: this should be wrapped with a paginator so as to match the same format as the list endpoint,
            # i.e. `{"results": [{instance}, {instance}, ...]}` instead of bare list `[{instance}, {instance}, ...]`
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class BulkUpdateModelMixin:
    """
    Support bulk modification of objects using the list endpoint for a model. Accepts a PATCH action with a list of one
    or more JSON objects, each specifying the UUID of an object to be updated as well as the attributes to be set.
    For example:

    PATCH /api/dcim/sites/
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

    DELETE /api/dcim/sites/
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
    brief = False
    # v2 TODO(jathan): Revisit whether this is still valid post-cacheops. Re: prefetch_related vs.
    # select_related
    brief_prefetch_fields = []

    def get_serializer(self, *args, **kwargs):

        # If a list of objects has been provided, initialize the serializer with many=True
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        logger = logging.getLogger("nautobot.core.api.views.ModelViewSet")

        # If using 'brief' mode, find and return the nested serializer for this model, if one exists
        if self.brief:
            logger.debug("Request is for 'brief' format; initializing nested serializer")
            try:
                serializer = get_serializer_for_model(self.queryset.model, prefix="Nested")
                logger.debug(f"Using serializer {serializer}")
                return serializer
            except SerializerNotFound:
                logger.debug(f"Nested serializer for {self.queryset.model} not found!")

        # Fall back to the hard-coded serializer class
        return self.serializer_class

    def get_queryset(self):
        # If using brief mode, clear all prefetches from the queryset and append only brief_prefetch_fields (if any)
        if self.brief:
            # v2 TODO(jathan): Replace prefetch_related with select_related
            return super().get_queryset().prefetch_related(None).prefetch_related(*self.brief_prefetch_fields)

        return super().get_queryset()

    def initialize_request(self, request, *args, **kwargs):
        # Check if brief=True has been passed
        if request.method == "GET" and request.GET.get("brief"):
            self.brief = True

        return super().initialize_request(request, *args, **kwargs)

    def restrict_queryset(self, request, *args, **kwargs):
        """
        Restrict the view's queryset to allow only the permitted objects for the given request.

        Subclasses (such as nautobot.extras.api.views.JobModelViewSet) may wish to override this.

        Called by initial(), below.
        """
        # Restrict the view's QuerySet to allow only the permitted objects for the given user, if applicable
        if request.user.is_authenticated:
            action = HTTP_ACTIONS[request.method]
            if action:
                self.queryset = self.queryset.restrict(request.user, action)

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
        logger = logging.getLogger("nautobot.core.api.views.ModelViewSet")

        try:
            return super().dispatch(request, *args, **kwargs)
        except ProtectedError as e:
            protected_objects = list(e.protected_objects)
            msg = f"Unable to delete object. {len(protected_objects)} dependent objects were found: "
            msg += ", ".join([f"{obj} ({obj.pk})" for obj in protected_objects])
            logger.warning(msg)
            return self.finalize_response(request, Response({"detail": msg}, status=409), *args, **kwargs)


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
        logger = logging.getLogger("nautobot.core.api.views.ModelViewSet")
        logger.info(f"Creating new {model._meta.verbose_name}")

        # Enforce object-level permissions on save()
        try:
            with transaction.atomic():
                instance = serializer.save()
                self._validate_objects(instance)
        except ObjectDoesNotExist:
            raise PermissionDenied()

    def perform_update(self, serializer):
        model = self.queryset.model
        logger = logging.getLogger("nautobot.core.api.views.ModelViewSet")
        logger.info(f"Updating {model._meta.verbose_name} {serializer.instance} (PK: {serializer.instance.pk})")

        # Enforce object-level permissions on save()
        try:
            with transaction.atomic():
                instance = serializer.save()
                self._validate_objects(instance)
        except ObjectDoesNotExist:
            raise PermissionDenied()

    def perform_destroy(self, instance):
        model = self.queryset.model
        logger = logging.getLogger("nautobot.core.api.views.ModelViewSet")
        logger.info(f"Deleting {model._meta.verbose_name} {instance} (PK: {instance.pk})")

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
    This is the root of the REST API. API endpoints are arranged by app and model name; e.g. `/api/dcim/sites/`.
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
                    # 2.0 TODO: remove rq-workers-running property
                    "rq-workers-running": {"type": "integer"},
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
                # 2.0 TODO: remove rq-workers-running
                "rq-workers-running": RQWorker.count(get_rq_connection("default")),
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
# Lookup Expr
#


class GetFilterSetFieldLookupExpressionChoicesAPIView(NautobotAPIVersionMixin, APIView):
    """API View that gets all lookup expression choices for a FilterSet field."""

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        try:
            field_name, model = ensure_content_type_and_field_name_inquery_params(request.GET)
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
            field_name, model = ensure_content_type_and_field_name_inquery_params(request.GET)
        except ValidationError as err:
            return Response(err.args[0], status=err.code)
        model_form = get_form_for_model(model)
        if model_form is None:
            logger = logging.getLogger(__name__)

            logger.warning(f"Form for {model} model not found")
            # Because the DOM Representation cannot be derived from a CharField without a Form, the DOM Representation must be hardcoded.
            return Response(
                {
                    "dom_element": f"<input type='text' name='{field_name}' class='form-control lookup_value-input' id='id_{field_name}'>"
                }
            )
        try:
            form_field = get_filterset_parameter_form_field(model, field_name)
        except FilterSetFieldNotFound:
            return Response("field_name not found", 404)

        field_dom_representation = form_field.get_bound_field(model_form(auto_id="id_for_%s"), field_name).as_widget()
        return Response({"dom_element": field_dom_representation})
