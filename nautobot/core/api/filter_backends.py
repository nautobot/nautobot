from django_filters.rest_framework.backends import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from tree_queries.models import TreeNode

from nautobot.core.api.constants import NON_FILTER_QUERY_PARAMS


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

        for non_filter_param in NON_FILTER_QUERY_PARAMS:
            data.pop(non_filter_param, None)

        kwargs["data"] = data
        return kwargs


class NautobotOrderingFilter(OrderingFilter):
    """Custom Ordering Filter backend."""

    def filter_queryset(self, request, queryset, view):
        filtered_queryset = super().filter_queryset(request, queryset, view)
        ordering = self.get_ordering(request, queryset, view)
        if ordering and issubclass(queryset.model, TreeNode):
            filtered_queryset = filtered_queryset.extra(order_by=ordering)
        return filtered_queryset
