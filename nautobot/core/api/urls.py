from django.urls import path

from nautobot.core.api.views.dynamic_groups import DynamicGroupViewSet, DynamicGroupMembershipViewSet
from . import routers, views

router = routers.OrderedDefaultRouter()
# router.APIRootView = views.CoreRootView

# Dynamic Groups
router.register("dynamic-groups", DynamicGroupViewSet)
router.register("dynamic-group-memberships", DynamicGroupMembershipViewSet)

core_api_patterns = [
    # Lookup Expr
    path(
        "filterset-fields/lookup-choices/",
        views.GetFilterSetFieldLookupExpressionChoicesAPIView.as_view(),
        name="filtersetfield-list-lookupchoices",
    ),
    path(
        "filterset-fields/lookup-value-dom-element/",
        views.GetFilterSetFieldDOMElementAPIView.as_view(),
        name="filtersetfield-retrieve-lookupvaluedomelement",
    ),
]


app_name = "core-api"
urlpatterns = router.urls + core_api_patterns
