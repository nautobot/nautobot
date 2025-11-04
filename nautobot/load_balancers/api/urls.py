"""Django API urlpatterns declaration for nautobot_load_balancer_models app."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_load_balancer_models.api import views

app_name = "nautobot_load_balancer_models-api"
router = OrderedDefaultRouter()
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


urlpatterns = router.urls
