from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "cloud"
router = NautobotUIViewSetRouter()

router.register("cloud-accounts", views.CloudAccountUIViewSet)
router.register("cloud-types", views.CloudTypeUIViewSet)

urlpatterns = []
urlpatterns += router.urls
