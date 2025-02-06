"""Django API urlpatterns declaration for nautobot_data_validation_engine app."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot.nautobot_data_validation_engine.api import views

router = OrderedDefaultRouter(view_name="Data Validation Engine")
# add the name of your api endpoint, usually hyphenated model name in plural, e.g. "my-model-classes"
# Regular expression rules
router.register("regex-rules", views.RegularExpressionValidationRuleViewSet)

# Min/max rules
router.register("min-max-rules", views.MinMaxValidationRuleViewSet)

# Required rules
router.register("required-rules", views.RequiredValidationRuleViewSet)

# Unique rules
router.register("unique-rules", views.UniqueValidationRuleViewSet)

# Data Compliance
router.register("data-compliance", views.DataComplianceAPIView)


app_name = "nautobot_data_validation_engine-api"
urlpatterns = router.urls
