"""Django urlpatterns declaration for nautobot_vpn_models app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_vpn_models import views

app_name = "nautobot_vpn_models"
router = NautobotUIViewSetRouter()
router.register("vpn-profiles", views.VPNProfileUIViewSet)
router.register("vpn-phase-1-policys", views.VPNPhase1PolicyUIViewSet)
router.register("vpn-phase-2-policys", views.VPNPhase2PolicyUIViewSet)
router.register("vpns", views.VPNUIViewSet)
router.register("vpn-tunnels", views.VPNTunnelUIViewSet)
router.register("vpn-tunnel-endpoints", views.VPNTunnelEndpointUIViewSet)

urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_vpn_models/docs/index.html")), name="docs"),
]

urlpatterns += router.urls