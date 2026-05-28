"""Django urlpatterns declaration for nautobot_load_balancer_models app."""

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.load_balancers import views

app_name = "load_balancers"

router = NautobotUIViewSetRouter()
router.register("certificate-profiles", views.CertificateProfileUIViewSet)
router.register("health-check-monitors", views.HealthCheckMonitorUIViewSet)
router.register("load-balancer-pool-members", views.LoadBalancerPoolMemberUIViewSet)
router.register("load-balancer-pools", views.LoadBalancerPoolUIViewSet)
router.register("virtual-servers", views.VirtualServerUIViewSet)

urlpatterns = []

urlpatterns += router.urls
