"""Django API urlpatterns declaration for the vpn models."""

from nautobot.apps.api import OrderedDefaultRouter

from . import views

app_name = "vpn-api"
router = OrderedDefaultRouter()
# add the name of your api endpoint, usually hyphenated model name in plural, e.g. "my-model-classes"
router.register("vpn-profiles", views.VPNProfileViewSet)
router.register("vpn-phase-1-policies", views.VPNPhase1PolicyViewSet)
router.register("vpn-phase-2-policies", views.VPNPhase2PolicyViewSet)
router.register("vpn-profile-phase-1-policy-assignments", views.VPNProfilePhase1PolicyAssignmentViewSet)
router.register("vpn-profile-phase-2-policy-assignments", views.VPNProfilePhase2PolicyAssignmentViewSet)
router.register("vpns", views.VPNViewSet)
router.register("vpn-tunnels", views.VPNTunnelViewSet)
router.register("vpn-tunnel-endpoints", views.VPNTunnelEndpointViewSet)

urlpatterns = router.urls
