"""Django urlpatterns declaration for data_validation app."""

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.data_validation import views

app_name = "data_validation"

router = NautobotUIViewSetRouter()
router.register("data-compliance", views.DataComplianceUIViewSet)
router.register("min-max-rules", views.MinMaxValidationRuleUIViewSet)
router.register("regex-rules", views.RegularExpressionValidationRuleUIViewSet)
router.register("required-rules", views.RequiredValidationRuleUIViewSet)
router.register("unique-rules", views.UniqueValidationRuleUIViewSet)

urlpatterns = router.urls
