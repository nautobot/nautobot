from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="IPAM")

# Namespaces
router.register("namespaces", views.NamespaceViewSet)

# VRFs
router.register("vrfs", views.VRFViewSet)
router.register("vrf-device-assignments", views.VRFDeviceAssignmentViewSet)
router.register("vrf-prefix-assignments", views.VRFPrefixAssignmentViewSet)

# Route targets
router.register("route-targets", views.RouteTargetViewSet)

# RIRs
router.register("rirs", views.RIRViewSet)

# Prefixes
router.register("prefixes", views.PrefixViewSet)
router.register("prefix-location-assignments", views.PrefixLocationAssignmentViewSet)

# IP addresses
router.register("ip-addresses", views.IPAddressViewSet)

# IP address To interface
router.register("ip-address-to-interface", views.IPAddressToInterfaceViewSet)

# VLANs
router.register("vlan-groups", views.VLANGroupViewSet)
router.register("vlans", views.VLANViewSet)
router.register("vlan-location-assignments", views.VLANLocationAssignmentViewSet)

# Services
router.register("services", views.ServiceViewSet)

app_name = "ipam-api"
urlpatterns = router.urls
