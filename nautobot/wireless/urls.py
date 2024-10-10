from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "wireless"
router = NautobotUIViewSetRouter()

router.register("access-point-groups", views.AccessPointGroupUIViewSet)
router.register("radio-profiles", views.RadioProfileUIViewSet)
router.register("supported-data-rates", views.SupportedDataRateUIViewSet)
router.register("wireless-networks", views.WirelessNetworkUIViewSet)

urlpatterns = []
urlpatterns += router.urls
