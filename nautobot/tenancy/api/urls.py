from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Tenancy")

# Tenants
router.register("tenant-groups", views.TenantGroupViewSet)
router.register("tenants", views.TenantViewSet)

app_name = "tenancy-api"
urlpatterns = router.urls
