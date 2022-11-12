from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ObjectChangeLogView, ObjectDynamicGroupsView, ObjectNotesView, ImageAttachmentEditView
from nautobot.ipam.views import ServiceEditView
from . import views
from .models import (
    Cable,
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceBay,
    DeviceRedundancyGroup,
    DeviceRole,
    DeviceType,
    FrontPort,
    Interface,
    InventoryItem,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    PowerFeed,
    PowerPanel,
    PowerPort,
    PowerOutlet,
    Rack,
    RackGroup,
    RackReservation,
    RackRole,
    RearPort,
    Region,
    Site,
    VirtualChassis,
)

app_name = "dcim"

router = NautobotUIViewSetRouter()
router.register("device-redundancy-groups", views.DeviceRedundancyGroupUIViewSet)

urlpatterns = [
    # Regions
    path("regions/", views.RegionListView.as_view(), name="region_list"),
    path("regions/add/", views.RegionEditView.as_view(), name="region_add"),
    path("regions/import/", views.RegionBulkImportView.as_view(), name="region_import"),
    path(
        "regions/delete/",
        views.RegionBulkDeleteView.as_view(),
        name="region_bulk_delete",
    ),
    path("regions/<uuid:pk>/", views.RegionView.as_view(), name="region"),
    path("regions/<uuid:pk>/edit/", views.RegionEditView.as_view(), name="region_edit"),
    path(
        "regions/<uuid:pk>/delete/",
        views.RegionDeleteView.as_view(),
        name="region_delete",
    ),
    path(
        "regions/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="region_changelog",
        kwargs={"model": Region},
    ),
    path(
        "regions/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="region_notes",
        kwargs={"model": Region},
    ),
    # Sites
    path("sites/", views.SiteListView.as_view(), name="site_list"),
    path("sites/add/", views.SiteEditView.as_view(), name="site_add"),
    path("sites/import/", views.SiteBulkImportView.as_view(), name="site_import"),
    path("sites/edit/", views.SiteBulkEditView.as_view(), name="site_bulk_edit"),
    path("sites/delete/", views.SiteBulkDeleteView.as_view(), name="site_bulk_delete"),
    path("sites/<slug:slug>/", views.SiteView.as_view(), name="site"),
    path("sites/<slug:slug>/edit/", views.SiteEditView.as_view(), name="site_edit"),
    path("sites/<slug:slug>/delete/", views.SiteDeleteView.as_view(), name="site_delete"),
    path(
        "sites/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="site_changelog",
        kwargs={"model": Site},
    ),
    path(
        "sites/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="site_notes",
        kwargs={"model": Site},
    ),
    path(
        "sites/<uuid:object_id>/images/add/",
        ImageAttachmentEditView.as_view(),
        name="site_add_image",
        kwargs={"model": Site},
    ),
    # Location types
    path("location-types/", views.LocationTypeListView.as_view(), name="locationtype_list"),
    path("location-types/add/", views.LocationTypeEditView.as_view(), name="locationtype_add"),
    path("location-types/import/", views.LocationTypeBulkImportView.as_view(), name="locationtype_import"),
    path("location-types/delete/", views.LocationTypeBulkDeleteView.as_view(), name="locationtype_bulk_delete"),
    path("location-types/<slug:slug>/", views.LocationTypeView.as_view(), name="locationtype"),
    path("location-types/<slug:slug>/edit/", views.LocationTypeEditView.as_view(), name="locationtype_edit"),
    path("location-types/<slug:slug>/delete/", views.LocationTypeDeleteView.as_view(), name="locationtype_delete"),
    path(
        "location-types/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="locationtype_changelog",
        kwargs={"model": LocationType},
    ),
    path(
        "location-types/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="locationtype_notes",
        kwargs={"model": LocationType},
    ),
    # Locations
    path("locations/", views.LocationListView.as_view(), name="location_list"),
    path("locations/add/", views.LocationEditView.as_view(), name="location_add"),
    path("locations/edit/", views.LocationBulkEditView.as_view(), name="location_bulk_edit"),
    path("locations/import/", views.LocationBulkImportView.as_view(), name="location_import"),
    path("locations/delete/", views.LocationBulkDeleteView.as_view(), name="location_bulk_delete"),
    path("locations/<slug:slug>/", views.LocationView.as_view(), name="location"),
    path("locations/<slug:slug>/edit/", views.LocationEditView.as_view(), name="location_edit"),
    path("locations/<slug:slug>/delete/", views.LocationDeleteView.as_view(), name="location_delete"),
    path(
        "locations/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="location_changelog",
        kwargs={"model": Location},
    ),
    path(
        "locations/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="location_notes",
        kwargs={"model": Location},
    ),
    path(
        "locations/<slug:slug>/images/add/",
        ImageAttachmentEditView.as_view(),
        name="location_add_image",
        kwargs={"model": Location},
    ),
    # Rack groups
    path("rack-groups/", views.RackGroupListView.as_view(), name="rackgroup_list"),
    path("rack-groups/add/", views.RackGroupEditView.as_view(), name="rackgroup_add"),
    path(
        "rack-groups/import/",
        views.RackGroupBulkImportView.as_view(),
        name="rackgroup_import",
    ),
    path(
        "rack-groups/delete/",
        views.RackGroupBulkDeleteView.as_view(),
        name="rackgroup_bulk_delete",
    ),
    path("rack-groups/<uuid:pk>/", views.RackGroupView.as_view(), name="rackgroup"),
    path(
        "rack-groups/<uuid:pk>/edit/",
        views.RackGroupEditView.as_view(),
        name="rackgroup_edit",
    ),
    path(
        "rack-groups/<uuid:pk>/delete/",
        views.RackGroupDeleteView.as_view(),
        name="rackgroup_delete",
    ),
    path(
        "rack-groups/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rackgroup_changelog",
        kwargs={"model": RackGroup},
    ),
    path(
        "rack-groups/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="rackgroup_notes",
        kwargs={"model": RackGroup},
    ),
    # Rack roles
    path("rack-roles/", views.RackRoleListView.as_view(), name="rackrole_list"),
    path("rack-roles/add/", views.RackRoleEditView.as_view(), name="rackrole_add"),
    path(
        "rack-roles/import/",
        views.RackRoleBulkImportView.as_view(),
        name="rackrole_import",
    ),
    path(
        "rack-roles/delete/",
        views.RackRoleBulkDeleteView.as_view(),
        name="rackrole_bulk_delete",
    ),
    path("rack-roles/<uuid:pk>/", views.RackRoleView.as_view(), name="rackrole"),
    path(
        "rack-roles/<uuid:pk>/edit/",
        views.RackRoleEditView.as_view(),
        name="rackrole_edit",
    ),
    path(
        "rack-roles/<uuid:pk>/delete/",
        views.RackRoleDeleteView.as_view(),
        name="rackrole_delete",
    ),
    path(
        "rack-roles/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rackrole_changelog",
        kwargs={"model": RackRole},
    ),
    path(
        "rack-roles/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="rackrole_notes",
        kwargs={"model": RackRole},
    ),
    # Rack reservations
    path(
        "rack-reservations/",
        views.RackReservationListView.as_view(),
        name="rackreservation_list",
    ),
    path(
        "rack-reservations/add/",
        views.RackReservationEditView.as_view(),
        name="rackreservation_add",
    ),
    path(
        "rack-reservations/import/",
        views.RackReservationImportView.as_view(),
        name="rackreservation_import",
    ),
    path(
        "rack-reservations/edit/",
        views.RackReservationBulkEditView.as_view(),
        name="rackreservation_bulk_edit",
    ),
    path(
        "rack-reservations/delete/",
        views.RackReservationBulkDeleteView.as_view(),
        name="rackreservation_bulk_delete",
    ),
    path(
        "rack-reservations/<uuid:pk>/",
        views.RackReservationView.as_view(),
        name="rackreservation",
    ),
    path(
        "rack-reservations/<uuid:pk>/edit/",
        views.RackReservationEditView.as_view(),
        name="rackreservation_edit",
    ),
    path(
        "rack-reservations/<uuid:pk>/delete/",
        views.RackReservationDeleteView.as_view(),
        name="rackreservation_delete",
    ),
    path(
        "rack-reservations/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rackreservation_changelog",
        kwargs={"model": RackReservation},
    ),
    path(
        "rack-reservations/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="rackreservation_notes",
        kwargs={"model": RackReservation},
    ),
    # Racks
    path("racks/", views.RackListView.as_view(), name="rack_list"),
    path(
        "rack-elevations/",
        views.RackElevationListView.as_view(),
        name="rack_elevation_list",
    ),
    path("racks/add/", views.RackEditView.as_view(), name="rack_add"),
    path("racks/import/", views.RackBulkImportView.as_view(), name="rack_import"),
    path("racks/edit/", views.RackBulkEditView.as_view(), name="rack_bulk_edit"),
    path("racks/delete/", views.RackBulkDeleteView.as_view(), name="rack_bulk_delete"),
    path("racks/<uuid:pk>/", views.RackView.as_view(), name="rack"),
    path("racks/<uuid:pk>/edit/", views.RackEditView.as_view(), name="rack_edit"),
    path("racks/<uuid:pk>/delete/", views.RackDeleteView.as_view(), name="rack_delete"),
    path(
        "racks/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rack_changelog",
        kwargs={"model": Rack},
    ),
    path(
        "racks/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="rack_notes",
        kwargs={"model": Rack},
    ),
    path(
        "racks/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="rack_dynamicgroups",
        kwargs={"model": Rack},
    ),
    path(
        "racks/<uuid:object_id>/images/add/",
        ImageAttachmentEditView.as_view(),
        name="rack_add_image",
        kwargs={"model": Rack},
    ),
    # Manufacturers
    path("manufacturers/", views.ManufacturerListView.as_view(), name="manufacturer_list"),
    path(
        "manufacturers/add/",
        views.ManufacturerEditView.as_view(),
        name="manufacturer_add",
    ),
    path(
        "manufacturers/import/",
        views.ManufacturerBulkImportView.as_view(),
        name="manufacturer_import",
    ),
    path(
        "manufacturers/delete/",
        views.ManufacturerBulkDeleteView.as_view(),
        name="manufacturer_bulk_delete",
    ),
    path(
        "manufacturers/<slug:slug>/",
        views.ManufacturerView.as_view(),
        name="manufacturer",
    ),
    path(
        "manufacturers/<slug:slug>/edit/",
        views.ManufacturerEditView.as_view(),
        name="manufacturer_edit",
    ),
    path(
        "manufacturers/<slug:slug>/delete/",
        views.ManufacturerDeleteView.as_view(),
        name="manufacturer_delete",
    ),
    path(
        "manufacturers/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="manufacturer_changelog",
        kwargs={"model": Manufacturer},
    ),
    path(
        "manufacturers/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="manufacturer_notes",
        kwargs={"model": Manufacturer},
    ),
    # Device types
    path("device-types/", views.DeviceTypeListView.as_view(), name="devicetype_list"),
    path("device-types/add/", views.DeviceTypeEditView.as_view(), name="devicetype_add"),
    path(
        "device-types/import/",
        views.DeviceTypeImportView.as_view(),
        name="devicetype_import",
    ),
    path(
        "device-types/edit/",
        views.DeviceTypeBulkEditView.as_view(),
        name="devicetype_bulk_edit",
    ),
    path(
        "device-types/delete/",
        views.DeviceTypeBulkDeleteView.as_view(),
        name="devicetype_bulk_delete",
    ),
    path("device-types/<uuid:pk>/", views.DeviceTypeView.as_view(), name="devicetype"),
    path(
        "device-types/<uuid:pk>/edit/",
        views.DeviceTypeEditView.as_view(),
        name="devicetype_edit",
    ),
    path(
        "device-types/<uuid:pk>/delete/",
        views.DeviceTypeDeleteView.as_view(),
        name="devicetype_delete",
    ),
    path(
        "device-types/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="devicetype_changelog",
        kwargs={"model": DeviceType},
    ),
    path(
        "device-types/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="devicetype_notes",
        kwargs={"model": DeviceType},
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
    # Device roles
    path("device-roles/", views.DeviceRoleListView.as_view(), name="devicerole_list"),
    path("device-roles/add/", views.DeviceRoleEditView.as_view(), name="devicerole_add"),
    path(
        "device-roles/import/",
        views.DeviceRoleBulkImportView.as_view(),
        name="devicerole_import",
    ),
    path(
        "device-roles/delete/",
        views.DeviceRoleBulkDeleteView.as_view(),
        name="devicerole_bulk_delete",
    ),
    path("device-roles/<slug:slug>/", views.DeviceRoleView.as_view(), name="devicerole"),
    path(
        "device-roles/<slug:slug>/edit/",
        views.DeviceRoleEditView.as_view(),
        name="devicerole_edit",
    ),
    path(
        "device-roles/<slug:slug>/delete/",
        views.DeviceRoleDeleteView.as_view(),
        name="devicerole_delete",
    ),
    path(
        "device-roles/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="devicerole_changelog",
        kwargs={"model": DeviceRole},
    ),
    path(
        "device-roles/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="devicerole_notes",
        kwargs={"model": DeviceRole},
    ),
    # Platforms
    path("platforms/", views.PlatformListView.as_view(), name="platform_list"),
    path("platforms/add/", views.PlatformEditView.as_view(), name="platform_add"),
    path(
        "platforms/import/",
        views.PlatformBulkImportView.as_view(),
        name="platform_import",
    ),
    path(
        "platforms/delete/",
        views.PlatformBulkDeleteView.as_view(),
        name="platform_bulk_delete",
    ),
    path("platforms/<slug:slug>/", views.PlatformView.as_view(), name="platform"),
    path(
        "platforms/<slug:slug>/edit/",
        views.PlatformEditView.as_view(),
        name="platform_edit",
    ),
    path(
        "platforms/<slug:slug>/delete/",
        views.PlatformDeleteView.as_view(),
        name="platform_delete",
    ),
    path(
        "platforms/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="platform_changelog",
        kwargs={"model": Platform},
    ),
    path(
        "platforms/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="platform_notes",
        kwargs={"model": Platform},
    ),
    # Devices
    path("devices/", views.DeviceListView.as_view(), name="device_list"),
    path("devices/add/", views.DeviceEditView.as_view(), name="device_add"),
    path("devices/import/", views.DeviceBulkImportView.as_view(), name="device_import"),
    path(
        "devices/import/child-devices/",
        views.ChildDeviceBulkImportView.as_view(),
        name="device_import_child",
    ),
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
        "devices/<uuid:pk>/console-server-ports/",
        views.DeviceConsoleServerPortsView.as_view(),
        name="device_consoleserverports",
    ),
    path(
        "devices/<uuid:pk>/power-ports/",
        views.DevicePowerPortsView.as_view(),
        name="device_powerports",
    ),
    path(
        "devices/<uuid:pk>/power-outlets/",
        views.DevicePowerOutletsView.as_view(),
        name="device_poweroutlets",
    ),
    path(
        "devices/<uuid:pk>/interfaces/",
        views.DeviceInterfacesView.as_view(),
        name="device_interfaces",
    ),
    path(
        "devices/<uuid:pk>/front-ports/",
        views.DeviceFrontPortsView.as_view(),
        name="device_frontports",
    ),
    path(
        "devices/<uuid:pk>/rear-ports/",
        views.DeviceRearPortsView.as_view(),
        name="device_rearports",
    ),
    path(
        "devices/<uuid:pk>/device-bays/",
        views.DeviceDeviceBaysView.as_view(),
        name="device_devicebays",
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
    # Console ports
    path("console-ports/", views.ConsolePortListView.as_view(), name="consoleport_list"),
    path(
        "console-ports/add/",
        views.ConsolePortCreateView.as_view(),
        name="consoleport_add",
    ),
    path(
        "console-ports/import/",
        views.ConsolePortBulkImportView.as_view(),
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
        views.ConsoleServerPortBulkImportView.as_view(),
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
        views.PowerPortBulkImportView.as_view(),
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
        views.PowerOutletBulkImportView.as_view(),
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
        views.InterfaceBulkImportView.as_view(),
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
        views.FrontPortBulkImportView.as_view(),
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
        views.RearPortBulkImportView.as_view(),
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
        views.DeviceBayBulkImportView.as_view(),
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
        views.InventoryItemBulkImportView.as_view(),
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
    # Cables
    path("cables/", views.CableListView.as_view(), name="cable_list"),
    path("cables/import/", views.CableBulkImportView.as_view(), name="cable_import"),
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
        "virtual-chassis/",
        views.VirtualChassisListView.as_view(),
        name="virtualchassis_list",
    ),
    path(
        "virtual-chassis/add/",
        views.VirtualChassisCreateView.as_view(),
        name="virtualchassis_add",
    ),
    path(
        "virtual-chassis/import/",
        views.VirtualChassisBulkImportView.as_view(),
        name="virtualchassis_import",
    ),
    path(
        "virtual-chassis/edit/",
        views.VirtualChassisBulkEditView.as_view(),
        name="virtualchassis_bulk_edit",
    ),
    path(
        "virtual-chassis/delete/",
        views.VirtualChassisBulkDeleteView.as_view(),
        name="virtualchassis_bulk_delete",
    ),
    path(
        "virtual-chassis/<uuid:pk>/",
        views.VirtualChassisView.as_view(),
        name="virtualchassis",
    ),
    path(
        "virtual-chassis/<uuid:pk>/edit/",
        views.VirtualChassisEditView.as_view(),
        name="virtualchassis_edit",
    ),
    path(
        "virtual-chassis/<uuid:pk>/delete/",
        views.VirtualChassisDeleteView.as_view(),
        name="virtualchassis_delete",
    ),
    path(
        "virtual-chassis/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="virtualchassis_changelog",
        kwargs={"model": VirtualChassis},
    ),
    path(
        "virtual-chassis/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="virtualchassis_notes",
        kwargs={"model": VirtualChassis},
    ),
    path(
        "virtual-chassis/<uuid:pk>/add-member/",
        views.VirtualChassisAddMemberView.as_view(),
        name="virtualchassis_add_member",
    ),
    path(
        "virtual-chassis-members/<uuid:pk>/delete/",
        views.VirtualChassisRemoveMemberView.as_view(),
        name="virtualchassis_remove_member",
    ),
    # Power panels
    path("power-panels/", views.PowerPanelListView.as_view(), name="powerpanel_list"),
    path("power-panels/add/", views.PowerPanelEditView.as_view(), name="powerpanel_add"),
    path(
        "power-panels/import/",
        views.PowerPanelBulkImportView.as_view(),
        name="powerpanel_import",
    ),
    path(
        "power-panels/edit/",
        views.PowerPanelBulkEditView.as_view(),
        name="powerpanel_bulk_edit",
    ),
    path(
        "power-panels/delete/",
        views.PowerPanelBulkDeleteView.as_view(),
        name="powerpanel_bulk_delete",
    ),
    path("power-panels/<uuid:pk>/", views.PowerPanelView.as_view(), name="powerpanel"),
    path(
        "power-panels/<uuid:pk>/edit/",
        views.PowerPanelEditView.as_view(),
        name="powerpanel_edit",
    ),
    path(
        "power-panels/<uuid:pk>/delete/",
        views.PowerPanelDeleteView.as_view(),
        name="powerpanel_delete",
    ),
    path(
        "power-panels/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="powerpanel_changelog",
        kwargs={"model": PowerPanel},
    ),
    path(
        "power-panels/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="powerpanel_notes",
        kwargs={"model": PowerPanel},
    ),
    # Power feeds
    path("power-feeds/", views.PowerFeedListView.as_view(), name="powerfeed_list"),
    path("power-feeds/add/", views.PowerFeedEditView.as_view(), name="powerfeed_add"),
    path(
        "power-feeds/import/",
        views.PowerFeedBulkImportView.as_view(),
        name="powerfeed_import",
    ),
    path(
        "power-feeds/edit/",
        views.PowerFeedBulkEditView.as_view(),
        name="powerfeed_bulk_edit",
    ),
    path(
        "power-feeds/delete/",
        views.PowerFeedBulkDeleteView.as_view(),
        name="powerfeed_bulk_delete",
    ),
    path("power-feeds/<uuid:pk>/", views.PowerFeedView.as_view(), name="powerfeed"),
    path(
        "power-feeds/<uuid:pk>/edit/",
        views.PowerFeedEditView.as_view(),
        name="powerfeed_edit",
    ),
    path(
        "power-feeds/<uuid:pk>/delete/",
        views.PowerFeedDeleteView.as_view(),
        name="powerfeed_delete",
    ),
    path(
        "power-feeds/<uuid:pk>/trace/",
        views.PathTraceView.as_view(),
        name="powerfeed_trace",
        kwargs={"model": PowerFeed},
    ),
    path(
        "power-feeds/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="powerfeed_changelog",
        kwargs={"model": PowerFeed},
    ),
    path(
        "power-feeds/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="powerfeed_notes",
        kwargs={"model": PowerFeed},
    ),
    path(
        "power-feeds/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        views.CableCreateView.as_view(),
        name="powerfeed_connect",
        kwargs={"termination_a_type": PowerFeed},
    ),
    path(
        "device-redundancy-groups/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="deviceredundancygroup_changelog",
        kwargs={"model": DeviceRedundancyGroup},
    ),
    path(
        "device-redundancy-groups/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="deviceredundancygroup_notes",
        kwargs={"model": DeviceRedundancyGroup},
    ),
]
urlpatterns += router.urls
