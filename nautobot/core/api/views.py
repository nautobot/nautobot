from collections import OrderedDict
import logging
import os
import platform

from django import __version__ as DJANGO_VERSION, forms
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.db.models.fields.related import ForeignKey, ManyToManyField, RelatedField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel
from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from drf_spectacular.plumbing import get_relative_url, set_query_parameters
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from graphene_django.settings import graphene_settings
from graphene_django.views import GraphQLView, HttpError, instantiate_middleware
from graphql import get_default_backend
from graphql.execution import ExecutionResult
from graphql.execution.middleware import MiddlewareManager
from graphql.type.schema import GraphQLSchema
import redis.exceptions
from rest_framework import routers, serializers as drf_serializers, status
from rest_framework.exceptions import APIException, ParseError, PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet as ModelViewSet_, ReadOnlyModelViewSet as ReadOnlyModelViewSet_
import yaml

from nautobot.core.api import BulkOperationSerializer
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.celery import app as celery_app
from nautobot.core.exceptions import FilterSetFieldNotFound
from nautobot.core.models.fields import TagsField
from nautobot.core.utils.data import is_uuid, render_jinja2
from nautobot.core.utils.filtering import get_all_lookup_expr_for_field, get_filterset_parameter_form_field
from nautobot.core.utils.lookup import get_form_for_model
from nautobot.core.utils.querysets import maybe_prefetch_related, maybe_select_related
from nautobot.core.utils.requests import ensure_content_type_and_field_name_in_query_params
from nautobot.core.views.utils import get_csv_form_fields_from_serializer_class

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


logger = logging.getLogger(__name__)


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

        if lookup_url_kwarg not in self.kwargs:
            raise RuntimeError(
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
            # CSV rendering should always use depth 0
            context["depth"] = 0
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

    def get_queryset(self):
        """
        Attempt to optimize the queryset based on the fields present in the associated serializer.

        See similar logic in nautobot.core.tables.BaseTable.
        """
        queryset = super().get_queryset()
        model = queryset.model
        serializer = self.get_serializer()

        select_fields = []
        prefetch_fields = []

        for field_instance in serializer.fields.values():
            if field_instance.write_only:
                continue
            if field_instance.source == "*":
                continue
            if "." in field_instance.source:
                # DRF uses `field.nested_field` instead of `field__nested_field`
                # TODO: We don't currently attempt to optimize nested lookups.
                continue
            if isinstance(field_instance, (drf_serializers.ManyRelatedField, drf_serializers.ListSerializer)):
                # ListSerializer with depth > 0, ManyRelatedField with depth 0
                try:
                    model_field = model._meta.get_field(field_instance.source)
                except FieldDoesNotExist:
                    continue
                if isinstance(model_field, (ManyToManyField, ManyToManyRel, RelatedField, ManyToOneRel, TagsField)):
                    prefetch_fields.append(field_instance.source)
            elif isinstance(field_instance, (drf_serializers.RelatedField, drf_serializers.Serializer)):
                # Serializer with depth > 0, RelatedField with depth 0
                try:
                    model_field = model._meta.get_field(field_instance.source)
                except FieldDoesNotExist:
                    continue
                if isinstance(model_field, ForeignKey):
                    select_fields.append(field_instance.source)

        if select_fields:
            queryset = maybe_select_related(queryset, select_fields)

        if prefetch_fields:
            queryset = maybe_prefetch_related(queryset, prefetch_fields)

        return queryset

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


class AuthenticatedAPIRootView(NautobotAPIVersionMixin, routers.APIRootView):
    """
    Extends DRF's base APIRootView class to enforce user authentication.
    """

    permission_classes = [IsAuthenticated]

    name = None
    description = None


class APIRootView(AuthenticatedAPIRootView):
    """
    This is the root of the REST API.

    API endpoints are arranged by app and model name; e.g. `/api/dcim/locations/`.
    """

    name = "API Root"

    @extend_schema(exclude=True)
    def get(self, request, *args, format=None, **kwargs):  # pylint: disable=redefined-builtin
        return Response(
            OrderedDict(
                (
                    (
                        "apps",
                        reverse("apps-api:api-root", request=request, format=format),
                    ),
                    (
                        "circuits",
                        reverse("circuits-api:api-root", request=request, format=format),
                    ),
                    (
                        "cloud",
                        reverse("cloud-api:api-root", request=request, format=format),
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
                    (
                        "wireless",
                        reverse(
                            "wireless-api:api-root",
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
                    "nautobot-apps": {"type": "object"},
                    "plugins": {"type": "object"},  # 3.0 TODO: remove this
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
                else:
                    version = str(version)
            installed_apps[app_config.name] = version
        installed_apps = dict(sorted(installed_apps.items()))

        # Gather installed Apps
        nautobot_apps = {}
        for app_name in settings.PLUGINS:
            app_name = app_name.rsplit(".", 1)[-1]
            app_config = apps.get_app_config(app_name)
            nautobot_apps[app_name] = getattr(app_config, "version", None)
        nautobot_apps = dict(sorted(nautobot_apps.items()))

        # Gather Celery workers
        try:
            workers = celery_app.control.inspect().active()  # list or None
        except redis.exceptions.ConnectionError:
            # Celery seems to be not smart enough to auto-retry on intermittent failures, so let's do it ourselves:
            try:
                workers = celery_app.control.inspect().active()  # list or None
            except redis.exceptions.ConnectionError as err:
                logger.error("Repeated ConnectionError from Celery/Redis: %s", err)
                workers = None

        worker_count = len(workers) if workers is not None else 0

        return Response(
            {
                "django-version": DJANGO_VERSION,
                "installed-apps": installed_apps,
                "nautobot-version": settings.VERSION,
                "nautobot-apps": nautobot_apps,
                "plugins": nautobot_apps,  # 3.0 TODO: remove this
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

    renderer_classes = [*SpectacularSwaggerView.renderer_classes, FakeOpenAPIRenderer]

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


@method_decorator(gzip_page, name="dispatch")
class NautobotSpectacularAPIView(SpectacularAPIView):
    def _get_schema_response(self, request):
        # version specified as parameter to the view always takes precedence. after
        # that we try to source version through the schema view's own versioning_class.
        version = self.api_version or request.version or self._get_version_parameter(request)
        cache_key = f"openapi_schema_cache_{version}_{settings.VERSION}"  # Invalidate cache on Nautobot release
        etag = f'W/"{hash(cache_key)}"'

        # With combined browser cache and backend cache, we have three options:
        # - cache expired on browser, but Etag is the same (no changes in nautobot) -> 70-100ms response
        # - cache expired on browser, Etag is different, cache present on backend -> 400-600ms response
        # - cache expired on browser, Etag is different, no cache on backend -> 3-4s response

        if_none_match = request.META.get("HTTP_IF_NONE_MATCH", "")
        if if_none_match == etag:
            return Response(status=304)

        schema = cache.get(cache_key)
        if not schema:
            generator = self.generator_class(urlconf=self.urlconf, api_version=version, patterns=self.patterns)
            schema = generator.get_schema(request=request, public=self.serve_public)
            cache.set(cache_key, schema, 60 * 60 * 24 * 7)

        return Response(
            data=schema,
            headers={
                "Content-Disposition": f'inline; filename="{self._get_filename(request, version)}"',
                "Cache-Control": f"max-age={3 * 24 * 60 * 60}, public",
                "ETag": etag,
                "Vary": "Accept, Accept-Encoding",
            },
        )


#
# GraphQL
#


class GraphQLDRFAPIView(NautobotAPIVersionMixin, APIView):
    """
    API View for GraphQL to integrate properly with DRF authentication mechanism.
    """

    # The code is a stripped down version of graphene-django default View
    # https://github.com/graphql-python/graphene-django/blob/main/graphene_django/views.py#L57

    permission_classes = [IsAuthenticated]
    graphql_schema = None
    executor = None
    backend = None
    middleware = None
    root_value = None

    def __init__(self, schema=None, executor=None, middleware=None, root_value=None, backend=None, **kwargs):
        self.schema = schema
        self.executor = executor
        self.middleware = middleware
        self.root_value = root_value
        self.backend = backend
        super().__init__(**kwargs)

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

        if not isinstance(self.graphql_schema, GraphQLSchema):
            raise ValueError("A Schema is required to be provided to GraphQLAPIView.")

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
            (dict): GraphQL query
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
            (ExecutionResult): Execution result object from GraphQL with response or error message.
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


class CSVImportFieldsForContentTypeAPIView(NautobotAPIVersionMixin, APIView):
    """Get information about CSV import fields for a given ContentType."""

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        content_type_id = request.GET.get("content-type-id")
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
        except ContentType.DoesNotExist:
            return Response({"detail": "Invalid content-type-id."}, status=404)
        model = content_type.model_class()
        if model is None:
            return Response(
                {
                    "detail": (
                        f"Model not found for {content_type.app_label}.{content_type.model}. Perhaps an app is missing?"
                    ),
                },
                status=404,
            )
        try:
            serializer_class = get_serializer_for_model(model)
        except SerializerNotFound:
            return Response(
                {"detail": f"Serializer not found for {content_type.app_label}.{content_type.model}."},
                status=404,
            )
        fields = get_csv_form_fields_from_serializer_class(serializer_class)
        fields.sort(key=lambda field: (not field["required"], field["name"]))
        return Response({"fields": fields})


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


class SettingsJSONSchemaView(NautobotAPIVersionMixin, APIView):
    """View that exposes the JSON Schema of the settings.yaml file in the REST API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def get(self, request):
        file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/settings.yaml"
        with open(file_path, "r") as yamlfile:
            schema_data = yaml.safe_load(yamlfile)
        return Response(schema_data)


class RenderJinjaError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Failed to render Jinja template."
    default_code = "render_jinja_error"


class RenderJinjaView(NautobotAPIVersionMixin, GenericAPIView):
    """
    View to render a Jinja template.
    """

    name = "Render Jinja2 Template"
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.RenderJinjaSerializer

    def post(self, request, *args, **kwargs):
        data = serializers.RenderJinjaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        template_code = data.validated_data["template_code"]
        context = data.validated_data["context"]
        try:
            rendered_template = render_jinja2(template_code, context)
        except Exception as exc:
            raise RenderJinjaError(f"Failed to render Jinja template: {exc}") from exc
        return Response(
            {
                "rendered_template": rendered_template,
                "rendered_template_lines": rendered_template.split("\n"),
                "template_code": template_code,
                "context": context,
            }
        )
