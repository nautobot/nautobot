"""Django urlpatterns declaration for data_validation app."""

from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.data_validation import views

app_name = "data_validation"

router = NautobotUIViewSetRouter()
router.register("data-compliance", views.DataComplianceUIViewSet)
router.register("min-max-rules", views.MinMaxValidationRuleUIViewSet)
router.register("regex-rules", views.RegularExpressionValidationRuleUIViewSet)
router.register("required-rules", views.RequiredValidationRuleUIViewSet)
router.register("unique-rules", views.UniqueValidationRuleUIViewSet)

urlpatterns = [
    path(
        "data-compliance/<model>/<uuid:id>/",
        views.DataComplianceObjectView.as_view(),
        name="data-compliance-tab",
    ),
]
urlpatterns += router.urls
