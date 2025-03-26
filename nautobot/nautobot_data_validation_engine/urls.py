"""Django urlpatterns declaration for nautobot_data_validation_engine app."""

from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.nautobot_data_validation_engine import views

app_name = "nautobot_data_validation_engine"

router = NautobotUIViewSetRouter()
router.register("data-compliance", views.DataComplianceUIViewSet)
router.register("regex-rules", views.RegularExpressionValidationRuleUIViewSet)
router.register("min-max-rules", views.MinMaxValidationRuleUIViewSet)
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
