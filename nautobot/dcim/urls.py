from django.urls import path
from django.views.generic.base import RedirectView

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ImageAttachmentEditView, ObjectChangeLogView, ObjectNotesView
from nautobot.ipam.views import ServiceEditView

from . import views
from .models import (
    Cable,
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceBay,
    FrontPort,
    Interface,
    InventoryItem,
    Location,
    PowerFeed,
    PowerOutlet,
    PowerPort,
    Rack,
    RearPort,
)

app_name = "dcim"

router = NautobotUIViewSetRouter()
router.register("controller-managed-device-groups", views.ControllerManagedDeviceGroupUIViewSet)
router.register("controllers", views.ControllerUIViewSet)
router.register("device-families", views.DeviceFamilyUIViewSet)
router.register("device-redundancy-groups", views.DeviceRedundancyGroupUIViewSet)
router.register("device-types", views.DeviceTypeUIViewSet)
router.register("interface-redundancy-groups", views.InterfaceRedundancyGroupUIViewSet)
router.register("interface-redundancy-groups-associations", views.InterfaceRedundancyGroupAssociationUIViewSet)
router.register("locations", views.LocationUIViewSet)
router.register("location-types", views.LocationTypeUIViewSet)
router.register("manufacturers", views.ManufacturerUIViewSet)
router.register("module-bay-templates", views.ModuleBayTemplateUIViewSet)
router.register("module-bays", views.ModuleBayUIViewSet)
router.register("module-families", views.ModuleFamilyUIViewSet)
router.register("module-types", views.ModuleTypeUIViewSet)
router.register("modules", views.ModuleUIViewSet)
router.register("platforms", views.PlatformUIViewSet)
router.register("power-feeds", views.PowerFeedUIViewSet)
router.register("power-panels", views.PowerPanelUIViewSet)
router.register("racks", views.RackUIViewSet)
router.register("rack-groups", views.RackGroupUIViewSet)
router.register("rack-reservations", views.RackReservationUIViewSet)
router.register("software-image-files", views.SoftwareImageFileUIViewSet)
router.register("software-versions", views.SoftwareVersionUIViewSet)
router.register("virtual-chassis", views.VirtualChassisUIViewSet)
router.register("virtual-device-contexts", views.VirtualDeviceContextUIViewSet)

urlpatterns = [
    # Locations
    path(
        "locations/<uuid:pk>/migrate-data-to-contact/",
        views.MigrateLocationDataToContactView.as_view(),
        name="location_migrate_data_to_contact",
    ),
    path(
        "locations/<uuid:object_id>/images/add/",
        ImageAttachmentEditView.as_view(),
        name="location_add_image",
        kwargs={"model": Location},
    ),
    # Racks
    path(
        "rack-elevations/",
        views.RackElevationListView.as_view(),
        name="rack_elevation_list",
    ),
    path(
        "racks/<uuid:object_id>/images/add/",
        ImageAttachmentEditView.as_view(),
        name="rack_add_image",
        kwargs={"model": Rack},
    ),
    # Device types
    path(
        "device-types/import/",
        views.DeviceTypeImportView.as_view(),
        name="devicetype_import",
    ),
    # Console port templates
    path(
        "console-port-templates/add/",
        views.ConsolePortTemplateCreateView.as_view(),
        name="consoleporttemplate_add",
    ),
    path(
        "console-port-templates/edit/",
        views.ConsolePortTemplateBulkEditView.as_view(),
        name="consoleporttemplate_bulk_edit",
    ),
    path(
        "console-port-templates/rename/",
        views.ConsolePortTemplateBulkRenameView.as_view(),
        name="consoleporttemplate_bulk_rename",
    ),
    path(
        "console-port-templates/delete/",
        views.ConsolePortTemplateBulkDeleteView.as_view(),
        name="consoleporttemplate_bulk_delete",
    ),
    path(
        "console-port-templates/<uuid:pk>/edit/",
        views.ConsolePortTemplateEditView.as_view(),
        name="consoleporttemplate_edit",
    ),
    path(
        "console-port-templates/<uuid:pk>/delete/",
        views.ConsolePortTemplateDeleteView.as_view(),
        name="consoleporttemplate_delete",
    ),
    # Console server port templates
    path(
        "console-server-port-templates/add/",
        views.ConsoleServerPortTemplateCreateView.as_view(),
        name="consoleserverporttemplate_add",
    ),
    path(
        "console-server-port-templates/edit/",
        views.ConsoleServerPortTemplateBulkEditView.as_view(),
        name="consoleserverporttemplate_bulk_edit",
    ),
    path(
        "console-server-port-templates/rename/",
        views.ConsoleServerPortTemplateBulkRenameView.as_view(),
        name="consoleserverporttemplate_bulk_rename",
    ),
    path(
        "console-server-port-templates/delete/",
        views.ConsoleServerPortTemplateBulkDeleteView.as_view(),
        name="consoleserverporttemplate_bulk_delete",
    ),
    path(
        "console-server-port-templates/<uuid:pk>/edit/",
        views.ConsoleServerPortTemplateEditView.as_view(),
        name="consoleserverporttemplate_edit",
    ),
    path(
        "console-server-port-templates/<uuid:pk>/delete/",
        views.ConsoleServerPortTemplateDeleteView.as_view(),
        name="consoleserverporttemplate_delete",
    ),
    # Power port templates
    path(
        "power-port-templates/add/",
        views.PowerPortTemplateCreateView.as_view(),
        name="powerporttemplate_add",
    ),
    path(
        "power-port-templates/edit/",
        views.PowerPortTemplateBulkEditView.as_view(),
        name="powerporttemplate_bulk_edit",
    ),
    path(
        "power-port-templates/rename/",
        views.PowerPortTemplateBulkRenameView.as_view(),
        name="powerporttemplate_bulk_rename",
    ),
    path(
        "power-port-templates/delete/",
        views.PowerPortTemplateBulkDeleteView.as_view(),
        name="powerporttemplate_bulk_delete",
    ),
    path(
        "power-port-templates/<uuid:pk>/edit/",
        views.PowerPortTemplateEditView.as_view(),
        name="powerporttemplate_edit",
    ),
    path(
        "power-port-templates/<uuid:pk>/delete/",
        views.PowerPortTemplateDeleteView.as_view(),
        name="powerporttemplate_delete",
    ),
    # Power outlet templates
    path(
        "power-outlet-templates/add/",
        views.PowerOutletTemplateCreateView.as_view(),
        name="poweroutlettemplate_add",
    ),
    path(
        "power-outlet-templates/edit/",
        views.PowerOutletTemplateBulkEditView.as_view(),
        name="poweroutlettemplate_bulk_edit",
    ),
    path(
        "power-outlet-templates/rename/",
        views.PowerOutletTemplateBulkRenameView.as_view(),
        name="poweroutlettemplate_bulk_rename",
    ),
    path(
        "power-outlet-templates/delete/",
        views.PowerOutletTemplateBulkDeleteView.as_view(),
        name="poweroutlettemplate_bulk_delete",
    ),
    path(
        "power-outlet-templates/<uuid:pk>/edit/",
        views.PowerOutletTemplateEditView.as_view(),
        name="poweroutlettemplate_edit",
    ),
    path(
        "power-outlet-templates/<uuid:pk>/delete/",
        views.PowerOutletTemplateDeleteView.as_view(),
        name="poweroutlettemplate_delete",
    ),
    # Interface templates
    path(
        "interface-templates/add/",
        views.InterfaceTemplateCreateView.as_view(),
        name="interfacetemplate_add",
    ),
    path(
        "interface-templates/edit/",
        views.InterfaceTemplateBulkEditView.as_view(),
        name="interfacetemplate_bulk_edit",
    ),
    path(
        "interface-templates/rename/",
        views.InterfaceTemplateBulkRenameView.as_view(),
        name="interfacetemplate_bulk_rename",
    ),
    path(
        "interface-templates/delete/",
        views.InterfaceTemplateBulkDeleteView.as_view(),
        name="interfacetemplate_bulk_delete",
    ),
    path(
        "interface-templates/<uuid:pk>/edit/",
        views.InterfaceTemplateEditView.as_view(),
        name="interfacetemplate_edit",
    ),
    path(
        "interface-templates/<uuid:pk>/delete/",
        views.InterfaceTemplateDeleteView.as_view(),
        name="interfacetemplate_delete",
    ),
    # Front port templates
    path(
        "front-port-templates/add/",
        views.FrontPortTemplateCreateView.as_view(),
        name="frontporttemplate_add",
    ),
    path(
        "front-port-templates/edit/",
        views.FrontPortTemplateBulkEditView.as_view(),
        name="frontporttemplate_bulk_edit",
    ),
    path(
        "front-port-templates/rename/",
        views.FrontPortTemplateBulkRenameView.as_view(),
        name="frontporttemplate_bulk_rename",
    ),
    path(
        "front-port-templates/delete/",
        views.FrontPortTemplateBulkDeleteView.as_view(),
        name="frontporttemplate_bulk_delete",
    ),
    path(
        "front-port-templates/<uuid:pk>/edit/",
        views.FrontPortTemplateEditView.as_view(),
        name="frontporttemplate_edit",
    ),
    path(
        "front-port-templates/<uuid:pk>/delete/",
        views.FrontPortTemplateDeleteView.as_view(),
        name="frontporttemplate_delete",
    ),
    # Rear port templates
    path(
        "rear-port-templates/add/",
        views.RearPortTemplateCreateView.as_view(),
        name="rearporttemplate_add",
    ),
    path(
        "rear-port-templates/edit/",
        views.RearPortTemplateBulkEditView.as_view(),
        name="rearporttemplate_bulk_edit",
    ),
    path(
        "rear-port-templates/rename/",
        views.RearPortTemplateBulkRenameView.as_view(),
        name="rearporttemplate_bulk_rename",
    ),
    path(
        "rear-port-templates/delete/",
        views.RearPortTemplateBulkDeleteView.as_view(),
        name="rearporttemplate_bulk_delete",
    ),
    path(
        "rear-port-templates/<uuid:pk>/edit/",
        views.RearPortTemplateEditView.as_view(),
        name="rearporttemplate_edit",
    ),
    path(
        "rear-port-templates/<uuid:pk>/delete/",
        views.RearPortTemplateDeleteView.as_view(),
        name="rearporttemplate_delete",
    ),
    # Device bay templates
    path(
        "device-bay-templates/add/",
        views.DeviceBayTemplateCreateView.as_view(),
        name="devicebaytemplate_add",
    ),
    path(
        "device-bay-templates/edit/",
        views.DeviceBayTemplateBulkEditView.as_view(),
        name="devicebaytemplate_bulk_edit",
    ),
    path(
        "device-bay-templates/rename/",
        views.DeviceBayTemplateBulkRenameView.as_view(),
        name="devicebaytemplate_bulk_rename",
    ),
    path(
        "device-bay-templates/delete/",
        views.DeviceBayTemplateBulkDeleteView.as_view(),
        name="devicebaytemplate_bulk_delete",
    ),
    path(
        "device-bay-templates/<uuid:pk>/edit/",
        views.DeviceBayTemplateEditView.as_view(),
        name="devicebaytemplate_edit",
    ),
    path(
        "device-bay-templates/<uuid:pk>/delete/",
        views.DeviceBayTemplateDeleteView.as_view(),
        name="devicebaytemplate_delete",
    ),
    # Devices
    path("devices/", views.DeviceListView.as_view(), name="device_list"),
    path("devices/add/", views.DeviceEditView.as_view(), name="device_add"),
    path("devices/import/", views.DeviceBulkImportView.as_view(), name="device_import"),  # 3.0 TODO: remove, unused
    path("devices/edit/", views.DeviceBulkEditView.as_view(), name="device_bulk_edit"),
    path(
        "devices/delete/",
        views.DeviceBulkDeleteView.as_view(),
        name="device_bulk_delete",
    ),
    path("devices/<uuid:pk>/", views.DeviceView.as_view(), name="device"),
    path("devices/<uuid:pk>/edit/", views.DeviceEditView.as_view(), name="device_edit"),
    path(
        "devices/<uuid:pk>/delete/",
        views.DeviceDeleteView.as_view(),
        name="device_delete",
    ),
    path(
        "devices/<uuid:pk>/console-ports/",
        views.DeviceConsolePortsView.as_view(),
        name="device_consoleports",
    ),
    path(
        "devices/<uuid:pk>/console-ports/add/",
        RedirectView.as_view(
            url="/dcim/console-ports/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/console-ports/"
        ),
        name="device_consoleports_add",
    ),
    path(
        "devices/<uuid:pk>/console-server-ports/",
        views.DeviceConsoleServerPortsView.as_view(),
        name="device_consoleserverports",
    ),
    path(
        "devices/<uuid:pk>/console-server-ports/add/",
        RedirectView.as_view(
            url="/dcim/console-server-ports/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/console-server-ports/"
        ),
        name="device_consoleserverports_add",
    ),
    path(
        "devices/<uuid:pk>/power-ports/",
        views.DevicePowerPortsView.as_view(),
        name="device_powerports",
    ),
    path(
        "devices/<uuid:pk>/power-ports/add/",
        RedirectView.as_view(url="/dcim/power-ports/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/power-ports/"),
        name="device_powerports_add",
    ),
    path(
        "devices/<uuid:pk>/power-outlets/",
        views.DevicePowerOutletsView.as_view(),
        name="device_poweroutlets",
    ),
    path(
        "devices/<uuid:pk>/power-outlets/add/",
        RedirectView.as_view(
            url="/dcim/power-outlets/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/power-outlets/"
        ),
        name="device_poweroutlets_add",
    ),
    path(
        "devices/<uuid:pk>/interfaces/",
        views.DeviceInterfacesView.as_view(),
        name="device_interfaces",
    ),
    path(
        "devices/<uuid:pk>/interfaces/add/",
        RedirectView.as_view(url="/dcim/interfaces/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/interfaces/"),
        name="device_interfaces_add",
    ),
    path(
        "devices/<uuid:pk>/front-ports/",
        views.DeviceFrontPortsView.as_view(),
        name="device_frontports",
    ),
    path(
        "devices/<uuid:pk>/front-ports/add/",
        RedirectView.as_view(url="/dcim/front-ports/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/front-ports/"),
        name="device_frontports_add",
    ),
    path(
        "devices/<uuid:pk>/rear-ports/",
        views.DeviceRearPortsView.as_view(),
        name="device_rearports",
    ),
    path(
        "devices/<uuid:pk>/rear-ports/add/",
        RedirectView.as_view(url="/dcim/rear-ports/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/rear-ports/"),
        name="device_rearports_add",
    ),
    path(
        "devices/<uuid:pk>/device-bays/",
        views.DeviceDeviceBaysView.as_view(),
        name="device_devicebays",
    ),
    path(
        "devices/<uuid:pk>/device-bays/add/",
        RedirectView.as_view(url="/dcim/device-bays/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/device-bays/"),
        name="device_devicebays_add",
    ),
    path(
        "devices/<uuid:pk>/module-bays/",
        views.DeviceModuleBaysView.as_view(),
        name="device_modulebays",
    ),
    path(
        "devices/<uuid:pk>/module-bays/add/",
        RedirectView.as_view(
            url="/dcim/module-bays/add/?parent_device=%(pk)s&return_url=/dcim/devices/%(pk)s/module-bays/"
        ),
        name="device_modulebays_add",
    ),
    path(
        "devices/<uuid:pk>/inventory/",
        views.DeviceInventoryView.as_view(),
        name="device_inventory",
    ),
    path(
        "devices/<uuid:pk>/config-context/",
        views.DeviceConfigContextView.as_view(),
        name="device_configcontext",
    ),
    path(
        "devices/<uuid:pk>/changelog/",
        views.DeviceChangeLogView.as_view(),
        name="device_changelog",
        kwargs={"model": Device},
    ),
    path(
        "devices/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="device_notes",
        kwargs={"model": Device},
    ),
    path(
        "devices/<uuid:pk>/dynamic-groups/",
        views.DeviceDynamicGroupsView.as_view(),
        name="device_dynamicgroups",
        kwargs={"model": Device},
    ),
    path(
        "devices/<uuid:pk>/status/",
        views.DeviceStatusView.as_view(),
        name="device_status",
    ),
    path(
        "devices/<uuid:pk>/lldp-neighbors/",
        views.DeviceLLDPNeighborsView.as_view(),
        name="device_lldp_neighbors",
    ),
    path(
        "devices/<uuid:pk>/config/",
        views.DeviceConfigView.as_view(),
        name="device_config",
    ),
    path(
        "devices/<uuid:device>/services/assign/",
        ServiceEditView.as_view(),
        name="device_service_assign",
    ),
    path(
        "devices/<uuid:object_id>/images/add/",
        ImageAttachmentEditView.as_view(),
        name="device_add_image",
        kwargs={"model": Device},
    ),
    path(
        "devices/<uuid:pk>/wireless/",
        views.DeviceWirelessView.as_view(),
        name="device_wireless",
    ),
    # Console ports
    path("console-ports/", views.ConsolePortListView.as_view(), name="consoleport_list"),
    path(
        "console-ports/add/",
        views.ConsolePortCreateView.as_view(),
        name="consoleport_add",
    ),
    path(
        "console-ports/import/",
        views.ConsolePortBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="consoleport_import",
    ),
    path(
        "console-ports/edit/",
        views.ConsolePortBulkEditView.as_view(),
        name="consoleport_bulk_edit",
    ),
    path(
        "console-ports/rename/",
        views.ConsolePortBulkRenameView.as_view(),
        name="consoleport_bulk_rename",
    ),
    path(
        "console-ports/disconnect/",
        views.ConsolePortBulkDisconnectView.as_view(),
        name="consoleport_bulk_disconnect",
    ),
    path(
        "console-ports/delete/",
        views.ConsolePortBulkDeleteView.as_view(),
        name="consoleport_bulk_delete",
    ),
    path("console-ports/<uuid:pk>/", views.ConsolePortView.as_view(), name="consoleport"),
    path(
        "console-ports/<uuid:pk>/edit/",
        views.ConsolePortEditView.as_view(),
        name="consoleport_edit",
    ),
    path(
        "console-ports/<uuid:pk>/delete/",
        views.ConsolePortDeleteView.as_view(),
        name="consoleport_delete",
    ),
    path(
        "console-ports/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="consoleport_changelog",
        kwargs={"model": ConsolePort},
    ),
    path(
        "console-ports/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="consoleport_notes",
        kwargs={"model": ConsolePort},
    ),
    path(
        "console-ports/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="consoleport_trace",
        kwargs={"model": ConsolePort},
    ),
    path(
        "console-ports/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="consoleport_connect",
        kwargs={"termination_a_type": ConsolePort},
    ),
    path(
        "devices/console-ports/add/",
        views.DeviceBulkAddConsolePortView.as_view(),
        name="device_bulk_add_consoleport",
    ),
    # Console server ports
    path(
        "console-server-ports/",
        views.ConsoleServerPortListView.as_view(),
        name="consoleserverport_list",
    ),
    path(
        "console-server-ports/add/",
        views.ConsoleServerPortCreateView.as_view(),
        name="consoleserverport_add",
    ),
    path(
        "console-server-ports/import/",
        views.ConsoleServerPortBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="consoleserverport_import",
    ),
    path(
        "console-server-ports/edit/",
        views.ConsoleServerPortBulkEditView.as_view(),
        name="consoleserverport_bulk_edit",
    ),
    path(
        "console-server-ports/rename/",
        views.ConsoleServerPortBulkRenameView.as_view(),
        name="consoleserverport_bulk_rename",
    ),
    path(
        "console-server-ports/disconnect/",
        views.ConsoleServerPortBulkDisconnectView.as_view(),
        name="consoleserverport_bulk_disconnect",
    ),
    path(
        "console-server-ports/delete/",
        views.ConsoleServerPortBulkDeleteView.as_view(),
        name="consoleserverport_bulk_delete",
    ),
    path(
        "console-server-ports/<uuid:pk>/",
        views.ConsoleServerPortView.as_view(),
        name="consoleserverport",
    ),
    path(
        "console-server-ports/<uuid:pk>/edit/",
        views.ConsoleServerPortEditView.as_view(),
        name="consoleserverport_edit",
    ),
    path(
        "console-server-ports/<uuid:pk>/delete/",
        views.ConsoleServerPortDeleteView.as_view(),
        name="consoleserverport_delete",
    ),
    path(
        "console-server-ports/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="consoleserverport_changelog",
        kwargs={"model": ConsoleServerPort},
    ),
    path(
        "console-server-ports/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="consoleserverport_notes",
        kwargs={"model": ConsoleServerPort},
    ),
    path(
        "console-server-ports/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="consoleserverport_trace",
        kwargs={"model": ConsoleServerPort},
    ),
    path(
        "console-server-ports/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="consoleserverport_connect",
        kwargs={"termination_a_type": ConsoleServerPort},
    ),
    path(
        "devices/console-server-ports/add/",
        views.DeviceBulkAddConsoleServerPortView.as_view(),
        name="device_bulk_add_consoleserverport",
    ),
    # Power ports
    path("power-ports/", views.PowerPortListView.as_view(), name="powerport_list"),
    path("power-ports/add/", views.PowerPortCreateView.as_view(), name="powerport_add"),
    path(
        "power-ports/import/",
        views.PowerPortBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="powerport_import",
    ),
    path(
        "power-ports/edit/",
        views.PowerPortBulkEditView.as_view(),
        name="powerport_bulk_edit",
    ),
    path(
        "power-ports/rename/",
        views.PowerPortBulkRenameView.as_view(),
        name="powerport_bulk_rename",
    ),
    path(
        "power-ports/disconnect/",
        views.PowerPortBulkDisconnectView.as_view(),
        name="powerport_bulk_disconnect",
    ),
    path(
        "power-ports/delete/",
        views.PowerPortBulkDeleteView.as_view(),
        name="powerport_bulk_delete",
    ),
    path("power-ports/<uuid:pk>/", views.PowerPortView.as_view(), name="powerport"),
    path(
        "power-ports/<uuid:pk>/edit/",
        views.PowerPortEditView.as_view(),
        name="powerport_edit",
    ),
    path(
        "power-ports/<uuid:pk>/delete/",
        views.PowerPortDeleteView.as_view(),
        name="powerport_delete",
    ),
    path(
        "power-ports/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="powerport_changelog",
        kwargs={"model": PowerPort},
    ),
    path(
        "power-ports/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="powerport_notes",
        kwargs={"model": PowerPort},
    ),
    path(
        "power-ports/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="powerport_trace",
        kwargs={"model": PowerPort},
    ),
    path(
        "power-ports/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="powerport_connect",
        kwargs={"termination_a_type": PowerPort},
    ),
    path(
        "devices/power-ports/add/",
        views.DeviceBulkAddPowerPortView.as_view(),
        name="device_bulk_add_powerport",
    ),
    # Power outlets
    path("power-outlets/", views.PowerOutletListView.as_view(), name="poweroutlet_list"),
    path(
        "power-outlets/add/",
        views.PowerOutletCreateView.as_view(),
        name="poweroutlet_add",
    ),
    path(
        "power-outlets/import/",
        views.PowerOutletBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="poweroutlet_import",
    ),
    path(
        "power-outlets/edit/",
        views.PowerOutletBulkEditView.as_view(),
        name="poweroutlet_bulk_edit",
    ),
    path(
        "power-outlets/rename/",
        views.PowerOutletBulkRenameView.as_view(),
        name="poweroutlet_bulk_rename",
    ),
    path(
        "power-outlets/disconnect/",
        views.PowerOutletBulkDisconnectView.as_view(),
        name="poweroutlet_bulk_disconnect",
    ),
    path(
        "power-outlets/delete/",
        views.PowerOutletBulkDeleteView.as_view(),
        name="poweroutlet_bulk_delete",
    ),
    path("power-outlets/<uuid:pk>/", views.PowerOutletView.as_view(), name="poweroutlet"),
    path(
        "power-outlets/<uuid:pk>/edit/",
        views.PowerOutletEditView.as_view(),
        name="poweroutlet_edit",
    ),
    path(
        "power-outlets/<uuid:pk>/delete/",
        views.PowerOutletDeleteView.as_view(),
        name="poweroutlet_delete",
    ),
    path(
        "power-outlets/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="poweroutlet_changelog",
        kwargs={"model": PowerOutlet},
    ),
    path(
        "power-outlets/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="poweroutlet_notes",
        kwargs={"model": PowerOutlet},
    ),
    path(
        "power-outlets/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="poweroutlet_trace",
        kwargs={"model": PowerOutlet},
    ),
    path(
        "power-outlets/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="poweroutlet_connect",
        kwargs={"termination_a_type": PowerOutlet},
    ),
    path(
        "devices/power-outlets/add/",
        views.DeviceBulkAddPowerOutletView.as_view(),
        name="device_bulk_add_poweroutlet",
    ),
    # Interfaces
    path("interfaces/", views.InterfaceListView.as_view(), name="interface_list"),
    path("interfaces/add/", views.InterfaceCreateView.as_view(), name="interface_add"),
    path(
        "interfaces/import/",
        views.InterfaceBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="interface_import",
    ),
    path(
        "interfaces/edit/",
        views.InterfaceBulkEditView.as_view(),
        name="interface_bulk_edit",
    ),
    path(
        "interfaces/rename/",
        views.InterfaceBulkRenameView.as_view(),
        name="interface_bulk_rename",
    ),
    path(
        "interfaces/disconnect/",
        views.InterfaceBulkDisconnectView.as_view(),
        name="interface_bulk_disconnect",
    ),
    path(
        "interfaces/delete/",
        views.InterfaceBulkDeleteView.as_view(),
        name="interface_bulk_delete",
    ),
    path("interfaces/<uuid:pk>/", views.InterfaceView.as_view(), name="interface"),
    path(
        "interfaces/<uuid:pk>/edit/",
        views.InterfaceEditView.as_view(),
        name="interface_edit",
    ),
    path(
        "interfaces/<uuid:pk>/delete/",
        views.InterfaceDeleteView.as_view(),
        name="interface_delete",
    ),
    path(
        "interfaces/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="interface_changelog",
        kwargs={"model": Interface},
    ),
    path(
        "interfaces/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="interface_notes",
        kwargs={"model": Interface},
    ),
    path(
        "interfaces/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="interface_trace",
        kwargs={"model": Interface},
    ),
    path(
        "interfaces/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="interface_connect",
        kwargs={"termination_a_type": Interface},
    ),
    path(
        "devices/interfaces/add/",
        views.DeviceBulkAddInterfaceView.as_view(),
        name="device_bulk_add_interface",
    ),
    # Front ports
    path("front-ports/", views.FrontPortListView.as_view(), name="frontport_list"),
    path("front-ports/add/", views.FrontPortCreateView.as_view(), name="frontport_add"),
    path(
        "front-ports/import/",
        views.FrontPortBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="frontport_import",
    ),
    path(
        "front-ports/edit/",
        views.FrontPortBulkEditView.as_view(),
        name="frontport_bulk_edit",
    ),
    path(
        "front-ports/rename/",
        views.FrontPortBulkRenameView.as_view(),
        name="frontport_bulk_rename",
    ),
    path(
        "front-ports/disconnect/",
        views.FrontPortBulkDisconnectView.as_view(),
        name="frontport_bulk_disconnect",
    ),
    path(
        "front-ports/delete/",
        views.FrontPortBulkDeleteView.as_view(),
        name="frontport_bulk_delete",
    ),
    path("front-ports/<uuid:pk>/", views.FrontPortView.as_view(), name="frontport"),
    path(
        "front-ports/<uuid:pk>/edit/",
        views.FrontPortEditView.as_view(),
        name="frontport_edit",
    ),
    path(
        "front-ports/<uuid:pk>/delete/",
        views.FrontPortDeleteView.as_view(),
        name="frontport_delete",
    ),
    path(
        "front-ports/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="frontport_changelog",
        kwargs={"model": FrontPort},
    ),
    path(
        "front-ports/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="frontport_notes",
        kwargs={"model": FrontPort},
    ),
    path(
        "front-ports/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="frontport_trace",
        kwargs={"model": FrontPort},
    ),
    path(
        "front-ports/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="frontport_connect",
        kwargs={"termination_a_type": FrontPort},
    ),
    # path('devices/front-ports/add/', views.DeviceBulkAddFrontPortView.as_view(), name='device_bulk_add_frontport'),
    # Rear ports
    path("rear-ports/", views.RearPortListView.as_view(), name="rearport_list"),
    path("rear-ports/add/", views.RearPortCreateView.as_view(), name="rearport_add"),
    path(
        "rear-ports/import/",
        views.RearPortBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="rearport_import",
    ),
    path(
        "rear-ports/edit/",
        views.RearPortBulkEditView.as_view(),
        name="rearport_bulk_edit",
    ),
    path(
        "rear-ports/rename/",
        views.RearPortBulkRenameView.as_view(),
        name="rearport_bulk_rename",
    ),
    path(
        "rear-ports/disconnect/",
        views.RearPortBulkDisconnectView.as_view(),
        name="rearport_bulk_disconnect",
    ),
    path(
        "rear-ports/delete/",
        views.RearPortBulkDeleteView.as_view(),
        name="rearport_bulk_delete",
    ),
    path("rear-ports/<uuid:pk>/", views.RearPortView.as_view(), name="rearport"),
    path(
        "rear-ports/<uuid:pk>/edit/",
        views.RearPortEditView.as_view(),
        name="rearport_edit",
    ),
    path(
        "rear-ports/<uuid:pk>/delete/",
        views.RearPortDeleteView.as_view(),
        name="rearport_delete",
    ),
    path(
        "rear-ports/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rearport_changelog",
        kwargs={"model": RearPort},
    ),
    path(
        "rear-ports/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="rearport_notes",
        kwargs={"model": RearPort},
    ),
    path(
        "rear-ports/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="rearport_trace",
        kwargs={"model": RearPort},
    ),
    path(
        "rear-ports/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="rearport_connect",
        kwargs={"termination_a_type": RearPort},
    ),
    path(
        "devices/rear-ports/add/",
        views.DeviceBulkAddRearPortView.as_view(),
        name="device_bulk_add_rearport",
    ),
    # Device bays
    path("device-bays/", views.DeviceBayListView.as_view(), name="devicebay_list"),
    path("device-bays/add/", views.DeviceBayCreateView.as_view(), name="devicebay_add"),
    path(
        "device-bays/import/",
        views.DeviceBayBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="devicebay_import",
    ),
    path(
        "device-bays/edit/",
        views.DeviceBayBulkEditView.as_view(),
        name="devicebay_bulk_edit",
    ),
    path(
        "device-bays/rename/",
        views.DeviceBayBulkRenameView.as_view(),
        name="devicebay_bulk_rename",
    ),
    path(
        "device-bays/delete/",
        views.DeviceBayBulkDeleteView.as_view(),
        name="devicebay_bulk_delete",
    ),
    path("device-bays/<uuid:pk>/", views.DeviceBayView.as_view(), name="devicebay"),
    path(
        "device-bays/<uuid:pk>/edit/",
        views.DeviceBayEditView.as_view(),
        name="devicebay_edit",
    ),
    path(
        "device-bays/<uuid:pk>/delete/",
        views.DeviceBayDeleteView.as_view(),
        name="devicebay_delete",
    ),
    path(
        "device-bays/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="devicebay_changelog",
        kwargs={"model": DeviceBay},
    ),
    path(
        "device-bays/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="devicebay_notes",
        kwargs={"model": DeviceBay},
    ),
    path(
        "device-bays/<uuid:pk>/populate/",
        views.DeviceBayPopulateView.as_view(),
        name="devicebay_populate",
    ),
    path(
        "device-bays/<uuid:pk>/depopulate/",
        views.DeviceBayDepopulateView.as_view(),
        name="devicebay_depopulate",
    ),
    path(
        "devices/device-bays/add/",
        views.DeviceBulkAddDeviceBayView.as_view(),
        name="device_bulk_add_devicebay",
    ),
    # Module bays (legacy views)
    path(
        "devices/module-bays/add/",
        views.DeviceBulkAddModuleBayView.as_view(),
        name="device_bulk_add_modulebay",
    ),
    # Inventory items
    path(
        "inventory-items/",
        views.InventoryItemListView.as_view(),
        name="inventoryitem_list",
    ),
    path(
        "inventory-items/add/",
        views.InventoryItemCreateView.as_view(),
        name="inventoryitem_add",
    ),
    path(
        "inventory-items/import/",
        views.InventoryItemBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="inventoryitem_import",
    ),
    path(
        "inventory-items/edit/",
        views.InventoryItemBulkEditView.as_view(),
        name="inventoryitem_bulk_edit",
    ),
    path(
        "inventory-items/rename/",
        views.InventoryItemBulkRenameView.as_view(),
        name="inventoryitem_bulk_rename",
    ),
    path(
        "inventory-items/delete/",
        views.InventoryItemBulkDeleteView.as_view(),
        name="inventoryitem_bulk_delete",
    ),
    path(
        "inventory-items/<uuid:pk>/",
        views.InventoryItemView.as_view(),
        name="inventoryitem",
    ),
    path(
        "inventory-items/<uuid:pk>/edit/",
        views.InventoryItemEditView.as_view(),
        name="inventoryitem_edit",
    ),
    path(
        "inventory-items/<uuid:pk>/delete/",
        views.InventoryItemDeleteView.as_view(),
        name="inventoryitem_delete",
    ),
    path(
        "inventory-items/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="inventoryitem_changelog",
        kwargs={"model": InventoryItem},
    ),
    path(
        "inventory-items/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="inventoryitem_notes",
        kwargs={"model": InventoryItem},
    ),
    path(
        "devices/inventory-items/add/",
        views.DeviceBulkAddInventoryItemView.as_view(),
        name="device_bulk_add_inventoryitem",
    ),
    path(
        "devices/<uuid:pk>/inventory-items/add/",
        RedirectView.as_view(url="/dcim/inventory-items/add/?device=%(pk)s&return_url=/dcim/devices/%(pk)s/inventory/"),
        name="device_inventoryitems_add",
    ),
    # Cables
    path("cables/", views.CableListView.as_view(), name="cable_list"),
    path("cables/import/", views.CableBulkImportView.as_view(), name="cable_import"),  # 3.0 TODO: remove, unused
    path("cables/edit/", views.CableBulkEditView.as_view(), name="cable_bulk_edit"),
    path("cables/delete/", views.CableBulkDeleteView.as_view(), name="cable_bulk_delete"),
    path("cables/<uuid:pk>/", views.CableView.as_view(), name="cable"),
    path("cables/<uuid:pk>/edit/", views.CableEditView.as_view(), name="cable_edit"),
    path("cables/<uuid:pk>/delete/", views.CableDeleteView.as_view(), name="cable_delete"),
    path(
        "cables/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="cable_changelog",
        kwargs={"model": Cable},
    ),
    path(
        "cables/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="cable_notes",
        kwargs={"model": Cable},
    ),
    # Console/power/interface connections (read-only)
    path(
        "console-connections/",
        views.ConsoleConnectionsListView.as_view(),
        name="console_connections_list",
    ),
    path(
        "power-connections/",
        views.PowerConnectionsListView.as_view(),
        name="power_connections_list",
    ),
    path(
        "interface-connections/",
        views.InterfaceConnectionsListView.as_view(),
        name="interface_connections_list",
    ),
    # Virtual chassis
    path(
        "virtual-chassis-members/<uuid:pk>/delete/",
        views.VirtualChassisRemoveMemberView.as_view(),
        name="virtualchassis_remove_member",
    ),
    # Power feeds
    path(
        "power-feeds/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="powerfeed_trace",
        kwargs={"model": PowerFeed},
    ),
    path(
        "power-feeds/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="powerfeed_connect",
        kwargs={"termination_a_type": PowerFeed},
    ),
]
urlpatterns += router.urls
