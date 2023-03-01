from django.conf.urls import include
from django.urls import path

from nautobot.core.api.views import (
    GetFilterSetFieldDOMElementAPIView,
    GetFilterSetFieldLookupExpressionChoicesAPIView,
    GetMenu,
)


# TODO: these should be moved under `api/ui/` for consistency. See #3240.
core_api_patterns = [
    # Lookup Expr
    path(
        "filterset-fields/lookup-choices/",
        GetFilterSetFieldLookupExpressionChoicesAPIView.as_view(),
        name="filtersetfield-list-lookupchoices",
    ),
    path(
        "filterset-fields/lookup-value-dom-element/",
        GetFilterSetFieldDOMElementAPIView.as_view(),
        name="filtersetfield-retrieve-lookupvaluedomelement",
    ),
]

urlpatterns = [
    path("get-menu/", GetMenu.as_view(), name="get-menu"),
    # Core
    path("core/", include((core_api_patterns, "core-api"))),
]
