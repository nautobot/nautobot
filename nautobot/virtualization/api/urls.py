from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Virtualization")

# Clusters
router.register("cluster-types", views.ClusterTypeViewSet)
router.register("cluster-groups", views.ClusterGroupViewSet)
router.register("clusters", views.ClusterViewSet)

# VirtualMachines
router.register("virtual-machines", views.VirtualMachineViewSet)
router.register("interfaces", views.VMInterfaceViewSet)

app_name = "virtualization-api"
urlpatterns = router.urls
