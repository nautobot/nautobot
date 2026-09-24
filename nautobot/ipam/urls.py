from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "ipam"

router = NautobotUIViewSetRouter()
router.register("ip-address-ranges", views.IPAddressRangeUIViewSet)
router.register("ip-address-to-interface", views.IPAddressToInterfaceUIViewSet)
router.register("ip-addresses", views.IPAddressUIViewSet)
router.register("namespaces", views.NamespaceUIViewSet)
router.register("prefixes", views.PrefixUIViewSet)
router.register("rirs", views.RIRUIViewSet)
router.register("route-targets", views.RouteTargetUIViewSet)
router.register("services", views.ServiceUIViewSet)
router.register("vlans", views.VLANUIViewSet)
router.register("vlan-groups", views.VLANGroupUIViewSet)
router.register("vrfs", views.VRFUIViewSet)

urlpatterns = []

urlpatterns += router.urls
