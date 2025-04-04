from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "tenancy"
router = NautobotUIViewSetRouter()
router.register("tenant-groups", views.TenantGroupUIViewSet)
router.register("tenants", views.TenantUIViewSet)

urlpatterns = []
urlpatterns += router.urls
