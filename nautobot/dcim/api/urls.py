from nautobot.core.api.routers import OrderedDefaultRouter
from . import views


router = OrderedDefaultRouter()
router.APIRootView = views.DCIMRootView

# Locations
router.register("location-types", views.LocationTypeViewSet)
router.register("locations", views.LocationViewSet)

# Racks
router.register("rack-groups", views.RackGroupViewSet)
router.register("racks", views.RackViewSet)
router.register("rack-reservations", views.RackReservationViewSet)

# Device types
router.register("manufacturers", views.ManufacturerViewSet)
router.register("device-types", views.DeviceTypeViewSet)

# Device type components
router.register("console-port-templates", views.ConsolePortTemplateViewSet)
router.register("console-server-port-templates", views.ConsoleServerPortTemplateViewSet)
router.register("power-port-templates", views.PowerPortTemplateViewSet)
router.register("power-outlet-templates", views.PowerOutletTemplateViewSet)
router.register("interface-templates", views.InterfaceTemplateViewSet)
router.register("front-port-templates", views.FrontPortTemplateViewSet)
router.register("rear-port-templates", views.RearPortTemplateViewSet)
router.register("device-bay-templates", views.DeviceBayTemplateViewSet)

# Devices
router.register("platforms", views.PlatformViewSet)
router.register("devices", views.DeviceViewSet)

# Device components
router.register("console-ports", views.ConsolePortViewSet)
router.register("console-server-ports", views.ConsoleServerPortViewSet)
router.register("power-ports", views.PowerPortViewSet)
router.register("power-outlets", views.PowerOutletViewSet)
router.register("interfaces", views.InterfaceViewSet)
router.register("front-ports", views.FrontPortViewSet)
router.register("rear-ports", views.RearPortViewSet)
router.register("device-bays", views.DeviceBayViewSet)
router.register("inventory-items", views.InventoryItemViewSet)

# Connections
router.register("console-connections", views.ConsoleConnectionViewSet, basename="consoleconnections")
router.register("power-connections", views.PowerConnectionViewSet, basename="powerconnections")
router.register(
    "interface-connections",
    views.InterfaceConnectionViewSet,
    basename="interfaceconnections",
)

# Cables
router.register("cables", views.CableViewSet)

# Interface Redundancy Group
router.register("interface-redundancy-groups", views.InterfaceRedundancyGroupViewSet)
router.register("interface-redundancy-group-associations", views.InterfaceRedundancyGroupAssociationViewSet)

# Virtual chassis
router.register("virtual-chassis", views.VirtualChassisViewSet)

# Power
router.register("power-panels", views.PowerPanelViewSet)
router.register("power-feeds", views.PowerFeedViewSet)

# Device Redundancy Group
router.register("device-redundancy-groups", views.DeviceRedundancyGroupViewSet)

# Miscellaneous
router.register("connected-device", views.ConnectedDeviceViewSet, basename="connected-device")

app_name = "dcim-api"
urlpatterns = router.urls
