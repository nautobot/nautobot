from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "cloud"
router = NautobotUIViewSetRouter()

router.register("cloud-accounts", views.CloudAccountUIViewSet)
router.register("cloud-networks", views.CloudNetworkUIViewSet)
router.register("cloud-resource-types", views.CloudResourceTypeUIViewSet)
router.register("cloud-services", views.CloudServiceUIViewSet)

urlpatterns = []
urlpatterns += router.urls
