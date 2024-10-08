
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request


class NautobotMetadata(SimpleMetadata):
    """
    Metadata class that emits JSON schema.
    """

    def determine_actions(self, request, view):
        """Generate the actions and return the names of the allowed methods."""
        actions = []
        for method in {"PUT", "POST"} & set(view.allowed_methods):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, "check_permissions"):
                    view.check_permissions(view.request)
                # Test object permissions (if viewing a specific object)
                if method == "PUT" and view.lookup_url_kwarg and hasattr(view, "get_object"):
                    view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                actions.append(method)
            finally:
                view.request = request
        return actions
