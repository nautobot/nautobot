from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "cloud"
router = NautobotUIViewSetRouter()

router.register("cloud-accounts", views.CloudAccountUIViewSet)

urlpatterns = []
urlpatterns += router.urls
