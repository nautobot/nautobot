from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Wireless")

router.register("access-point-groups", views.AccessPointGroupViewSet)
router.register("access-point-group-device-assignments", views.AccessPointGroupDeviceAssignmentViewSet)
router.register("access-point-group-radio-profile-assignments", views.AccessPointGroupRadioProfileAssignmentViewSet)
router.register(
    "access-point-group-wireless-network-assignments", views.AccessPointGroupWirelessNetworkAssignmentViewSet
)
router.register("supported-data-rates", views.SupportedDataRateViewSet)
router.register("radio-profiles", views.RadioProfileViewSet)
router.register("wireless-networks", views.WirelessNetworkViewSet)

app_name = "wireless-api"
urlpatterns = router.urls
