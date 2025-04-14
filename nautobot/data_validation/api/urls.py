"""Django API urlpatterns declaration for data_validation app."""

from nautobot.apps.api import OrderedDefaultRouter
from nautobot.data_validation.api import views

router = OrderedDefaultRouter(view_name="Data Validation Engine")

# Data Compliance
router.register("data-compliance", views.DataComplianceAPIView)
# Min/max rules
router.register("min-max-rules", views.MinMaxValidationRuleViewSet)
# Regular expression rules
router.register("regex-rules", views.RegularExpressionValidationRuleViewSet)
# Required rules
router.register("required-rules", views.RequiredValidationRuleViewSet)
# Unique rules
router.register("unique-rules", views.UniqueValidationRuleViewSet)

app_name = "data_validation-api"
urlpatterns = router.urls
