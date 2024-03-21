from collections import OrderedDict
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import APIRootView, DefaultRouter

logger = logging.getLogger(__name__)


class AuthenticatedAPIRootView(APIRootView):
    """
    Extends DRF's base APIRootView class to enforce user authentication.
    """

    permission_classes = [IsAuthenticated]

    name = None
    description = None


class OrderedDefaultRouter(DefaultRouter):
    APIRootView = AuthenticatedAPIRootView

    def __init__(self, *args, view_name=None, view_description=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.view_name = view_name
        if view_name and not view_description:
            view_description = f"{view_name} API root view"
        self.view_description = view_description

        # Extend the list view mappings to support the DELETE operation
        self.routes[0].mapping.update(
            {
                "put": "bulk_update",
                "patch": "bulk_partial_update",
                "delete": "bulk_destroy",
            }
        )

    def get_api_root_view(self, api_urls=None):
        """
        Wrap DRF's DefaultRouter to return an alphabetized list of endpoints.
        """
        api_root_dict = OrderedDict()
        list_name = self.routes[0].name

        for prefix, _viewset, basename in sorted(self.registry, key=lambda x: x[0]):
            api_root_dict[prefix] = list_name.format(basename=basename)

        if issubclass(self.APIRootView, AuthenticatedAPIRootView):
            return self.APIRootView.as_view(
                api_root_dict=api_root_dict, name=self.view_name, description=self.view_description
            )
        # Fallback for the established practice of overriding self.APIRootView with a custom class
        logger.warning(
            "Something has changed an OrderedDefaultRouter's APIRootView attribute to a custom class. "
            "Please verify that class %s implements appropriate authentication controls.",
            self.APIRootView.__name__,
        )
        return self.APIRootView.as_view(api_root_dict=api_root_dict)
