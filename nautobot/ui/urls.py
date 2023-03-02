# UI-related API endpoints

from django.conf.urls import include
from django.urls import path

from nautobot.core.api.views import (
    GetMenu,
    GetFilterSetFieldDOMElementAPIView,
    GetFilterSetFieldLookupExpressionChoicesAPIView,
)


core_api_patterns = [
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
ui_api_patterns = [
    # Lookup Expr
    path("core/", include((core_api_patterns, "core-api"))),
    path("get-menu/", GetMenu.as_view(), name="get-menu"),
]
