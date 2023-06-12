from django_filters.rest_framework.backends import DjangoFilterBackend


class NautobotFilterBackend(DjangoFilterBackend):
    """Custom filtering backend for use with django-rest-framework and django-filters."""

    def get_filterset_kwargs(self, request, queryset, view):
        """
        Get the kwargs that should be passed through when constructing a FilterSet corresponding to a given request.

        This extends the base DjangoFilterBackend method to explicitly exclude query parameters that we know to be
        non-filterset parameters.
        """
        kwargs = super().get_filterset_kwargs(request, queryset, view)
        # The default 'data' is a reference to request.GET, which is immutable; copies of this data are mutable
        data = kwargs["data"].copy()

        for non_filter_param in (
            "api_version",  # used to select the Nautobot API version
            "depth",  # nested levels of the serializers default to depth=0
            "format",  # "json" or "api", used in the interactive HTML REST API views
            "include",  # used to include computed fields, relationships, config-contexts, etc. (excluded by default)
            "limit",  # pagination
            "offset",  # pagination
            "sort",  # sorting of results
        ):
            data.pop(non_filter_param, None)

        kwargs["data"] = data
        return kwargs
