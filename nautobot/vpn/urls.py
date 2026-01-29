from nautobot.apps.urls import NautobotUIViewSetRouter

from . import views

app_name = "vpn"
router = NautobotUIViewSetRouter()

router.register("vpn-profiles", views.VPNProfileUIViewSet)
router.register("vpn-phase-1-policies", views.VPNPhase1PolicyUIViewSet)
router.register("vpn-phase-2-policies", views.VPNPhase2PolicyUIViewSet)
router.register("vpns", views.VPNUIViewSet)
router.register("vpn-tunnels", views.VPNTunnelUIViewSet)
router.register("vpn-tunnel-endpoints", views.VPNTunnelEndpointUIViewSet)
router.register("l2vpns", views.L2VPNUIViewSet)
router.register("l2vpn-terminations", views.L2VPNTerminationUIViewSet)



urlpatterns = []
urlpatterns += router.urls


