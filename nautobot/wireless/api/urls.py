from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Wireless")

router.register(
    "controller-managed-device-group-radio-profile-assignments",
    views.ControllerManagedDeviceGroupRadioProfileAssignmentViewSet,
)
router.register(
    "controller-managed-device-group-wireless-network-assignments",
    views.ControllerManagedDeviceGroupWirelessNetworkAssignmentViewSet,
)
router.register("supported-data-rates", views.SupportedDataRateViewSet)
router.register("radio-profiles", views.RadioProfileViewSet)
router.register("wireless-networks", views.WirelessNetworkViewSet)

app_name = "wireless-api"
urlpatterns = router.urls
