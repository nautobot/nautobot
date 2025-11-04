"""Django API urlpatterns declaration for nautobot_load_balancer_models app."""

from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Load Balancers")

router.register("certificate-profiles", views.CertificateProfileViewSet)
router.register("health-check-monitors", views.HealthCheckMonitorViewSet)
router.register("load-balancer-pool-members", views.LoadBalancerPoolMemberViewSet)
router.register(
    "load-balancer-pool-member-certificate-profile-assignments",
    views.LoadBalancerPoolMemberCertificateProfileAssignmentViewSet,
)
router.register("load-balancer-pools", views.LoadBalancerPoolViewSet)
router.register("virtual-servers", views.VirtualServerViewSet)
router.register(
    "virtual-server-certificate-profile-assignments", views.VirtualServerCertificateProfileAssignmentViewSet
)

app_name = "load_balancers-api"
urlpatterns = router.urls
