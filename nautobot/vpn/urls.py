from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "vpn"
router = NautobotUIViewSetRouter()

router.register("vpn-profiles", views.VPNProfileUIViewSet)
router.register("vpn-phase-1-policies", views.VPNPhase1PolicyUIViewSet)
router.register("vpn-phase-2-policies", views.VPNPhase2PolicyUIViewSet)
router.register("vpns", views.VPNUIViewSet)
router.register("vpn-tunnels", views.VPNTunnelUIViewSet)
router.register("vpn-tunnel-endpoints", views.VPNTunnelEndpointUIViewSet)

urlpatterns = []
urlpatterns += router.urls
