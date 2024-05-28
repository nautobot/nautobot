from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Cloud")

# Cloud Accounts
router.register("cloud-accounts", views.CloudAccountViewSet)

app_name = "cloud-api"
urlpatterns = router.urls
