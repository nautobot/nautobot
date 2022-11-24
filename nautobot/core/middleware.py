from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware as RemoteUserMiddleware_
from django.db import ProgrammingError
from django.http import Http404
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.utils.deprecation import MiddlewareMixin

from nautobot.core.views import server_error
from nautobot.extras.context_managers import change_logging, WebChangeContext
from nautobot.utilities.api import is_api_request, rest_api_server_error
from nautobot.core.settings_funcs import (
    sso_auth_enabled,
    remote_auth_enabled,
    ldap_auth_enabled,
)
from nautobot.core.authentication import (
    assign_groups_to_user,
    assign_permissions_to_user,
)


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

        # Pass request rather than user here because at this point in the request handling logic, request.user may not have been set yet
        change_context = WebChangeContext(request=request, context_detail=change_context_detail)

        # Process the request with change logging enabled
        with change_logging(change_context):
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
