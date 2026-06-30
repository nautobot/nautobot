import json
import re
import time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware as RemoteUserMiddleware_
from django.db import ProgrammingError
from django.http import Http404
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django_structlog.middlewares import RequestMiddleware
from django_structlog.signals import bind_extra_request_failed_metadata
from opentelemetry import trace
import structlog

from nautobot.core.api.utils import is_api_request, rest_api_server_error
from nautobot.core.authentication import (
    assign_groups_to_user,
    assign_permissions_to_user,
)
from nautobot.core.settings_funcs import (
    ldap_auth_enabled,
    remote_auth_enabled,
    sso_auth_enabled,
)
from nautobot.core.views import server_error
from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.context_managers import web_request_context

logger = structlog.get_logger(__name__)

_GRAPHQL_PATHS = frozenset({"/graphql", "/api/graphql"})
_GRAPHQL_OPERATION_RE = re.compile(r"^\s*(query|mutation|subscription)\b", re.IGNORECASE)


class RemoteUserMiddleware(RemoteUserMiddleware_):
    """
    Custom implementation of Django's RemoteUserMiddleware which allows for a user-configurable HTTP header name.
    """

    force_logout_if_no_header = False

    @property
    def header(self):
        return settings.REMOTE_AUTH_HEADER

    def process_request(self, request):
        # Bypass middleware if remote authentication is not enabled
        if not remote_auth_enabled(auth_backends=settings.AUTHENTICATION_BACKENDS):
            return None

        return super().process_request(request)


class ExternalAuthMiddleware(MiddlewareMixin):
    """
    Custom implementation of Django's AuthenticationMiddleware used to set permissions for
    remotely-authenticated users.

    This must inherit from `MiddlewareMixin` to support Django middleware magic.
    """

    def process_request(self, request):
        # Bypass middleware if external authentication is not enabled
        # Session middleware handles attaching the user to the request
        backends_enabled = (
            remote_auth_enabled(auth_backends=settings.AUTHENTICATION_BACKENDS),
            sso_auth_enabled(auth_backends=settings.AUTHENTICATION_BACKENDS),
            ldap_auth_enabled(auth_backends=settings.AUTHENTICATION_BACKENDS),
        )
        if not any(backends_enabled) or not request.user.is_authenticated:
            return

        if settings.EXTERNAL_AUTH_DEFAULT_GROUPS:
            # Assign default groups to the user
            assign_groups_to_user(request.user, settings.EXTERNAL_AUTH_DEFAULT_GROUPS)

        if settings.EXTERNAL_AUTH_DEFAULT_PERMISSIONS:
            # Assign default object permissions to the user
            assign_permissions_to_user(request.user, settings.EXTERNAL_AUTH_DEFAULT_PERMISSIONS)


class ObjectChangeMiddleware:
    """
    This middleware performs three functions in response to an object being created, updated, or deleted:

        1. Create an ObjectChange to reflect the modification to the object in the changelog.
        2. Enqueue any relevant webhooks.
        3. Increment the metric counter for the event type.

    The post_save and post_delete signals are employed to catch object modifications, however changes are recorded a bit
    differently for each. Objects being saved are cached into thread-local storage for action *after* the response has
    completed. This ensures that serialization of the object is performed only after any related objects (e.g. tags)
    have been created. Conversely, deletions are acted upon immediately, so that the serialized representation of the
    object is recorded before it (and any related objects) are actually deleted from the database.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine the resolved path of the request that initiated the change
        try:
            change_context_detail = resolve(request.path).view_name
        except Resolver404:
            change_context_detail = ""

        # Bypass change logging for health check requests to prevent database connection exhaustion
        if change_context_detail == "health_check:health_check_home":
            response = self.get_response(request)
            return response

        # Process the request with change logging enabled
        with web_request_context(
            request.user,
            context_detail=change_context_detail,
            context=ObjectChangeEventContextChoices.CONTEXT_WEB,
            request=request,
        ):
            response = self.get_response(request)

        return response


class ExceptionHandlingMiddleware:
    """
    Intercept certain exceptions which are likely indicative of installation issues and provide helpful instructions
    to the user.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Don't catch exceptions when in debug mode
        if settings.DEBUG:
            return None

        # Ignore Http404s (defer to Django's built-in 404 handling)
        if isinstance(exception, Http404):
            return None

        # Handle exceptions that occur from REST API requests
        if is_api_request(request):
            # Replicate django_structlog middleware behaviour for this middleware.
            # Without this, stack traces for HTTP 500s from the API are lost.
            # This is because returning something from the `process_exception` handler of a middleware causes
            # the middlewares that are above this middleware not to be called [0].
            # Re-ordering of the middlewares such that the django_structlog middleware is _below_ this middleware
            # also has no effect, this is likely because that middleware does _not_ use `process_exception` but
            # rather a mechanism based off of calling the middleware directly through `__call__`, which is in this
            # case seems to never be called.
            # [0] https://docs.djangoproject.com/en/4.2/topics/http/middleware/#process-exception
            if "django_structlog.middlewares.RequestMiddleware" in settings.MIDDLEWARE:
                log_kwargs = {
                    "code": 500,
                    "request": RequestMiddleware.format_request(request),
                }
                bind_extra_request_failed_metadata.send(
                    sender=self.__class__,
                    request=request,
                    logger=logger,
                    exception=exception,
                    log_kwargs=log_kwargs,
                )
                logger.exception(
                    "request_failed",
                    **log_kwargs,
                )
            return rest_api_server_error(request)

        # Determine the type of exception. If it's a common issue, return a custom error page with instructions.
        custom_template = None
        if isinstance(exception, ProgrammingError):
            custom_template = "exceptions/programming_error.html"
        elif isinstance(exception, ImportError):
            custom_template = "exceptions/import_error.html"
        elif isinstance(exception, PermissionError):
            custom_template = "exceptions/permission_error.html"

        # Return a custom error message, or fall back to Django's default 500 error handling
        if custom_template:
            return server_error(request, template_name=custom_template)

        return None


class UserDefinedTimeZoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if tzname := request.user.get_config("timezone"):
                timezone.activate(ZoneInfo(tzname))
            else:
                timezone.deactivate()
        return self.get_response(request)


class GraphQLOpenTelemetryMiddleware:
    """
    Django middleware that creates an OpenTelemetry span and emits a structured INFO log
    for every request to the /graphql and /api/graphql endpoints.

    Opt-in: this is a no-op pass-through unless ``OTEL_PYTHON_DJANGO_INSTRUMENT`` is enabled,
    matching the rest of the OpenTelemetry feature (disabled by default). This prevents the
    GraphQL query/variables from being logged in deployments that never enabled OTel.

    Span attributes set:
    - ``enduser.id``            - authenticated username
    - ``http.client_ip``        - originating IP (X-Forwarded-For -> X-Real-IP -> REMOTE_ADDR)
    - ``graphql.document``      - full query / mutation / subscription text
    - ``graphql.variables``     - JSON-serialised variables (when present)
    - ``graphql.operation.type``- ``query``, ``mutation``, or ``subscription``
    - ``http.status_code``      - HTTP response status code

    The INFO log additionally includes ``duration_ms``.

    Must be placed after ``ExternalAuthMiddleware`` in MIDDLEWARE so that ``request.user``
    is fully resolved (including remote-auth and SSO/LDAP users) before this runs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.rstrip("/") not in _GRAPHQL_PATHS:
            return self.get_response(request)

        # Opt-in only: when OpenTelemetry is disabled (the default) this middleware is a pass-through.
        # Without this guard it would span and log every GraphQL request, leaking the query and variables
        # into INFO logs in deployments that never enabled OTel.
        if not settings.OTEL_PYTHON_DJANGO_INSTRUMENT:
            return self.get_response(request)

        client_ip = self._get_client_ip(request)
        query, variables = self._parse_graphql_body(request)
        operation_type = self._get_operation_type(query)
        username = getattr(getattr(request, "user", None), "username", None) or "anonymous"

        tracer = trace.get_tracer("nautobot.graphql")
        span_name = f"graphql {operation_type}" if operation_type else "graphql"

        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("enduser.id", username)
            span.set_attribute("http.client_ip", client_ip)
            if query:
                span.set_attribute("graphql.document", query)
            if variables:
                span.set_attribute("graphql.variables", json.dumps(variables))
            if operation_type:
                span.set_attribute("graphql.operation.type", operation_type)

            start = time.monotonic()
            response = self.get_response(request)
            duration_ms = round((time.monotonic() - start) * 1000, 2)

            span.set_attribute("http.status_code", response.status_code)

            logger.info(
                "graphql.request",
                username=username,
                client_ip=client_ip,
                query=query,
                variables=variables,
                duration_ms=duration_ms,
                http_status=response.status_code,
            )

        return response

    @staticmethod
    def _get_client_ip(request):
        """Return the originating client IP, respecting reverse-proxy headers."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            # X-Forwarded-For may be a comma-separated list; the leftmost IP is the client.
            return xff.split(",")[0].strip()
        return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def _parse_graphql_body(request):
        """Return ``(query_string, variables_dict)`` extracted from the POST body."""
        if request.method != "POST":
            return None, None
        try:
            body = request.body
        except Exception:
            return None, None
        content_type = request.content_type or ""
        if "application/json" in content_type:
            try:
                payload = json.loads(body)
                return payload.get("query"), payload.get("variables")
            except (json.JSONDecodeError, ValueError):
                return None, None
        if "application/graphql" in content_type:
            try:
                return body.decode("utf-8"), None
            except UnicodeDecodeError:
                return None, None
        return None, None

    @staticmethod
    def _get_operation_type(query):
        """Return ``query``, ``mutation``, or ``subscription`` from the document, or ``None``."""
        if not query:
            return None
        match = _GRAPHQL_OPERATION_RE.match(query)
        return match.group(1).lower() if match else None
