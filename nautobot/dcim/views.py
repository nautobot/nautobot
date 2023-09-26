import uuid
from collections import OrderedDict

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import F, Prefetch
from django.forms import (
    ModelMultipleChoiceField,
    MultipleHiddenInput,
    modelformset_factory,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic import View
from django_tables2 import RequestConfig

from nautobot.circuits.models import Circuit
from nautobot.core.forms import ConfirmationForm
from nautobot.core.models.querysets import count_related
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.views import generic
from nautobot.core.views.mixins import (
    GetReturnURLMixin,
    ObjectDestroyViewMixin,
    ObjectEditViewMixin,
    ObjectPermissionRequiredMixin,
)
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.utils import get_network_driver_mapping_tool_names, get_all_network_driver_mappings
from nautobot.extras.views import ObjectChangeLogView, ObjectConfigContextView, ObjectDynamicGroupsView
from nautobot.ipam.models import IPAddress, Prefix, Service, VLAN
from nautobot.ipam.tables import InterfaceIPAddressTable, InterfaceVLANTable, VRFDeviceAssignmentTable
from nautobot.virtualization.models import VirtualMachine
from . import filters, forms, tables
from .api import serializers
from .choices import DeviceFaceChoices
from .constants import NONCONNECTABLE_IFACE_TYPES
from .models import (
    Cable,
    CablePath,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRedundancyGroup,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceRedundancyGroup,
    InterfaceRedundancyGroupAssociation,
    InterfaceTemplate,
    InventoryItem,
    Location,
    LocationType,
    Manufacturer,
    PathEndpoint,
    Platform,
    PowerFeed,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RearPort,
    RearPortTemplate,
    VirtualChassis,
)


class BulkDisconnectView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    An extendable view for disconnection console/power/interface components in bulk.
    """

    queryset = None
    template_name = "dcim/bulk_disconnect.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a new Form class from ConfirmationForm
        class _Form(ConfirmationForm):
            pk = ModelMultipleChoiceField(queryset=self.queryset, widget=MultipleHiddenInput())

        self.form = _Form

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "change")

    def post(self, request):
        selected_objects = []
        return_url = self.get_return_url(request)

        if "_confirm" in request.POST:
            form = self.form(request.POST)

            if form.is_valid():
                with transaction.atomic():
                    count = 0
                    for obj in self.queryset.filter(pk__in=form.cleaned_data["pk"]):
                        if obj.cable is None:
                            continue
                        obj.cable.delete()
                        count += 1

                messages.success(
                    request,
                    f"Disconnected {count} {self.queryset.model._meta.verbose_name_plural}",
                )

                return redirect(return_url)

        else:
            form = self.form(initial={"pk": request.POST.getlist("pk")})
            selected_objects = self.queryset.filter(pk__in=form.initial["pk"])

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "obj_type_plural": self.queryset.model._meta.verbose_name_plural,
                "selected_objects": selected_objects,
                "return_url": return_url,
            },
        )


class BaseDeviceComponentsBulkRenameView(generic.BulkRenameView):
    def get_selected_objects_parents_name(self, selected_objects):
        selected_object = selected_objects.first()
        if selected_object and selected_object.device:
            return selected_object.device.name
        return ""


#
# LocationTypes
#


class LocationTypeListView(generic.ObjectListView):
    queryset = LocationType.objects.with_tree_fields()
    filterset = filters.LocationTypeFilterSet
    filterset_form = forms.LocationTypeFilterForm
    table = tables.LocationTypeTable


class LocationTypeView(generic.ObjectView):
    queryset = LocationType.objects.all()

    def get_extra_context(self, request, instance):
        children = LocationType.objects.restrict(request.user, "view").filter(parent=instance).select_related("parent")
        locations = (
            Location.objects.restrict(request.user, "view")
            .filter(location_type=instance)
            .select_related("parent", "location_type")
        )

        children_table = tables.LocationTypeTable(children)
        locations_table = tables.LocationTable(locations)
        locations_table.columns.hide("location_type")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(children_table)
        RequestConfig(request, paginate).configure(locations_table)

        return {
            "children_table": children_table,
            "locations_table": locations_table,
        }


class LocationTypeEditView(generic.ObjectEditView):
    queryset = LocationType.objects.all()
    model_form = forms.LocationTypeForm


class LocationTypeDeleteView(generic.ObjectDeleteView):
    queryset = LocationType.objects.all()


class LocationTypeBulkImportView(generic.BulkImportView):
    queryset = LocationType.objects.all()
    table = tables.LocationTypeTable


class LocationTypeBulkDeleteView(generic.BulkDeleteView):
    queryset = LocationType.objects.all()
    filterset = filters.LocationTypeFilterSet
    table = tables.LocationTypeTable


#
# Locations
#


class LocationListView(generic.ObjectListView):
    queryset = Location.objects.select_related("location_type", "parent", "tenant")
    filterset = filters.LocationFilterSet
    filterset_form = forms.LocationFilterForm
    table = tables.LocationTable
    use_new_ui = True


class LocationView(generic.ObjectView):
    queryset = Location.objects.all()
    use_new_ui = True

    def get_extra_context(self, request, instance):
        related_locations = (
            instance.descendants(include_self=True).restrict(request.user, "view").values_list("pk", flat=True)
        )
        stats = {
            "rack_count": Rack.objects.restrict(request.user, "view").filter(location__in=related_locations).count(),
            "device_count": Device.objects.restrict(request.user, "view")
            .filter(location__in=related_locations)
            .count(),
            "prefix_count": Prefix.objects.restrict(request.user, "view")
            .filter(location__in=related_locations)
            .count(),
            "vlan_count": VLAN.objects.restrict(request.user, "view").filter(location__in=related_locations).count(),
            "circuit_count": Circuit.objects.restrict(request.user, "view")
            .filter(circuit_terminations__location__in=related_locations)
            .count(),
            "vm_count": VirtualMachine.objects.restrict(request.user, "view")
            .filter(cluster__location__in=related_locations)
            .count(),
        }
        rack_groups = (
            RackGroup.objects.annotate(rack_count=count_related(Rack, "rack_group"))
            .restrict(request.user, "view")
            .filter(location__in=related_locations)
        )
        children = (
            Location.objects.restrict(request.user, "view")
            .filter(parent=instance)
            .select_related("parent", "location_type")
        )

        children_table = tables.LocationTable(children)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(children_table)

        return {
            "children_table": children_table,
            "rack_groups": rack_groups,
            "stats": stats,
        }


class LocationEditView(generic.ObjectEditView):
    queryset = Location.objects.all()
    model_form = forms.LocationForm
    template_name = "dcim/location_edit.html"


class LocationDeleteView(generic.ObjectDeleteView):
    queryset = Location.objects.all()


class LocationBulkEditView(generic.BulkEditView):
    queryset = Location.objects.select_related("location_type", "parent", "tenant")
    filterset = filters.LocationFilterSet
    table = tables.LocationTable
    form = forms.LocationBulkEditForm


class LocationBulkImportView(generic.BulkImportView):
    queryset = Location.objects.all()
    table = tables.LocationTable


class LocationBulkDeleteView(generic.BulkDeleteView):
    queryset = Location.objects.select_related("location_type", "parent", "tenant")
    filterset = filters.LocationFilterSet
    table = tables.LocationTable


#
# Rack groups
#


class RackGroupListView(generic.ObjectListView):
    queryset = RackGroup.objects.annotate(rack_count=count_related(Rack, "rack_group")).select_related("location")
    filterset = filters.RackGroupFilterSet
    filterset_form = forms.RackGroupFilterForm
    table = tables.RackGroupTable


class RackGroupView(generic.ObjectView):
    queryset = RackGroup.objects.all()

    def get_extra_context(self, request, instance):
        # Racks
        racks = (
            Rack.objects.restrict(request.user, "view")
            .filter(rack_group__in=instance.descendants(include_self=True))
            .select_related("role", "location", "tenant")
        )

        rack_table = tables.RackTable(racks)
        rack_table.columns.hide("rack_group")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(rack_table)

        return {
            "rack_table": rack_table,
        }


class RackGroupEditView(generic.ObjectEditView):
    queryset = RackGroup.objects.all()
    model_form = forms.RackGroupForm


class RackGroupDeleteView(generic.ObjectDeleteView):
    queryset = RackGroup.objects.all()


class RackGroupBulkImportView(generic.BulkImportView):
    queryset = RackGroup.objects.all()
    table = tables.RackGroupTable


class RackGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = RackGroup.objects.annotate(rack_count=count_related(Rack, "rack_group")).select_related("location")
    filterset = filters.RackGroupFilterSet
    table = tables.RackGroupTable


#
# Racks
#


class RackListView(generic.ObjectListView):
    queryset = (
        Rack.objects.select_related("location", "rack_group", "tenant", "role", "status")
        .prefetch_related("devices__device_type")
        .annotate(device_count=count_related(Device, "rack"))
    )
    filterset = filters.RackFilterSet
    filterset_form = forms.RackFilterForm
    table = tables.RackDetailTable


class RackElevationListView(generic.ObjectListView):
    """
    Display a set of rack elevations side-by-side.
    """

    queryset = Rack.objects.select_related("role")
    non_filter_params = (
        *generic.ObjectListView.non_filter_params,
        "face",  # render front or rear of racks?
        "reverse",  # control of ordering
    )
    filterset = filters.RackFilterSet
    action_buttons = []
    template_name = "dcim/rack_elevation_list.html"

    def extra_context(self):
        racks = self.queryset
        request = self.request
        total_count = racks.count()

        # Determine ordering
        racks_reverse = bool(request.GET.get("reverse", False))
        if racks_reverse:
            racks = racks.reverse()

        # Pagination
        per_page = get_paginate_count(request)
        page_number = request.GET.get("page", 1)
        paginator = EnhancedPaginator(racks, per_page)
        try:
            page = paginator.page(page_number)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)

        # Determine rack face
        rack_face = request.GET.get("face", DeviceFaceChoices.FACE_FRONT)
        if rack_face not in DeviceFaceChoices.values():
            rack_face = DeviceFaceChoices.FACE_FRONT

        return {
            "paginator": paginator,
            "page": page,
            "total_count": total_count,
            "reverse": racks_reverse,
            "rack_face": rack_face,
            "title": "Rack Elevation",
            "list_url": "dcim:rack_elevation_list",
        }


class RackView(generic.ObjectView):
    queryset = Rack.objects.select_related("location", "tenant__tenant_group", "rack_group", "role")

    def get_extra_context(self, request, instance):
        # Get 0U and child devices located within the rack
        nonracked_devices = Device.objects.filter(rack=instance, position__isnull=True).select_related(
            "device_type__manufacturer"
        )

        peer_racks = Rack.objects.restrict(request.user, "view").filter(location=instance.location)

        if instance.rack_group:
            peer_racks = peer_racks.filter(rack_group=instance.rack_group)
        else:
            peer_racks = peer_racks.filter(rack_group__isnull=True)
        next_rack = peer_racks.filter(name__gt=instance.name).order_by("name").first()
        prev_rack = peer_racks.filter(name__lt=instance.name).order_by("-name").first()

        reservations = RackReservation.objects.restrict(request.user, "view").filter(rack=instance)
        power_feeds = (
            PowerFeed.objects.restrict(request.user, "view").filter(rack=instance).select_related("power_panel")
        )

        device_count = Device.objects.restrict(request.user, "view").filter(rack=instance).count()

        return {
            "device_count": device_count,
            "reservations": reservations,
            "power_feeds": power_feeds,
            "nonracked_devices": nonracked_devices,
            "next_rack": next_rack,
            "prev_rack": prev_rack,
        }


class RackEditView(generic.ObjectEditView):
    queryset = Rack.objects.all()
    model_form = forms.RackForm
    template_name = "dcim/rack_edit.html"


class RackDeleteView(generic.ObjectDeleteView):
    queryset = Rack.objects.all()


class RackBulkImportView(generic.BulkImportView):
    queryset = Rack.objects.all()
    table = tables.RackTable


class RackBulkEditView(generic.BulkEditView):
    queryset = Rack.objects.select_related("location", "rack_group", "tenant", "role")
    filterset = filters.RackFilterSet
    table = tables.RackTable
    form = forms.RackBulkEditForm


class RackBulkDeleteView(generic.BulkDeleteView):
    queryset = Rack.objects.select_related("location", "rack_group", "tenant", "role")
    filterset = filters.RackFilterSet
    table = tables.RackTable


#
# Rack reservations
#


class RackReservationListView(generic.ObjectListView):
    queryset = RackReservation.objects.all()
    filterset = filters.RackReservationFilterSet
    filterset_form = forms.RackReservationFilterForm
    table = tables.RackReservationTable


class RackReservationView(generic.ObjectView):
    queryset = RackReservation.objects.select_related("rack")


class RackReservationEditView(generic.ObjectEditView):
    queryset = RackReservation.objects.all()
    model_form = forms.RackReservationForm
    template_name = "dcim/rackreservation_edit.html"

    def alter_obj(self, obj, request, args, kwargs):
        if not obj.present_in_database:
            if "rack" in request.GET:
                obj.rack = get_object_or_404(Rack, pk=request.GET.get("rack"))
            obj.user = request.user
        return obj


class RackReservationDeleteView(generic.ObjectDeleteView):
    queryset = RackReservation.objects.all()


class RackReservationImportView(generic.BulkImportView):
    queryset = RackReservation.objects.all()
    table = tables.RackReservationTable


class RackReservationBulkEditView(generic.BulkEditView):
    queryset = RackReservation.objects.select_related("rack", "user")
    filterset = filters.RackReservationFilterSet
    table = tables.RackReservationTable
    form = forms.RackReservationBulkEditForm


class RackReservationBulkDeleteView(generic.BulkDeleteView):
    queryset = RackReservation.objects.select_related("rack", "user")
    filterset = filters.RackReservationFilterSet
    table = tables.RackReservationTable


#
# Manufacturers
#


class ManufacturerListView(generic.ObjectListView):
    queryset = Manufacturer.objects.annotate(
        device_type_count=count_related(DeviceType, "manufacturer"),
        inventory_item_count=count_related(InventoryItem, "manufacturer"),
        platform_count=count_related(Platform, "manufacturer"),
    )
    filterset = filters.ManufacturerFilterSet
    table = tables.ManufacturerTable


class ManufacturerView(generic.ObjectView):
    queryset = Manufacturer.objects.all()

    def get_extra_context(self, request, instance):
        # Devices
        devices = (
            Device.objects.restrict(request.user, "view")
            .filter(device_type__manufacturer=instance)
            .select_related("status", "location", "tenant", "role", "rack", "device_type")
        )

        device_table = tables.DeviceTable(devices)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(device_table)

        return {
            "device_table": device_table,
        }


class ManufacturerEditView(generic.ObjectEditView):
    queryset = Manufacturer.objects.all()
    model_form = forms.ManufacturerForm


class ManufacturerDeleteView(generic.ObjectDeleteView):
    queryset = Manufacturer.objects.all()


class ManufacturerBulkImportView(generic.BulkImportView):
    queryset = Manufacturer.objects.all()
    table = tables.ManufacturerTable


class ManufacturerBulkDeleteView(generic.BulkDeleteView):
    queryset = Manufacturer.objects.annotate(device_type_count=count_related(DeviceType, "manufacturer"))
    table = tables.ManufacturerTable
    filterset = filters.ManufacturerFilterSet


#
# Device types
#


class DeviceTypeListView(generic.ObjectListView):
    queryset = DeviceType.objects.select_related("manufacturer").annotate(
        device_count=count_related(Device, "device_type")
    )
    filterset = filters.DeviceTypeFilterSet
    filterset_form = forms.DeviceTypeFilterForm
    table = tables.DeviceTypeTable
    use_new_ui = True


class DeviceTypeView(generic.ObjectView):
    queryset = DeviceType.objects.select_related("manufacturer")
    use_new_ui = True

    def get_extra_context(self, request, instance):
        instance_count = Device.objects.restrict(request.user).filter(device_type=instance).count()

        # Component tables
        consoleport_table = tables.ConsolePortTemplateTable(
            ConsolePortTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        consoleserverport_table = tables.ConsoleServerPortTemplateTable(
            ConsoleServerPortTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        powerport_table = tables.PowerPortTemplateTable(
            PowerPortTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        poweroutlet_table = tables.PowerOutletTemplateTable(
            PowerOutletTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        interface_table = tables.InterfaceTemplateTable(
            list(InterfaceTemplate.objects.restrict(request.user, "view").filter(device_type=instance)),
            orderable=False,
        )
        front_port_table = tables.FrontPortTemplateTable(
            FrontPortTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        rear_port_table = tables.RearPortTemplateTable(
            RearPortTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        devicebay_table = tables.DeviceBayTemplateTable(
            DeviceBayTemplate.objects.restrict(request.user, "view").filter(device_type=instance),
            orderable=False,
        )
        if request.user.has_perm("dcim.change_devicetype"):
            consoleport_table.columns.show("pk")
            consoleserverport_table.columns.show("pk")
            powerport_table.columns.show("pk")
            poweroutlet_table.columns.show("pk")
            interface_table.columns.show("pk")
            front_port_table.columns.show("pk")
            rear_port_table.columns.show("pk")
            devicebay_table.columns.show("pk")

        return {
            "instance_count": instance_count,
            "consoleport_table": consoleport_table,
            "consoleserverport_table": consoleserverport_table,
            "powerport_table": powerport_table,
            "poweroutlet_table": poweroutlet_table,
            "interface_table": interface_table,
            "front_port_table": front_port_table,
            "rear_port_table": rear_port_table,
            "devicebay_table": devicebay_table,
        }


class DeviceTypeEditView(generic.ObjectEditView):
    queryset = DeviceType.objects.all()
    model_form = forms.DeviceTypeForm
    template_name = "dcim/devicetype_edit.html"


class DeviceTypeDeleteView(generic.ObjectDeleteView):
    queryset = DeviceType.objects.all()


class DeviceTypeImportView(generic.ObjectImportView):
    additional_permissions = [
        "dcim.add_devicetype",
        "dcim.add_consoleporttemplate",
        "dcim.add_consoleserverporttemplate",
        "dcim.add_powerporttemplate",
        "dcim.add_poweroutlettemplate",
        "dcim.add_interfacetemplate",
        "dcim.add_frontporttemplate",
        "dcim.add_rearporttemplate",
        "dcim.add_devicebaytemplate",
    ]
    queryset = DeviceType.objects.all()
    model_form = forms.DeviceTypeImportForm
    related_object_forms = OrderedDict(
        (
            ("console-ports", forms.ConsolePortTemplateImportForm),
            ("console-server-ports", forms.ConsoleServerPortTemplateImportForm),
            ("power-ports", forms.PowerPortTemplateImportForm),
            ("power-outlets", forms.PowerOutletTemplateImportForm),
            ("interfaces", forms.InterfaceTemplateImportForm),
            ("rear-ports", forms.RearPortTemplateImportForm),
            ("front-ports", forms.FrontPortTemplateImportForm),
            ("device-bays", forms.DeviceBayTemplateImportForm),
        )
    )


class DeviceTypeBulkEditView(generic.BulkEditView):
    queryset = DeviceType.objects.select_related("manufacturer").annotate(
        device_count=count_related(Device, "device_type")
    )
    filterset = filters.DeviceTypeFilterSet
    table = tables.DeviceTypeTable
    form = forms.DeviceTypeBulkEditForm


class DeviceTypeBulkDeleteView(generic.BulkDeleteView):
    queryset = DeviceType.objects.select_related("manufacturer").annotate(
        device_count=count_related(Device, "device_type")
    )
    filterset = filters.DeviceTypeFilterSet
    table = tables.DeviceTypeTable


#
# Console port templates
#


class ConsolePortTemplateCreateView(generic.ComponentCreateView):
    queryset = ConsolePortTemplate.objects.all()
    form = forms.ConsolePortTemplateCreateForm
    model_form = forms.ConsolePortTemplateForm
    template_name = "dcim/device_component_add.html"


class ConsolePortTemplateEditView(generic.ObjectEditView):
    queryset = ConsolePortTemplate.objects.all()
    model_form = forms.ConsolePortTemplateForm


class ConsolePortTemplateDeleteView(generic.ObjectDeleteView):
    queryset = ConsolePortTemplate.objects.all()


class ConsolePortTemplateBulkEditView(generic.BulkEditView):
    queryset = ConsolePortTemplate.objects.all()
    table = tables.ConsolePortTemplateTable
    form = forms.ConsolePortTemplateBulkEditForm
    filterset = filters.ConsolePortTemplateFilterSet


class ConsolePortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = ConsolePortTemplate.objects.all()


class ConsolePortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = ConsolePortTemplate.objects.all()
    table = tables.ConsolePortTemplateTable
    filterset = filters.ConsolePortTemplateFilterSet


#
# Console server port templates
#


class ConsoleServerPortTemplateCreateView(generic.ComponentCreateView):
    queryset = ConsoleServerPortTemplate.objects.all()
    form = forms.ConsoleServerPortTemplateCreateForm
    model_form = forms.ConsoleServerPortTemplateForm
    template_name = "dcim/device_component_add.html"


class ConsoleServerPortTemplateEditView(generic.ObjectEditView):
    queryset = ConsoleServerPortTemplate.objects.all()
    model_form = forms.ConsoleServerPortTemplateForm


class ConsoleServerPortTemplateDeleteView(generic.ObjectDeleteView):
    queryset = ConsoleServerPortTemplate.objects.all()


class ConsoleServerPortTemplateBulkEditView(generic.BulkEditView):
    queryset = ConsoleServerPortTemplate.objects.all()
    table = tables.ConsoleServerPortTemplateTable
    form = forms.ConsoleServerPortTemplateBulkEditForm
    filterset = filters.ConsoleServerPortTemplateFilterSet


class ConsoleServerPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = ConsoleServerPortTemplate.objects.all()


class ConsoleServerPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = ConsoleServerPortTemplate.objects.all()
    table = tables.ConsoleServerPortTemplateTable
    filterset = filters.ConsoleServerPortTemplateFilterSet


#
# Power port templates
#


class PowerPortTemplateCreateView(generic.ComponentCreateView):
    queryset = PowerPortTemplate.objects.all()
    form = forms.PowerPortTemplateCreateForm
    model_form = forms.PowerPortTemplateForm
    template_name = "dcim/device_component_add.html"


class PowerPortTemplateEditView(generic.ObjectEditView):
    queryset = PowerPortTemplate.objects.all()
    model_form = forms.PowerPortTemplateForm


class PowerPortTemplateDeleteView(generic.ObjectDeleteView):
    queryset = PowerPortTemplate.objects.all()


class PowerPortTemplateBulkEditView(generic.BulkEditView):
    queryset = PowerPortTemplate.objects.all()
    table = tables.PowerPortTemplateTable
    form = forms.PowerPortTemplateBulkEditForm
    filterset = filters.PowerPortTemplateFilterSet


class PowerPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = PowerPortTemplate.objects.all()


class PowerPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerPortTemplate.objects.all()
    table = tables.PowerPortTemplateTable
    filterset = filters.PowerPortTemplateFilterSet


#
# Power outlet templates
#


class PowerOutletTemplateCreateView(generic.ComponentCreateView):
    queryset = PowerOutletTemplate.objects.all()
    form = forms.PowerOutletTemplateCreateForm
    model_form = forms.PowerOutletTemplateForm
    template_name = "dcim/device_component_add.html"


class PowerOutletTemplateEditView(generic.ObjectEditView):
    queryset = PowerOutletTemplate.objects.all()
    model_form = forms.PowerOutletTemplateForm


class PowerOutletTemplateDeleteView(generic.ObjectDeleteView):
    queryset = PowerOutletTemplate.objects.all()


class PowerOutletTemplateBulkEditView(generic.BulkEditView):
    queryset = PowerOutletTemplate.objects.all()
    table = tables.PowerOutletTemplateTable
    form = forms.PowerOutletTemplateBulkEditForm
    filterset = filters.PowerOutletTemplateFilterSet


class PowerOutletTemplateBulkRenameView(generic.BulkRenameView):
    queryset = PowerOutletTemplate.objects.all()


class PowerOutletTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerOutletTemplate.objects.all()
    table = tables.PowerOutletTemplateTable
    filterset = filters.PowerOutletTemplateFilterSet


#
# Interface templates
#


class InterfaceTemplateCreateView(generic.ComponentCreateView):
    queryset = InterfaceTemplate.objects.all()
    form = forms.InterfaceTemplateCreateForm
    model_form = forms.InterfaceTemplateForm
    template_name = "dcim/device_component_add.html"


class InterfaceTemplateEditView(generic.ObjectEditView):
    queryset = InterfaceTemplate.objects.all()
    model_form = forms.InterfaceTemplateForm


class InterfaceTemplateDeleteView(generic.ObjectDeleteView):
    queryset = InterfaceTemplate.objects.all()


class InterfaceTemplateBulkEditView(generic.BulkEditView):
    queryset = InterfaceTemplate.objects.all()
    table = tables.InterfaceTemplateTable
    form = forms.InterfaceTemplateBulkEditForm
    filterset = filters.InterfaceTemplateFilterSet


class InterfaceTemplateBulkRenameView(generic.BulkRenameView):
    queryset = InterfaceTemplate.objects.all()


class InterfaceTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = InterfaceTemplate.objects.all()
    table = tables.InterfaceTemplateTable
    filterset = filters.InterfaceTemplateFilterSet


#
# Front port templates
#


class FrontPortTemplateCreateView(generic.ComponentCreateView):
    queryset = FrontPortTemplate.objects.all()
    form = forms.FrontPortTemplateCreateForm
    model_form = forms.FrontPortTemplateForm
    template_name = "dcim/device_component_add.html"


class FrontPortTemplateEditView(generic.ObjectEditView):
    queryset = FrontPortTemplate.objects.all()
    model_form = forms.FrontPortTemplateForm


class FrontPortTemplateDeleteView(generic.ObjectDeleteView):
    queryset = FrontPortTemplate.objects.all()


class FrontPortTemplateBulkEditView(generic.BulkEditView):
    queryset = FrontPortTemplate.objects.all()
    table = tables.FrontPortTemplateTable
    form = forms.FrontPortTemplateBulkEditForm
    filterset = filters.FrontPortTemplateFilterSet


class FrontPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = FrontPortTemplate.objects.all()


class FrontPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = FrontPortTemplate.objects.all()
    table = tables.FrontPortTemplateTable
    filterset = filters.FrontPortTemplateFilterSet


#
# Rear port templates
#


class RearPortTemplateCreateView(generic.ComponentCreateView):
    queryset = RearPortTemplate.objects.all()
    form = forms.RearPortTemplateCreateForm
    model_form = forms.RearPortTemplateForm
    template_name = "dcim/device_component_add.html"


class RearPortTemplateEditView(generic.ObjectEditView):
    queryset = RearPortTemplate.objects.all()
    model_form = forms.RearPortTemplateForm


class RearPortTemplateDeleteView(generic.ObjectDeleteView):
    queryset = RearPortTemplate.objects.all()


class RearPortTemplateBulkEditView(generic.BulkEditView):
    queryset = RearPortTemplate.objects.all()
    table = tables.RearPortTemplateTable
    form = forms.RearPortTemplateBulkEditForm
    filterset = filters.RearPortTemplateFilterSet


class RearPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = RearPortTemplate.objects.all()


class RearPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = RearPortTemplate.objects.all()
    table = tables.RearPortTemplateTable
    filterset = filters.RearPortTemplateFilterSet


#
# Device bay templates
#


class DeviceBayTemplateCreateView(generic.ComponentCreateView):
    queryset = DeviceBayTemplate.objects.all()
    form = forms.DeviceBayTemplateCreateForm
    model_form = forms.DeviceBayTemplateForm
    template_name = "dcim/device_component_add.html"


class DeviceBayTemplateEditView(generic.ObjectEditView):
    queryset = DeviceBayTemplate.objects.all()
    model_form = forms.DeviceBayTemplateForm


class DeviceBayTemplateDeleteView(generic.ObjectDeleteView):
    queryset = DeviceBayTemplate.objects.all()


class DeviceBayTemplateBulkEditView(generic.BulkEditView):
    queryset = DeviceBayTemplate.objects.all()
    table = tables.DeviceBayTemplateTable
    form = forms.DeviceBayTemplateBulkEditForm
    filterset = filters.DeviceBayTemplateFilterSet


class DeviceBayTemplateBulkRenameView(generic.BulkRenameView):
    queryset = DeviceBayTemplate.objects.all()


class DeviceBayTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = DeviceBayTemplate.objects.all()
    table = tables.DeviceBayTemplateTable
    filterset = filters.DeviceBayTemplateFilterSet


#
# Platforms
#


class PlatformListView(generic.ObjectListView):
    queryset = Platform.objects.annotate(
        device_count=count_related(Device, "platform"),
        virtual_machine_count=count_related(VirtualMachine, "platform"),
    )
    filterset = filters.PlatformFilterSet
    table = tables.PlatformTable


class PlatformView(generic.ObjectView):
    queryset = Platform.objects.all()

    def get_extra_context(self, request, instance):
        # Devices
        devices = (
            Device.objects.restrict(request.user, "view")
            .filter(platform=instance)
            .select_related("status", "location", "tenant", "rack", "device_type", "role")
        )

        device_table = tables.DeviceTable(devices)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(device_table)

        return {
            "device_table": device_table,
            "network_driver_tool_names": get_network_driver_mapping_tool_names(),
        }


class PlatformEditView(generic.ObjectEditView):
    queryset = Platform.objects.all()
    model_form = forms.PlatformForm
    template_name = "dcim/platform_edit.html"

    def get_extra_context(self, request, instance):
        return {"network_driver_names": sorted(get_all_network_driver_mappings().keys())}


class PlatformDeleteView(generic.ObjectDeleteView):
    queryset = Platform.objects.all()


class PlatformBulkImportView(generic.BulkImportView):
    queryset = Platform.objects.all()
    table = tables.PlatformTable


class PlatformBulkDeleteView(generic.BulkDeleteView):
    queryset = Platform.objects.all()
    table = tables.PlatformTable
    filterset = filters.PlatformFilterSet


#
# Devices
#


class DeviceListView(generic.ObjectListView):
    queryset = Device.objects.select_related(
        "status",
        "device_type",
        "role",
        "tenant",
        "location",
        "rack",
        "primary_ip4",
        "primary_ip6",
    )
    filterset = filters.DeviceFilterSet
    filterset_form = forms.DeviceFilterForm
    table = tables.DeviceTable
    template_name = "dcim/device_list.html"
    use_new_ui = True


class DeviceView(generic.ObjectView):
    queryset = Device.objects.select_related(
        "location",
        "rack__rack_group",
        "tenant__tenant_group",
        "role",
        "platform",
        "primary_ip4",
        "primary_ip6",
        "status",
    )
    use_new_ui = True

    def get_extra_context(self, request, instance):
        # VirtualChassis members
        if instance.virtual_chassis is not None:
            vc_members = (
                Device.objects.restrict(request.user, "view")
                .filter(virtual_chassis=instance.virtual_chassis)
                .order_by("vc_position")
            )
        else:
            vc_members = []

        # Services
        services = Service.objects.restrict(request.user, "view").filter(device=instance)

        # VRF assignments
        vrf_assignments = instance.vrf_assignments.restrict(request.user, "view")
        vrf_table = VRFDeviceAssignmentTable(vrf_assignments, exclude=("virtual_machine", "device"))

        return {
            "services": services,
            "vc_members": vc_members,
            "vrf_table": vrf_table,
            "active_tab": "device",
        }


class DeviceConsolePortsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/consoleports.html"

    def get_extra_context(self, request, instance):
        consoleports = (
            ConsolePort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .select_related("cable")
            .prefetch_related("_path__destination")
        )
        consoleport_table = tables.DeviceConsolePortTable(data=consoleports, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_consoleport") or request.user.has_perm("dcim.delete_consoleport"):
            consoleport_table.columns.show("pk")

        return {
            "consoleport_table": consoleport_table,
            "active_tab": "console-ports",
        }


class DeviceConsoleServerPortsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/consoleserverports.html"

    def get_extra_context(self, request, instance):
        consoleserverports = (
            ConsoleServerPort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .select_related("cable")
            .prefetch_related("_path__destination")
        )
        consoleserverport_table = tables.DeviceConsoleServerPortTable(
            data=consoleserverports, user=request.user, orderable=False
        )
        if request.user.has_perm("dcim.change_consoleserverport") or request.user.has_perm(
            "dcim.delete_consoleserverport"
        ):
            consoleserverport_table.columns.show("pk")

        return {
            "consoleserverport_table": consoleserverport_table,
            "active_tab": "console-server-ports",
        }


class DevicePowerPortsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/powerports.html"

    def get_extra_context(self, request, instance):
        powerports = (
            PowerPort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .select_related("cable")
            .prefetch_related("_path__destination")
        )
        powerport_table = tables.DevicePowerPortTable(data=powerports, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_powerport") or request.user.has_perm("dcim.delete_powerport"):
            powerport_table.columns.show("pk")

        return {
            "powerport_table": powerport_table,
            "active_tab": "power-ports",
        }


class DevicePowerOutletsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/poweroutlets.html"

    def get_extra_context(self, request, instance):
        poweroutlets = (
            PowerOutlet.objects.restrict(request.user, "view")
            .filter(device=instance)
            .select_related("cable", "power_port")
            .prefetch_related("_path__destination")
        )
        poweroutlet_table = tables.DevicePowerOutletTable(data=poweroutlets, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_poweroutlet") or request.user.has_perm("dcim.delete_poweroutlet"):
            poweroutlet_table.columns.show("pk")

        return {
            "poweroutlet_table": poweroutlet_table,
            "active_tab": "power-outlets",
        }


class DeviceInterfacesView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/interfaces.html"

    def get_extra_context(self, request, instance):
        interfaces = (
            instance.vc_interfaces.restrict(request.user, "view")
            .prefetch_related(
                Prefetch("ip_addresses", queryset=IPAddress.objects.restrict(request.user)),
                Prefetch("member_interfaces", queryset=Interface.objects.restrict(request.user)),
                "_path__destination",
                "tags",
            )
            .select_related("lag", "cable")
        )
        interface_table = tables.DeviceInterfaceTable(data=interfaces, user=request.user, orderable=False)
        if VirtualChassis.objects.filter(master=instance).exists():
            interface_table.columns.show("device")
        if request.user.has_perm("dcim.change_interface") or request.user.has_perm("dcim.delete_interface"):
            interface_table.columns.show("pk")

        return {
            "interface_table": interface_table,
            "active_tab": "interfaces",
        }


class DeviceFrontPortsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/frontports.html"

    def get_extra_context(self, request, instance):
        frontports = (
            FrontPort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .select_related("cable", "rear_port")
        )
        frontport_table = tables.DeviceFrontPortTable(data=frontports, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_frontport") or request.user.has_perm("dcim.delete_frontport"):
            frontport_table.columns.show("pk")

        return {
            "frontport_table": frontport_table,
            "active_tab": "front-ports",
        }


class DeviceRearPortsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/rearports.html"

    def get_extra_context(self, request, instance):
        rearports = RearPort.objects.restrict(request.user, "view").filter(device=instance).select_related("cable")
        rearport_table = tables.DeviceRearPortTable(data=rearports, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_rearport") or request.user.has_perm("dcim.delete_rearport"):
            rearport_table.columns.show("pk")

        return {
            "rearport_table": rearport_table,
            "active_tab": "rear-ports",
        }


class DeviceDeviceBaysView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/devicebays.html"

    def get_extra_context(self, request, instance):
        devicebays = (
            DeviceBay.objects.restrict(request.user, "view")
            .filter(device=instance)
            .select_related(
                "installed_device__device_type__manufacturer",
            )
        )
        devicebay_table = tables.DeviceDeviceBayTable(data=devicebays, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_devicebay") or request.user.has_perm("dcim.delete_devicebay"):
            devicebay_table.columns.show("pk")

        return {
            "devicebay_table": devicebay_table,
            "active_tab": "device-bays",
        }


class DeviceInventoryView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/inventory.html"

    def get_extra_context(self, request, instance):
        inventoryitems = (
            InventoryItem.objects.restrict(request.user, "view").filter(device=instance).select_related("manufacturer")
        )
        inventoryitem_table = tables.DeviceInventoryItemTable(data=inventoryitems, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_inventoryitem") or request.user.has_perm("dcim.delete_inventoryitem"):
            inventoryitem_table.columns.show("pk")

        return {
            "inventoryitem_table": inventoryitem_table,
            "active_tab": "inventory",
        }


class DeviceStatusView(generic.ObjectView):
    additional_permissions = ["dcim.napalm_read_device"]
    queryset = Device.objects.all()
    template_name = "dcim/device/status.html"

    def get_extra_context(self, request, instance):
        return {
            "active_tab": "status",
        }


class DeviceLLDPNeighborsView(generic.ObjectView):
    additional_permissions = ["dcim.napalm_read_device"]
    queryset = Device.objects.all()
    template_name = "dcim/device/lldp_neighbors.html"

    def get_extra_context(self, request, instance):
        interfaces = (
            instance.vc_interfaces.restrict(request.user, "view")
            .prefetch_related("_path__destination")
            .exclude(type__in=NONCONNECTABLE_IFACE_TYPES)
        )

        return {
            "interfaces": interfaces,
            "active_tab": "lldp-neighbors",
        }


class DeviceConfigView(generic.ObjectView):
    additional_permissions = ["dcim.napalm_read_device"]
    queryset = Device.objects.all()
    template_name = "dcim/device/config.html"

    def get_extra_context(self, request, instance):
        return {
            "active_tab": "config",
        }


class DeviceConfigContextView(ObjectConfigContextView):
    base_template = "dcim/device/base.html"

    @cached_property
    def queryset(self):  # pylint: disable=method-hidden
        """
        A cached_property rather than a class attribute because annotate_config_context_data() is unsafe at import time.
        """
        return Device.objects.annotate_config_context_data()


class DeviceChangeLogView(ObjectChangeLogView):
    base_template = "dcim/device/base.html"


class DeviceDynamicGroupsView(ObjectDynamicGroupsView):
    base_template = "dcim/device/base.html"


class DeviceEditView(generic.ObjectEditView):
    queryset = Device.objects.all()
    model_form = forms.DeviceForm
    template_name = "dcim/device_edit.html"


class DeviceDeleteView(generic.ObjectDeleteView):
    queryset = Device.objects.all()


class DeviceBulkImportView(generic.BulkImportView):
    queryset = Device.objects.all()
    table = tables.DeviceImportTable


class DeviceBulkEditView(generic.BulkEditView):
    queryset = Device.objects.select_related(
        "tenant", "location", "rack", "role", "device_type__manufacturer", "secrets_group", "device_redundancy_group"
    )
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    form = forms.DeviceBulkEditForm


class DeviceBulkDeleteView(generic.BulkDeleteView):
    queryset = Device.objects.select_related("tenant", "location", "rack", "role", "device_type__manufacturer")
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable


#
# Console ports
#


class ConsolePortListView(generic.ObjectListView):
    queryset = ConsolePort.objects.all()
    filterset = filters.ConsolePortFilterSet
    filterset_form = forms.ConsolePortFilterForm
    table = tables.ConsolePortTable
    action_buttons = ("import", "export")


class ConsolePortView(generic.ObjectView):
    queryset = ConsolePort.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_consoleports"}


class ConsolePortCreateView(generic.ComponentCreateView):
    queryset = ConsolePort.objects.all()
    form = forms.ConsolePortCreateForm
    model_form = forms.ConsolePortForm
    template_name = "dcim/device_component_add.html"


class ConsolePortEditView(generic.ObjectEditView):
    queryset = ConsolePort.objects.all()
    model_form = forms.ConsolePortForm
    template_name = "dcim/device_component_edit.html"


class ConsolePortDeleteView(generic.ObjectDeleteView):
    queryset = ConsolePort.objects.all()


class ConsolePortBulkImportView(generic.BulkImportView):
    queryset = ConsolePort.objects.all()
    table = tables.ConsolePortTable


class ConsolePortBulkEditView(generic.BulkEditView):
    queryset = ConsolePort.objects.all()
    filterset = filters.ConsolePortFilterSet
    table = tables.ConsolePortTable
    form = forms.ConsolePortBulkEditForm


class ConsolePortBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = ConsolePort.objects.all()


class ConsolePortBulkDisconnectView(BulkDisconnectView):
    queryset = ConsolePort.objects.all()


class ConsolePortBulkDeleteView(generic.BulkDeleteView):
    queryset = ConsolePort.objects.all()
    filterset = filters.ConsolePortFilterSet
    table = tables.ConsolePortTable


#
# Console server ports
#


class ConsoleServerPortListView(generic.ObjectListView):
    queryset = ConsoleServerPort.objects.all()
    filterset = filters.ConsoleServerPortFilterSet
    filterset_form = forms.ConsoleServerPortFilterForm
    table = tables.ConsoleServerPortTable
    action_buttons = ("import", "export")


class ConsoleServerPortView(generic.ObjectView):
    queryset = ConsoleServerPort.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_consoleserverports"}


class ConsoleServerPortCreateView(generic.ComponentCreateView):
    queryset = ConsoleServerPort.objects.all()
    form = forms.ConsoleServerPortCreateForm
    model_form = forms.ConsoleServerPortForm
    template_name = "dcim/device_component_add.html"


class ConsoleServerPortEditView(generic.ObjectEditView):
    queryset = ConsoleServerPort.objects.all()
    model_form = forms.ConsoleServerPortForm
    template_name = "dcim/device_component_edit.html"


class ConsoleServerPortDeleteView(generic.ObjectDeleteView):
    queryset = ConsoleServerPort.objects.all()


class ConsoleServerPortBulkImportView(generic.BulkImportView):
    queryset = ConsoleServerPort.objects.all()
    table = tables.ConsoleServerPortTable


class ConsoleServerPortBulkEditView(generic.BulkEditView):
    queryset = ConsoleServerPort.objects.all()
    filterset = filters.ConsoleServerPortFilterSet
    table = tables.ConsoleServerPortTable
    form = forms.ConsoleServerPortBulkEditForm


class ConsoleServerPortBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = ConsoleServerPort.objects.all()


class ConsoleServerPortBulkDisconnectView(BulkDisconnectView):
    queryset = ConsoleServerPort.objects.all()


class ConsoleServerPortBulkDeleteView(generic.BulkDeleteView):
    queryset = ConsoleServerPort.objects.all()
    filterset = filters.ConsoleServerPortFilterSet
    table = tables.ConsoleServerPortTable


#
# Power ports
#


class PowerPortListView(generic.ObjectListView):
    queryset = PowerPort.objects.all()
    filterset = filters.PowerPortFilterSet
    filterset_form = forms.PowerPortFilterForm
    table = tables.PowerPortTable
    action_buttons = ("import", "export")


class PowerPortView(generic.ObjectView):
    queryset = PowerPort.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_powerports"}


class PowerPortCreateView(generic.ComponentCreateView):
    queryset = PowerPort.objects.all()
    form = forms.PowerPortCreateForm
    model_form = forms.PowerPortForm
    template_name = "dcim/device_component_add.html"


class PowerPortEditView(generic.ObjectEditView):
    queryset = PowerPort.objects.all()
    model_form = forms.PowerPortForm
    template_name = "dcim/device_component_edit.html"


class PowerPortDeleteView(generic.ObjectDeleteView):
    queryset = PowerPort.objects.all()


class PowerPortBulkImportView(generic.BulkImportView):
    queryset = PowerPort.objects.all()
    table = tables.PowerPortTable


class PowerPortBulkEditView(generic.BulkEditView):
    queryset = PowerPort.objects.all()
    filterset = filters.PowerPortFilterSet
    table = tables.PowerPortTable
    form = forms.PowerPortBulkEditForm


class PowerPortBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = PowerPort.objects.all()


class PowerPortBulkDisconnectView(BulkDisconnectView):
    queryset = PowerPort.objects.all()


class PowerPortBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerPort.objects.all()
    filterset = filters.PowerPortFilterSet
    table = tables.PowerPortTable


#
# Power outlets
#


class PowerOutletListView(generic.ObjectListView):
    queryset = PowerOutlet.objects.all()
    filterset = filters.PowerOutletFilterSet
    filterset_form = forms.PowerOutletFilterForm
    table = tables.PowerOutletTable
    action_buttons = ("import", "export")


class PowerOutletView(generic.ObjectView):
    queryset = PowerOutlet.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_poweroutlets"}


class PowerOutletCreateView(generic.ComponentCreateView):
    queryset = PowerOutlet.objects.all()
    form = forms.PowerOutletCreateForm
    model_form = forms.PowerOutletForm
    template_name = "dcim/device_component_add.html"


class PowerOutletEditView(generic.ObjectEditView):
    queryset = PowerOutlet.objects.all()
    model_form = forms.PowerOutletForm
    template_name = "dcim/device_component_edit.html"


class PowerOutletDeleteView(generic.ObjectDeleteView):
    queryset = PowerOutlet.objects.all()


class PowerOutletBulkImportView(generic.BulkImportView):
    queryset = PowerOutlet.objects.all()
    table = tables.PowerOutletTable


class PowerOutletBulkEditView(generic.BulkEditView):
    queryset = PowerOutlet.objects.all()
    filterset = filters.PowerOutletFilterSet
    table = tables.PowerOutletTable
    form = forms.PowerOutletBulkEditForm


class PowerOutletBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = PowerOutlet.objects.all()


class PowerOutletBulkDisconnectView(BulkDisconnectView):
    queryset = PowerOutlet.objects.all()


class PowerOutletBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerOutlet.objects.all()
    filterset = filters.PowerOutletFilterSet
    table = tables.PowerOutletTable


#
# Interfaces
#


class InterfaceListView(generic.ObjectListView):
    queryset = Interface.objects.all()
    filterset = filters.InterfaceFilterSet
    filterset_form = forms.InterfaceFilterForm
    table = tables.InterfaceTable
    action_buttons = ("import", "export")


class InterfaceView(generic.ObjectView):
    queryset = Interface.objects.all()

    def get_extra_context(self, request, instance):
        # Get assigned IP addresses
        ipaddress_table = InterfaceIPAddressTable(
            # data=instance.ip_addresses.restrict(request.user, "view").select_related("vrf", "tenant"),
            data=instance.ip_addresses.restrict(request.user, "view").select_related("tenant"),
            orderable=False,
        )

        # Get child interfaces
        child_interfaces = instance.child_interfaces.restrict(request.user, "view")
        child_interfaces_tables = tables.InterfaceTable(child_interfaces, orderable=False, exclude=("device",))

        # Get assigned VLANs and annotate whether each is tagged or untagged
        vlans = []
        if instance.untagged_vlan is not None:
            vlans.append(instance.untagged_vlan)
            vlans[0].tagged = False

        for vlan in instance.tagged_vlans.restrict(request.user).select_related(
            "location", "vlan_group", "tenant", "role"
        ):
            vlan.tagged = True
            vlans.append(vlan)
        vlan_table = InterfaceVLANTable(interface=instance, data=vlans, orderable=False)

        redundancy_table = self._get_interface_redundancy_groups_table(request, instance)

        return {
            "ipaddress_table": ipaddress_table,
            "vlan_table": vlan_table,
            "breadcrumb_url": "dcim:device_interfaces",
            "child_interfaces_table": child_interfaces_tables,
            "redundancy_table": redundancy_table,
        }

    def _get_interface_redundancy_groups_table(self, request, instance):
        """Return a table of assigned Interface Redundancy Groups."""
        queryset = instance.interface_redundancy_group_associations.restrict(request.user)
        queryset = queryset.select_related("interface_redundancy_group")
        queryset = queryset.order_by("interface_redundancy_group", "priority")
        column_sequence = (
            "interface_redundancy_group",
            "priority",
            "interface_redundancy_group__status",
            "interface_redundancy_group__protocol",
            "interface_redundancy_group__protocol_group_id",
            "interface_redundancy_group__virtual_ip",
        )
        table = tables.InterfaceRedundancyGroupAssociationTable(
            data=queryset,
            sequence=column_sequence,
            orderable=False,
        )
        for field in column_sequence:
            table.columns.show(field)
        return table


class InterfaceCreateView(generic.ComponentCreateView):
    queryset = Interface.objects.all()
    form = forms.InterfaceCreateForm
    model_form = forms.InterfaceForm
    template_name = "dcim/device_component_add.html"


class InterfaceEditView(generic.ObjectEditView):
    queryset = Interface.objects.all()
    model_form = forms.InterfaceForm
    template_name = "dcim/interface_edit.html"


class InterfaceDeleteView(generic.ObjectDeleteView):
    queryset = Interface.objects.all()
    template_name = "dcim/device_interface_delete.html"


class InterfaceBulkImportView(generic.BulkImportView):
    queryset = Interface.objects.all()
    table = tables.InterfaceTable


class InterfaceBulkEditView(generic.BulkEditView):
    queryset = Interface.objects.all()
    filterset = filters.InterfaceFilterSet
    table = tables.InterfaceTable
    form = forms.InterfaceBulkEditForm


class InterfaceBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = Interface.objects.all()


class InterfaceBulkDisconnectView(BulkDisconnectView):
    queryset = Interface.objects.all()


class InterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = Interface.objects.all()
    filterset = filters.InterfaceFilterSet
    table = tables.InterfaceTable
    template_name = "dcim/interface_bulk_delete.html"


#
# Front ports
#


class FrontPortListView(generic.ObjectListView):
    queryset = FrontPort.objects.all()
    filterset = filters.FrontPortFilterSet
    filterset_form = forms.FrontPortFilterForm
    table = tables.FrontPortTable
    action_buttons = ("import", "export")


class FrontPortView(generic.ObjectView):
    queryset = FrontPort.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_frontports"}


class FrontPortCreateView(generic.ComponentCreateView):
    queryset = FrontPort.objects.all()
    form = forms.FrontPortCreateForm
    model_form = forms.FrontPortForm
    template_name = "dcim/device_component_add.html"


class FrontPortEditView(generic.ObjectEditView):
    queryset = FrontPort.objects.all()
    model_form = forms.FrontPortForm
    template_name = "dcim/device_component_edit.html"


class FrontPortDeleteView(generic.ObjectDeleteView):
    queryset = FrontPort.objects.all()


class FrontPortBulkImportView(generic.BulkImportView):
    queryset = FrontPort.objects.all()
    table = tables.FrontPortTable


class FrontPortBulkEditView(generic.BulkEditView):
    queryset = FrontPort.objects.all()
    filterset = filters.FrontPortFilterSet
    table = tables.FrontPortTable
    form = forms.FrontPortBulkEditForm


class FrontPortBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = FrontPort.objects.all()


class FrontPortBulkDisconnectView(BulkDisconnectView):
    queryset = FrontPort.objects.all()


class FrontPortBulkDeleteView(generic.BulkDeleteView):
    queryset = FrontPort.objects.all()
    filterset = filters.FrontPortFilterSet
    table = tables.FrontPortTable


#
# Rear ports
#


class RearPortListView(generic.ObjectListView):
    queryset = RearPort.objects.all()
    filterset = filters.RearPortFilterSet
    filterset_form = forms.RearPortFilterForm
    table = tables.RearPortTable
    action_buttons = ("import", "export")


class RearPortView(generic.ObjectView):
    queryset = RearPort.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_rearports"}


class RearPortCreateView(generic.ComponentCreateView):
    queryset = RearPort.objects.all()
    form = forms.RearPortCreateForm
    model_form = forms.RearPortForm
    template_name = "dcim/device_component_add.html"


class RearPortEditView(generic.ObjectEditView):
    queryset = RearPort.objects.all()
    model_form = forms.RearPortForm
    template_name = "dcim/device_component_edit.html"


class RearPortDeleteView(generic.ObjectDeleteView):
    queryset = RearPort.objects.all()


class RearPortBulkImportView(generic.BulkImportView):
    queryset = RearPort.objects.all()
    table = tables.RearPortTable


class RearPortBulkEditView(generic.BulkEditView):
    queryset = RearPort.objects.all()
    filterset = filters.RearPortFilterSet
    table = tables.RearPortTable
    form = forms.RearPortBulkEditForm


class RearPortBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = RearPort.objects.all()


class RearPortBulkDisconnectView(BulkDisconnectView):
    queryset = RearPort.objects.all()


class RearPortBulkDeleteView(generic.BulkDeleteView):
    queryset = RearPort.objects.all()
    filterset = filters.RearPortFilterSet
    table = tables.RearPortTable


#
# Device bays
#


class DeviceBayListView(generic.ObjectListView):
    queryset = DeviceBay.objects.all()
    filterset = filters.DeviceBayFilterSet
    filterset_form = forms.DeviceBayFilterForm
    table = tables.DeviceBayTable
    action_buttons = ("import", "export")


class DeviceBayView(generic.ObjectView):
    queryset = DeviceBay.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_devicebays"}


class DeviceBayCreateView(generic.ComponentCreateView):
    queryset = DeviceBay.objects.all()
    form = forms.DeviceBayCreateForm
    model_form = forms.DeviceBayForm
    template_name = "dcim/device_component_add.html"


class DeviceBayEditView(generic.ObjectEditView):
    queryset = DeviceBay.objects.all()
    model_form = forms.DeviceBayForm
    template_name = "dcim/device_component_edit.html"


class DeviceBayDeleteView(generic.ObjectDeleteView):
    queryset = DeviceBay.objects.all()


class DeviceBayPopulateView(generic.ObjectEditView):
    queryset = DeviceBay.objects.all()

    def get(self, request, *args, **kwargs):
        device_bay = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = forms.PopulateDeviceBayForm(device_bay)

        return render(
            request,
            "dcim/devicebay_populate.html",
            {
                "device_bay": device_bay,
                "form": form,
                "return_url": self.get_return_url(request, device_bay),
            },
        )

    def post(self, request, *args, **kwargs):
        device_bay = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = forms.PopulateDeviceBayForm(device_bay, request.POST)

        if form.is_valid():
            device_bay.installed_device = form.cleaned_data["installed_device"]
            device_bay.save()
            messages.success(
                request,
                f"Added {device_bay.installed_device} to {device_bay}.",
            )

            return redirect("dcim:device", pk=device_bay.device.pk)

        return render(
            request,
            "dcim/devicebay_populate.html",
            {
                "device_bay": device_bay,
                "form": form,
                "return_url": self.get_return_url(request, device_bay),
            },
        )


class DeviceBayDepopulateView(generic.ObjectEditView):
    queryset = DeviceBay.objects.all()

    def get(self, request, *args, **kwargs):
        device_bay = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = ConfirmationForm()

        return render(
            request,
            "dcim/devicebay_depopulate.html",
            {
                "device_bay": device_bay,
                "form": form,
                "return_url": self.get_return_url(request, device_bay),
            },
        )

    def post(self, request, *args, **kwargs):
        device_bay = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            removed_device = device_bay.installed_device
            device_bay.installed_device = None
            device_bay.save()
            messages.success(
                request,
                f"Removed {removed_device} from {device_bay}.",
            )

            return redirect("dcim:device", pk=device_bay.device.pk)

        return render(
            request,
            "dcim/devicebay_depopulate.html",
            {
                "device_bay": device_bay,
                "form": form,
                "return_url": self.get_return_url(request, device_bay),
            },
        )


class DeviceBayBulkImportView(generic.BulkImportView):
    queryset = DeviceBay.objects.all()
    table = tables.DeviceBayTable


class DeviceBayBulkEditView(generic.BulkEditView):
    queryset = DeviceBay.objects.all()
    filterset = filters.DeviceBayFilterSet
    table = tables.DeviceBayTable
    form = forms.DeviceBayBulkEditForm


class DeviceBayBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = DeviceBay.objects.all()


class DeviceBayBulkDeleteView(generic.BulkDeleteView):
    queryset = DeviceBay.objects.all()
    filterset = filters.DeviceBayFilterSet
    table = tables.DeviceBayTable


#
# Inventory items
#


class InventoryItemListView(generic.ObjectListView):
    queryset = InventoryItem.objects.all()
    filterset = filters.InventoryItemFilterSet
    filterset_form = forms.InventoryItemFilterForm
    table = tables.InventoryItemTable
    action_buttons = ("import", "export")


class InventoryItemView(generic.ObjectView):
    queryset = InventoryItem.objects.all()

    def get_extra_context(self, request, instance):
        return {"breadcrumb_url": "dcim:device_inventory"}


class InventoryItemEditView(generic.ObjectEditView):
    queryset = InventoryItem.objects.all()
    model_form = forms.InventoryItemForm


class InventoryItemCreateView(generic.ComponentCreateView):
    queryset = InventoryItem.objects.all()
    form = forms.InventoryItemCreateForm
    model_form = forms.InventoryItemForm
    template_name = "dcim/device_component_add.html"


class InventoryItemDeleteView(generic.ObjectDeleteView):
    queryset = InventoryItem.objects.all()


class InventoryItemBulkImportView(generic.BulkImportView):
    queryset = InventoryItem.objects.all()
    table = tables.InventoryItemTable


class InventoryItemBulkEditView(generic.BulkEditView):
    queryset = InventoryItem.objects.select_related("device", "manufacturer")
    filterset = filters.InventoryItemFilterSet
    table = tables.InventoryItemTable
    form = forms.InventoryItemBulkEditForm


class InventoryItemBulkRenameView(BaseDeviceComponentsBulkRenameView):
    queryset = InventoryItem.objects.all()


class InventoryItemBulkDeleteView(generic.BulkDeleteView):
    queryset = InventoryItem.objects.select_related("device", "manufacturer")
    table = tables.InventoryItemTable
    template_name = "dcim/inventoryitem_bulk_delete.html"
    filterset = filters.InventoryItemFilterSet


#
# Bulk Device component creation
#


class DeviceBulkAddConsolePortView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.ConsolePortBulkCreateForm
    queryset = ConsolePort.objects.all()
    model_form = forms.ConsolePortForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


class DeviceBulkAddConsoleServerPortView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.ConsoleServerPortBulkCreateForm
    queryset = ConsoleServerPort.objects.all()
    model_form = forms.ConsoleServerPortForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


class DeviceBulkAddPowerPortView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.PowerPortBulkCreateForm
    queryset = PowerPort.objects.all()
    model_form = forms.PowerPortForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


class DeviceBulkAddPowerOutletView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.PowerOutletBulkCreateForm
    queryset = PowerOutlet.objects.all()
    model_form = forms.PowerOutletForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


class DeviceBulkAddInterfaceView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.InterfaceBulkCreateForm
    queryset = Interface.objects.all()
    model_form = forms.InterfaceForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


# class DeviceBulkAddFrontPortView(generic.BulkComponentCreateView):
#     parent_model = Device
#     parent_field = 'device'
#     form = forms.FrontPortBulkCreateForm
#     queryset = FrontPort.objects.all()
#     model_form = forms.FrontPortForm
#     filterset = filters.DeviceFilterSet
#     table = tables.DeviceTable
#     default_return_url = 'dcim:device_list'


class DeviceBulkAddRearPortView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.RearPortBulkCreateForm
    queryset = RearPort.objects.all()
    model_form = forms.RearPortForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


class DeviceBulkAddDeviceBayView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.DeviceBayBulkCreateForm
    queryset = DeviceBay.objects.all()
    model_form = forms.DeviceBayForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


class DeviceBulkAddInventoryItemView(generic.BulkComponentCreateView):
    parent_model = Device
    parent_field = "device"
    form = forms.InventoryItemBulkCreateForm
    queryset = InventoryItem.objects.all()
    model_form = forms.InventoryItemForm
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    default_return_url = "dcim:device_list"


#
# Cables
#


class CableListView(generic.ObjectListView):
    queryset = Cable.objects.all()
    filterset = filters.CableFilterSet
    filterset_form = forms.CableFilterForm
    table = tables.CableTable
    action_buttons = ("import", "export")


class CableView(generic.ObjectView):
    queryset = Cable.objects.all()


class PathTraceView(generic.ObjectView):
    """
    Trace a cable path beginning from the given path endpoint (origin).
    """

    additional_permissions = ["dcim.view_cable"]
    template_name = "dcim/cable_trace.html"

    def dispatch(self, request, *args, **kwargs):
        model = kwargs.pop("model")
        self.queryset = model.objects.all()

        return super().dispatch(request, *args, **kwargs)

    def get_extra_context(self, request, instance):
        related_paths = []

        # If tracing a PathEndpoint, locate the CablePath (if one exists) by its origin
        if isinstance(instance, PathEndpoint):
            path = instance._path

        # Otherwise, find all CablePaths which traverse the specified object
        else:
            related_paths = CablePath.objects.filter(path__contains=instance).prefetch_related("origin")
            # Check for specification of a particular path (when tracing pass-through ports)

            cablepath_id = request.GET.get("cablepath_id")
            if cablepath_id is not None:
                try:
                    path_id = uuid.UUID(cablepath_id)
                except (AttributeError, TypeError, ValueError):
                    path_id = None
                try:
                    path = related_paths.get(pk=path_id)
                except CablePath.DoesNotExist:
                    path = related_paths.first()
            else:
                path = related_paths.first()

        return {
            "path": path,
            "related_paths": related_paths,
            "total_length": path.get_total_length() if path else None,
        }


class CableCreateView(generic.ObjectEditView):
    queryset = Cable.objects.all()
    template_name = "dcim/cable_connect.html"

    def dispatch(self, request, *args, **kwargs):
        # Set the model_form class based on the type of component being connected
        self.model_form = {
            "console-port": forms.ConnectCableToConsolePortForm,
            "console-server-port": forms.ConnectCableToConsoleServerPortForm,
            "power-port": forms.ConnectCableToPowerPortForm,
            "power-outlet": forms.ConnectCableToPowerOutletForm,
            "interface": forms.ConnectCableToInterfaceForm,
            "front-port": forms.ConnectCableToFrontPortForm,
            "rear-port": forms.ConnectCableToRearPortForm,
            "power-feed": forms.ConnectCableToPowerFeedForm,
            "circuit-termination": forms.ConnectCableToCircuitTerminationForm,
        }[kwargs.get("termination_b_type")]

        return super().dispatch(request, *args, **kwargs)

    def alter_obj(self, obj, request, url_args, url_kwargs):
        termination_a_type = url_kwargs.get("termination_a_type")
        termination_a_id = url_kwargs.get("termination_a_id")
        termination_b_type_name = url_kwargs.get("termination_b_type")
        self.termination_b_type = ContentType.objects.get(model=termination_b_type_name.replace("-", ""))

        # Initialize Cable termination attributes
        obj.termination_a = termination_a_type.objects.get(pk=termination_a_id)
        obj.termination_b_type = self.termination_b_type

        return obj

    def get(self, request, *args, **kwargs):
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)

        # Parse initial data manually to avoid setting field values as lists
        initial_data = {k: request.GET[k] for k in request.GET}

        # Set initial location and rack based on side A termination (if not already set)
        termination_a_location = getattr(obj.termination_a.parent, "location", None)
        if "termination_b_location" not in initial_data:
            initial_data["termination_b_location"] = termination_a_location
        if "termination_b_rack" not in initial_data:
            initial_data["termination_b_rack"] = getattr(obj.termination_a.parent, "rack", None)

        form = self.model_form(exclude_id=kwargs.get("termination_a_id"), instance=obj, initial=initial_data)

        # the following builds up a CSS query selector to match all drop-downs
        # in the termination_b form except the termination_b_id. this is necessary to reset the termination_b_id
        # drop-down whenever any of these drop-downs' values changes. this cannot be hardcoded because the form is
        # selected dynamically and therefore the fields change depending on the value of termination_b_type (L2358)
        js_select_onchange_query = ", ".join(
            [
                f"select#id_{field_name}"
                for field_name, field in form.fields.items()
                # include all termination_b_* fields:
                if field_name.startswith("termination_b")
                # exclude termination_b_id:
                and field_name != "termination_b_id"
                # include only HTML select fields:
                and field.widget.input_type == "select"
            ]
        )
        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "obj_type": Cable._meta.verbose_name,
                "termination_b_type": self.termination_b_type.name,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                "js_select_onchange_query": js_select_onchange_query,
            },
        )


class CableEditView(generic.ObjectEditView):
    queryset = Cable.objects.all()
    model_form = forms.CableForm
    template_name = "dcim/cable_edit.html"


class CableDeleteView(generic.ObjectDeleteView):
    queryset = Cable.objects.all()


class CableBulkImportView(generic.BulkImportView):
    queryset = Cable.objects.all()
    table = tables.CableTable


class CableBulkEditView(generic.BulkEditView):
    queryset = Cable.objects.prefetch_related("termination_a", "termination_b")
    filterset = filters.CableFilterSet
    table = tables.CableTable
    form = forms.CableBulkEditForm


class CableBulkDeleteView(generic.BulkDeleteView):
    queryset = Cable.objects.prefetch_related("termination_a", "termination_b")
    filterset = filters.CableFilterSet
    table = tables.CableTable


#
# Connections
#


class ConnectionsListView(generic.ObjectListView):
    pass


class ConsoleConnectionsListView(ConnectionsListView):
    queryset = ConsolePort.objects.filter(_path__isnull=False)
    filterset = filters.ConsoleConnectionFilterSet
    filterset_form = forms.ConsoleConnectionFilterForm
    table = tables.ConsoleConnectionTable
    template_name = "dcim/console_port_connection_list.html"
    action_buttons = ("export",)

    def extra_context(self):
        return {
            "title": "Console Connections",
            "list_url": "dcim:console_connections_list",
            "search_form": None,  # ConsoleConnectionFilterSet do not support q filter
        }


class PowerConnectionsListView(ConnectionsListView):
    queryset = PowerPort.objects.filter(_path__isnull=False)
    filterset = filters.PowerConnectionFilterSet
    filterset_form = forms.PowerConnectionFilterForm
    table = tables.PowerConnectionTable
    template_name = "dcim/power_port_connection_list.html"
    action_buttons = ("export",)

    def extra_context(self):
        return {
            "title": "Power Connections",
            "list_url": "dcim:power_connections_list",
            "search_form": None,  # PowerConnectionFilterSet do not support q filter
        }


class InterfaceConnectionsListView(ConnectionsListView):
    queryset = None  # This gets set initially in init (See `get_queryset()`)
    filterset = filters.InterfaceConnectionFilterSet
    filterset_form = forms.InterfaceConnectionFilterForm
    table = tables.InterfaceConnectionTable
    template_name = "dcim/interface_connection_list.html"
    action_buttons = ("export",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_queryset()  # Populate self.queryset after init.

    def get_queryset(self):
        """
        This is a required so that the call to `ContentType.objects.get_for_model` does not result in a circular import.
        """
        qs = Interface.objects.filter(_path__isnull=False).exclude(
            # If an Interface is connected to another Interface, avoid returning both (A, B) and (B, A)
            # Unfortunately we can't use something consistent to pick which pair to exclude (such as device or name)
            # as _path.destination is a GenericForeignKey without a corresponding GenericRelation and so cannot be
            # used for reverse querying.
            # The below at least ensures uniqueness, but doesn't guarantee whether we get (A, B) or (B, A)
            # TODO: this is very problematic when filtering the view via FilterSet - if the filterset matches (A), then
            #       the connection will appear in the table, but if it only matches (B) then the connection will not!
            _path__destination_type=ContentType.objects.get_for_model(Interface),
            pk__lt=F("_path__destination_id"),
        )
        if self.queryset is None:
            self.queryset = qs

        return self.queryset

    def extra_context(self):
        return {
            "title": "Interface Connections",
            "list_url": "dcim:interface_connections_list",
            "search_form": None,  # InterfaceConnectionFilterSet do not support q filter
        }


#
# Virtual chassis
#


class VirtualChassisListView(generic.ObjectListView):
    queryset = VirtualChassis.objects.select_related("master").annotate(
        member_count=count_related(Device, "virtual_chassis")
    )
    table = tables.VirtualChassisTable
    filterset = filters.VirtualChassisFilterSet
    filterset_form = forms.VirtualChassisFilterForm


class VirtualChassisView(generic.ObjectView):
    queryset = VirtualChassis.objects.all()

    def get_extra_context(self, request, instance):
        members = Device.objects.restrict(request.user).filter(virtual_chassis=instance)

        return {
            "members": members,
        }


class VirtualChassisCreateView(generic.ObjectEditView):
    queryset = VirtualChassis.objects.all()
    model_form = forms.VirtualChassisCreateForm
    template_name = "dcim/virtualchassis_add.html"


class VirtualChassisEditView(ObjectPermissionRequiredMixin, GetReturnURLMixin, View):
    queryset = VirtualChassis.objects.all()

    def get_required_permission(self):
        return "dcim.change_virtualchassis"

    def get(self, request, pk):
        virtual_chassis = get_object_or_404(self.queryset, pk=pk)
        VCMemberFormSet = modelformset_factory(
            model=Device,
            form=forms.DeviceVCMembershipForm,
            formset=forms.BaseVCMemberFormSet,
            extra=0,
        )
        members_queryset = virtual_chassis.members.select_related("rack").order_by("vc_position")

        vc_form = forms.VirtualChassisForm(instance=virtual_chassis)
        vc_form.fields["master"].queryset = members_queryset
        formset = VCMemberFormSet(queryset=members_queryset)

        return render(
            request,
            "dcim/virtualchassis_edit.html",
            {
                "vc_form": vc_form,
                "formset": formset,
                "return_url": self.get_return_url(request, virtual_chassis),
            },
        )

    def post(self, request, pk):
        virtual_chassis = get_object_or_404(self.queryset, pk=pk)
        VCMemberFormSet = modelformset_factory(
            model=Device,
            form=forms.DeviceVCMembershipForm,
            formset=forms.BaseVCMemberFormSet,
            extra=0,
        )
        members_queryset = virtual_chassis.members.select_related("rack").order_by("vc_position")

        vc_form = forms.VirtualChassisForm(request.POST, instance=virtual_chassis)
        vc_form.fields["master"].queryset = members_queryset
        formset = VCMemberFormSet(request.POST, queryset=members_queryset)

        if vc_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Save the VirtualChassis
                vc_form.save()

                # Nullify the vc_position of each member first to allow reordering without raising an IntegrityError on
                # duplicate positions. Then save each member instance.
                members = formset.save(commit=False)
                devices = Device.objects.filter(pk__in=[m.pk for m in members])
                for device in devices:
                    device.vc_position = None
                    device.save()
                for member in members:
                    member.save()

            return redirect(virtual_chassis.get_absolute_url())

        return render(
            request,
            "dcim/virtualchassis_edit.html",
            {
                "vc_form": vc_form,
                "formset": formset,
                "return_url": self.get_return_url(request, virtual_chassis),
            },
        )


class VirtualChassisDeleteView(generic.ObjectDeleteView):
    queryset = VirtualChassis.objects.all()


class VirtualChassisAddMemberView(ObjectPermissionRequiredMixin, GetReturnURLMixin, View):
    queryset = VirtualChassis.objects.all()

    def get_required_permission(self):
        return "dcim.change_virtualchassis"

    def get(self, request, pk):
        virtual_chassis = get_object_or_404(self.queryset, pk=pk)

        initial_data = {k: request.GET[k] for k in request.GET}
        member_select_form = forms.VCMemberSelectForm(initial=initial_data)
        membership_form = forms.DeviceVCMembershipForm(initial=initial_data)

        return render(
            request,
            "dcim/virtualchassis_add_member.html",
            {
                "virtual_chassis": virtual_chassis,
                "member_select_form": member_select_form,
                "membership_form": membership_form,
                "return_url": self.get_return_url(request, virtual_chassis),
            },
        )

    def post(self, request, pk):
        virtual_chassis = get_object_or_404(self.queryset, pk=pk)

        member_select_form = forms.VCMemberSelectForm(request.POST)

        if member_select_form.is_valid():
            device = member_select_form.cleaned_data["device"]
            device.virtual_chassis = virtual_chassis
            data = {k: request.POST[k] for k in ["vc_position", "vc_priority"]}
            membership_form = forms.DeviceVCMembershipForm(data=data, validate_vc_position=True, instance=device)

            if membership_form.is_valid():
                membership_form.save()
                msg = f'Added member <a href="{device.get_absolute_url()}">{escape(device)}</a>'
                messages.success(request, mark_safe(msg))

                if "_addanother" in request.POST:
                    return redirect(request.get_full_path())

                return redirect(self.get_return_url(request, device))

        else:
            membership_form = forms.DeviceVCMembershipForm(data=request.POST)

        return render(
            request,
            "dcim/virtualchassis_add_member.html",
            {
                "virtual_chassis": virtual_chassis,
                "member_select_form": member_select_form,
                "membership_form": membership_form,
                "return_url": self.get_return_url(request, virtual_chassis),
            },
        )


class VirtualChassisRemoveMemberView(ObjectPermissionRequiredMixin, GetReturnURLMixin, View):
    queryset = Device.objects.all()

    def get_required_permission(self):
        return "dcim.change_device"

    def get(self, request, pk):
        device = get_object_or_404(self.queryset, pk=pk, virtual_chassis__isnull=False)
        form = ConfirmationForm(initial=request.GET)

        return render(
            request,
            "dcim/virtualchassis_remove_member.html",
            {
                "device": device,
                "form": form,
                "return_url": self.get_return_url(request, device),
            },
        )

    def post(self, request, pk):
        device = get_object_or_404(self.queryset, pk=pk, virtual_chassis__isnull=False)
        form = ConfirmationForm(request.POST)

        # Protect master device from being removed
        virtual_chassis = VirtualChassis.objects.filter(master=device).first()
        if virtual_chassis is not None:
            msg = f"Unable to remove master device {escape(device)} from the virtual chassis."
            messages.error(request, mark_safe(msg))
            return redirect(device.get_absolute_url())

        if form.is_valid():
            devices = Device.objects.filter(pk=device.pk)
            for device in devices:
                device.virtual_chassis = None
                device.vc_position = None
                device.vc_priority = None
                device.save()

            msg = f"Removed {device} from virtual chassis {device.virtual_chassis}"
            messages.success(request, msg)

            return redirect(self.get_return_url(request, device))

        return render(
            request,
            "dcim/virtualchassis_remove_member.html",
            {
                "device": device,
                "form": form,
                "return_url": self.get_return_url(request, device),
            },
        )


class VirtualChassisBulkImportView(generic.BulkImportView):
    queryset = VirtualChassis.objects.all()
    table = tables.VirtualChassisTable


class VirtualChassisBulkEditView(generic.BulkEditView):
    queryset = VirtualChassis.objects.all()
    filterset = filters.VirtualChassisFilterSet
    table = tables.VirtualChassisTable
    form = forms.VirtualChassisBulkEditForm


class VirtualChassisBulkDeleteView(generic.BulkDeleteView):
    queryset = VirtualChassis.objects.all()
    filterset = filters.VirtualChassisFilterSet
    table = tables.VirtualChassisTable


#
# Power panels
#


class PowerPanelListView(generic.ObjectListView):
    queryset = PowerPanel.objects.select_related("location", "rack_group").annotate(
        power_feed_count=count_related(PowerFeed, "power_panel")
    )
    filterset = filters.PowerPanelFilterSet
    filterset_form = forms.PowerPanelFilterForm
    table = tables.PowerPanelTable


class PowerPanelView(generic.ObjectView):
    queryset = PowerPanel.objects.prefetch_related("location", "rack_group")

    def get_extra_context(self, request, instance):
        power_feeds = PowerFeed.objects.restrict(request.user).filter(power_panel=instance).select_related("rack")
        powerfeed_table = tables.PowerFeedTable(data=power_feeds, orderable=False)
        powerfeed_table.exclude = ["power_panel"]

        return {
            "powerfeed_table": powerfeed_table,
        }


class PowerPanelEditView(generic.ObjectEditView):
    queryset = PowerPanel.objects.all()
    model_form = forms.PowerPanelForm
    template_name = "dcim/powerpanel_edit.html"


class PowerPanelDeleteView(generic.ObjectDeleteView):
    queryset = PowerPanel.objects.all()


class PowerPanelBulkImportView(generic.BulkImportView):
    queryset = PowerPanel.objects.all()
    table = tables.PowerPanelTable


class PowerPanelBulkEditView(generic.BulkEditView):
    queryset = PowerPanel.objects.select_related("location", "rack_group")
    filterset = filters.PowerPanelFilterSet
    table = tables.PowerPanelTable
    form = forms.PowerPanelBulkEditForm


class PowerPanelBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerPanel.objects.select_related("location", "rack_group").annotate(
        power_feed_count=count_related(PowerFeed, "power_panel")
    )
    filterset = filters.PowerPanelFilterSet
    table = tables.PowerPanelTable


#
# Power feeds
#


class PowerFeedListView(generic.ObjectListView):
    queryset = PowerFeed.objects.all()
    filterset = filters.PowerFeedFilterSet
    filterset_form = forms.PowerFeedFilterForm
    table = tables.PowerFeedTable


class PowerFeedView(generic.ObjectView):
    queryset = PowerFeed.objects.select_related("power_panel", "rack")


class PowerFeedEditView(generic.ObjectEditView):
    queryset = PowerFeed.objects.all()
    model_form = forms.PowerFeedForm
    template_name = "dcim/powerfeed_edit.html"


class PowerFeedDeleteView(generic.ObjectDeleteView):
    queryset = PowerFeed.objects.all()


class PowerFeedBulkImportView(generic.BulkImportView):
    queryset = PowerFeed.objects.all()
    table = tables.PowerFeedTable


class PowerFeedBulkEditView(generic.BulkEditView):
    queryset = PowerFeed.objects.select_related("power_panel", "rack")
    filterset = filters.PowerFeedFilterSet
    table = tables.PowerFeedTable
    form = forms.PowerFeedBulkEditForm


class PowerFeedBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerFeed.objects.select_related("power_panel", "rack")
    filterset = filters.PowerFeedFilterSet
    table = tables.PowerFeedTable


class DeviceRedundancyGroupUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.DeviceRedundancyGroupBulkEditForm
    filterset_class = filters.DeviceRedundancyGroupFilterSet
    filterset_form_class = forms.DeviceRedundancyGroupFilterForm
    form_class = forms.DeviceRedundancyGroupForm
    queryset = (
        DeviceRedundancyGroup.objects.select_related("status")
        .prefetch_related("devices")
        .annotate(device_count=count_related(Device, "device_redundancy_group"))
    )
    serializer_class = serializers.DeviceRedundancyGroupSerializer
    table_class = tables.DeviceRedundancyGroupTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        if self.action == "retrieve" and instance:
            devices = instance.devices_sorted.restrict(request.user)
            devices_table = tables.DeviceTable(devices)
            devices_table.columns.show("device_redundancy_group_priority")
            context["devices_table"] = devices_table
        return context


class InterfaceRedundancyGroupUIViewSet(NautobotUIViewSet):
    """ViewSet for the InterfaceRedundancyGroup model."""

    bulk_update_form_class = forms.InterfaceRedundancyGroupBulkEditForm
    filterset_class = filters.InterfaceRedundancyGroupFilterSet
    filterset_form_class = forms.InterfaceRedundancyGroupFilterForm
    form_class = forms.InterfaceRedundancyGroupForm
    queryset = InterfaceRedundancyGroup.objects.select_related("status")
    queryset = queryset.prefetch_related("interfaces")
    queryset = queryset.annotate(
        interface_count=count_related(Interface, "interface_redundancy_groups"),
    )
    serializer_class = serializers.InterfaceRedundancyGroupSerializer
    table_class = tables.InterfaceRedundancyGroupTable
    lookup_field = "pk"

    def get_extra_context(self, request, instance):
        """Return additional panels for display."""
        context = super().get_extra_context(request, instance)
        if instance and self.action == "retrieve":
            interface_table = self._get_interface_redundancy_groups_table(request, instance)
            context["interface_table"] = interface_table
        return context

    def _get_interface_redundancy_groups_table(self, request, instance):
        """Return a table of assigned Interfaces."""
        queryset = instance.interface_redundancy_group_associations.restrict(request.user)
        queryset = queryset.prefetch_related("interface")
        queryset = queryset.order_by("priority")
        column_sequence = (
            "interface__device",
            "interface",
            "priority",
            "interface__status",
            "interface__enabled",
            "interface__ip_addresses",
            "interface__type",
            "interface__description",
            "interface__label",
        )
        table = tables.InterfaceRedundancyGroupAssociationTable(
            data=queryset,
            sequence=column_sequence,
            orderable=False,
        )
        for column_name in column_sequence:
            table.columns.show(column_name)
        return table


class InterfaceRedundancyGroupAssociationUIViewSet(ObjectEditViewMixin, ObjectDestroyViewMixin):
    queryset = InterfaceRedundancyGroupAssociation.objects.all()
    form_class = forms.InterfaceRedundancyGroupAssociationForm
    template_name = "dcim/interfaceredundancygroupassociation_create.html"
    lookup_field = "pk"
