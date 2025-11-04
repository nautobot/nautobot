"""Django urlpatterns declaration for nautobot_load_balancer_models app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_load_balancer_models import views

app_name = "nautobot_load_balancer_models"
router = NautobotUIViewSetRouter()
router.register("certificate-profiles", views.CertificateProfileUIViewSet)
router.register("health-check-monitors", views.HealthCheckMonitorUIViewSet)
router.register("load-balancer-pool-members", views.LoadBalancerPoolMemberUIViewSet)
router.register("load-balancer-pools", views.LoadBalancerPoolUIViewSet)
router.register("virtual-servers", views.VirtualServerUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_load_balancer_models/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
