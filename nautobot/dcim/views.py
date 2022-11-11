import uuid
from collections import OrderedDict, namedtuple

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
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic import View
from django_tables2 import RequestConfig

from nautobot.circuits.models import Circuit
from nautobot.core.views import generic
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.extras.views import ObjectChangeLogView, ObjectConfigContextView, ObjectDynamicGroupsView
from nautobot.ipam.models import IPAddress, Prefix, Service, VLAN
from nautobot.ipam.tables import InterfaceIPAddressTable, InterfaceVLANTable
from nautobot.utilities.forms import ConfirmationForm
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.utils import csv_format, count_related
from nautobot.utilities.views import GetReturnURLMixin, ObjectPermissionRequiredMixin
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
    DeviceRole,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
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
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
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


#
# Regions
#


class RegionListView(generic.ObjectListView):
    queryset = Region.objects.add_related_count(Region.objects.all(), Site, "region", "site_count", cumulative=True)
    filterset = filters.RegionFilterSet
    filterset_form = forms.RegionFilterForm
    table = tables.RegionTable


class RegionView(generic.ObjectView):
    queryset = Region.objects.all()

    def get_extra_context(self, request, instance):

        # Sites
        # v2 TODO(jathan): Replace prefetch_related with select_related
        sites = (
            Site.objects.restrict(request.user, "view")
            .filter(region__in=instance.get_descendants(include_self=True))
            .prefetch_related("parent", "region", "tenant")
        )

        sites_table = tables.SiteTable(sites)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(sites_table)

        return {
            "sites_table": sites_table,
        }


class RegionEditView(generic.ObjectEditView):
    queryset = Region.objects.all()
    model_form = forms.RegionForm


class RegionDeleteView(generic.ObjectDeleteView):
    queryset = Region.objects.all()


class RegionBulkImportView(generic.BulkImportView):
    queryset = Region.objects.all()
    model_form = forms.RegionCSVForm
    table = tables.RegionTable


class RegionBulkDeleteView(generic.BulkDeleteView):
    queryset = Region.objects.add_related_count(Region.objects.all(), Site, "region", "site_count", cumulative=True)
    filterset = filters.RegionFilterSet
    table = tables.RegionTable


#
# Sites
#


class SiteListView(generic.ObjectListView):
    queryset = Site.objects.all()
    filterset = filters.SiteFilterSet
    filterset_form = forms.SiteFilterForm
    table = tables.SiteTable


class SiteView(generic.ObjectView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Site.objects.prefetch_related("region", "tenant__group")

    def get_extra_context(self, request, instance):
        stats = {
            "rack_count": Rack.objects.restrict(request.user, "view").filter(site=instance).count(),
            "device_count": Device.objects.restrict(request.user, "view").filter(site=instance).count(),
            "prefix_count": Prefix.objects.restrict(request.user, "view").filter(site=instance).count(),
            "vlan_count": VLAN.objects.restrict(request.user, "view").filter(site=instance).count(),
            "circuit_count": Circuit.objects.restrict(request.user, "view").filter(terminations__site=instance).count(),
            "vm_count": VirtualMachine.objects.restrict(request.user, "view").filter(cluster__site=instance).count(),
        }
        rack_groups = (
            RackGroup.objects.add_related_count(RackGroup.objects.all(), Rack, "group", "rack_count", cumulative=True)
            .restrict(request.user, "view")
            .filter(site=instance)
        )
        # v2 TODO(jathan): Replace prefetch_related with select_related
        locations = (
            Location.objects.restrict(request.user, "view")
            .filter(site=instance)
            .prefetch_related("parent", "location_type")
        )

        locations_table = tables.LocationTable(locations)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(locations_table)

        return {
            "locations_table": locations_table,
            "stats": stats,
            "rack_groups": rack_groups,
        }


class SiteEditView(generic.ObjectEditView):
    queryset = Site.objects.all()
    model_form = forms.SiteForm
    template_name = "dcim/site_edit.html"


class SiteDeleteView(generic.ObjectDeleteView):
    queryset = Site.objects.all()


class SiteBulkImportView(generic.BulkImportView):
    queryset = Site.objects.all()
    model_form = forms.SiteCSVForm
    table = tables.SiteTable


class SiteBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Site.objects.prefetch_related("region", "tenant")
    filterset = filters.SiteFilterSet
    table = tables.SiteTable
    form = forms.SiteBulkEditForm


class SiteBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Site.objects.prefetch_related("region", "tenant")
    filterset = filters.SiteFilterSet
    table = tables.SiteTable


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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        children = (
            LocationType.objects.restrict(request.user, "view").filter(parent=instance).prefetch_related("parent")
        )
        # v2 TODO(jathan): Replace prefetch_related with select_related
        locations = (
            Location.objects.restrict(request.user, "view")
            .filter(location_type=instance)
            .prefetch_related("parent", "location_type")
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
    model_form = forms.LocationTypeCSVForm
    table = tables.LocationTypeTable


class LocationTypeBulkDeleteView(generic.BulkDeleteView):
    queryset = LocationType.objects.all()
    filterset = filters.LocationTypeFilterSet
    table = tables.LocationTypeTable


#
# Locations
#


class LocationListView(generic.ObjectListView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Location.objects.prefetch_related("location_type", "parent", "site", "tenant")
    filterset = filters.LocationFilterSet
    filterset_form = forms.LocationFilterForm
    table = tables.LocationTable


class LocationView(generic.ObjectView):
    queryset = Location.objects.all()

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
            .filter(terminations__location__in=related_locations)
            .count(),
            "vm_count": VirtualMachine.objects.restrict(request.user, "view")
            .filter(cluster__location__in=related_locations)
            .count(),
        }
        rack_groups = (
            RackGroup.objects.add_related_count(RackGroup.objects.all(), Rack, "group", "rack_count", cumulative=True)
            .restrict(request.user, "view")
            .filter(location__in=related_locations)
        )
        # v2 TODO(jathan): Replace prefetch_related with select_related
        children = (
            Location.objects.restrict(request.user, "view")
            .filter(parent=instance)
            .prefetch_related("parent", "location_type")
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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Location.objects.prefetch_related("location_type", "parent", "site", "tenant")
    filterset = filters.LocationFilterSet
    table = tables.LocationTable
    form = forms.LocationBulkEditForm


class LocationBulkImportView(generic.BulkImportView):
    queryset = Location.objects.all()
    model_form = forms.LocationCSVForm
    table = tables.LocationTable


class LocationBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Location.objects.prefetch_related("location_type", "parent", "site", "tenant")
    filterset = filters.LocationFilterSet
    table = tables.LocationTable


#
# Rack groups
#


class RackGroupListView(generic.ObjectListView):
    queryset = RackGroup.objects.add_related_count(
        RackGroup.objects.all(), Rack, "group", "rack_count", cumulative=True
    )
    filterset = filters.RackGroupFilterSet
    filterset_form = forms.RackGroupFilterForm
    table = tables.RackGroupTable


class RackGroupView(generic.ObjectView):
    queryset = RackGroup.objects.all()

    def get_extra_context(self, request, instance):

        # Racks
        # v2 TODO(jathan): Replace prefetch_related with select_related
        racks = (
            Rack.objects.restrict(request.user, "view")
            .filter(group__in=instance.get_descendants(include_self=True))
            .prefetch_related("role", "site", "tenant")
        )

        rack_table = tables.RackTable(racks)
        rack_table.columns.hide("group")

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
    model_form = forms.RackGroupCSVForm
    table = tables.RackGroupTable


class RackGroupBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = RackGroup.objects.add_related_count(
        RackGroup.objects.all(), Rack, "group", "rack_count", cumulative=True
    ).prefetch_related("site")
    filterset = filters.RackGroupFilterSet
    table = tables.RackGroupTable


#
# Rack roles
#


class RackRoleListView(generic.ObjectListView):
    queryset = RackRole.objects.annotate(rack_count=count_related(Rack, "role"))
    filterset = filters.RackRoleFilterSet
    table = tables.RackRoleTable


class RackRoleView(generic.ObjectView):
    queryset = RackRole.objects.all()

    def get_extra_context(self, request, instance):

        # Racks
        # v2 TODO(jathan): Replace prefetch_related with select_related
        racks = (
            Rack.objects.restrict(request.user, "view")
            .filter(role=instance)
            .prefetch_related("group", "site", "tenant")
        )

        rack_table = tables.RackTable(racks)
        rack_table.columns.hide("role")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(rack_table)

        return {
            "rack_table": rack_table,
        }


class RackRoleEditView(generic.ObjectEditView):
    queryset = RackRole.objects.all()
    model_form = forms.RackRoleForm


class RackRoleDeleteView(generic.ObjectDeleteView):
    queryset = RackRole.objects.all()


class RackRoleBulkImportView(generic.BulkImportView):
    queryset = RackRole.objects.all()
    model_form = forms.RackRoleCSVForm
    table = tables.RackRoleTable


class RackRoleBulkDeleteView(generic.BulkDeleteView):
    queryset = RackRole.objects.annotate(rack_count=count_related(Rack, "role"))
    table = tables.RackRoleTable


#
# Racks
#


class RackListView(generic.ObjectListView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Rack.objects.prefetch_related("site", "group", "tenant", "role", "devices__device_type").annotate(
        device_count=count_related(Device, "rack")
    )
    filterset = filters.RackFilterSet
    filterset_form = forms.RackFilterForm
    table = tables.RackDetailTable


class RackElevationListView(generic.ObjectListView):
    """
    Display a set of rack elevations side-by-side.
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Rack.objects.prefetch_related("role")
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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Rack.objects.prefetch_related("site__region", "tenant__group", "group", "role")

    def get_extra_context(self, request, instance):
        # Get 0U and child devices located within the rack
        # v2 TODO(jathan): Replace prefetch_related with select_related
        nonracked_devices = Device.objects.filter(rack=instance, position__isnull=True).prefetch_related(
            "device_type__manufacturer"
        )

        peer_racks = Rack.objects.restrict(request.user, "view").filter(site=instance.site)

        if instance.group:
            peer_racks = peer_racks.filter(group=instance.group)
        else:
            peer_racks = peer_racks.filter(group__isnull=True)
        next_rack = peer_racks.filter(name__gt=instance.name).order_by("name").first()
        prev_rack = peer_racks.filter(name__lt=instance.name).order_by("-name").first()

        reservations = RackReservation.objects.restrict(request.user, "view").filter(rack=instance)
        # v2 TODO(jathan): Replace prefetch_related with select_related
        power_feeds = (
            PowerFeed.objects.restrict(request.user, "view").filter(rack=instance).prefetch_related("power_panel")
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
    model_form = forms.RackCSVForm
    table = tables.RackTable


class RackBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Rack.objects.prefetch_related("site", "group", "tenant", "role")
    filterset = filters.RackFilterSet
    table = tables.RackTable
    form = forms.RackBulkEditForm


class RackBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Rack.objects.prefetch_related("site", "group", "tenant", "role")
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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = RackReservation.objects.prefetch_related("rack")


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
    model_form = forms.RackReservationCSVForm
    table = tables.RackReservationTable

    def _save_obj(self, obj_form, request):
        """
        Assign the currently authenticated user to the RackReservation.
        """
        instance = obj_form.save(commit=False)
        instance.user = request.user
        instance.save()

        return instance


class RackReservationBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = RackReservation.objects.prefetch_related("rack", "user")
    filterset = filters.RackReservationFilterSet
    table = tables.RackReservationTable
    form = forms.RackReservationBulkEditForm


class RackReservationBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = RackReservation.objects.prefetch_related("rack", "user")
    filterset = filters.RackReservationFilterSet
    table = tables.RackReservationTable


#
# Manufacturers
#


class ManufacturerListView(generic.ObjectListView):
    queryset = Manufacturer.objects.annotate(
        devicetype_count=count_related(DeviceType, "manufacturer"),
        inventoryitem_count=count_related(InventoryItem, "manufacturer"),
        platform_count=count_related(Platform, "manufacturer"),
    )
    filterset = filters.ManufacturerFilterSet
    table = tables.ManufacturerTable


class ManufacturerView(generic.ObjectView):
    queryset = Manufacturer.objects.all()

    def get_extra_context(self, request, instance):

        # Devices
        # v2 TODO(jathan): Replace prefetch_related with select_related
        devices = (
            Device.objects.restrict(request.user, "view")
            .filter(device_type__manufacturer=instance)
            .prefetch_related("status", "site", "tenant", "device_role", "rack", "device_type")
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
    model_form = forms.ManufacturerCSVForm
    table = tables.ManufacturerTable


class ManufacturerBulkDeleteView(generic.BulkDeleteView):
    queryset = Manufacturer.objects.annotate(devicetype_count=count_related(DeviceType, "manufacturer"))
    table = tables.ManufacturerTable


#
# Device types
#


class DeviceTypeListView(generic.ObjectListView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DeviceType.objects.prefetch_related("manufacturer").annotate(
        instance_count=count_related(Device, "device_type")
    )
    filterset = filters.DeviceTypeFilterSet
    filterset_form = forms.DeviceTypeFilterForm
    table = tables.DeviceTypeTable


class DeviceTypeView(generic.ObjectView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DeviceType.objects.prefetch_related("manufacturer")

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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DeviceType.objects.prefetch_related("manufacturer").annotate(
        instance_count=count_related(Device, "device_type")
    )
    filterset = filters.DeviceTypeFilterSet
    table = tables.DeviceTypeTable
    form = forms.DeviceTypeBulkEditForm


class DeviceTypeBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DeviceType.objects.prefetch_related("manufacturer").annotate(
        instance_count=count_related(Device, "device_type")
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


class ConsolePortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = ConsolePortTemplate.objects.all()


class ConsolePortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = ConsolePortTemplate.objects.all()
    table = tables.ConsolePortTemplateTable


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


class ConsoleServerPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = ConsoleServerPortTemplate.objects.all()


class ConsoleServerPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = ConsoleServerPortTemplate.objects.all()
    table = tables.ConsoleServerPortTemplateTable


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


class PowerPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = PowerPortTemplate.objects.all()


class PowerPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerPortTemplate.objects.all()
    table = tables.PowerPortTemplateTable


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


class PowerOutletTemplateBulkRenameView(generic.BulkRenameView):
    queryset = PowerOutletTemplate.objects.all()


class PowerOutletTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = PowerOutletTemplate.objects.all()
    table = tables.PowerOutletTemplateTable


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


class InterfaceTemplateBulkRenameView(generic.BulkRenameView):
    queryset = InterfaceTemplate.objects.all()


class InterfaceTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = InterfaceTemplate.objects.all()
    table = tables.InterfaceTemplateTable


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


class FrontPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = FrontPortTemplate.objects.all()


class FrontPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = FrontPortTemplate.objects.all()
    table = tables.FrontPortTemplateTable


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


class RearPortTemplateBulkRenameView(generic.BulkRenameView):
    queryset = RearPortTemplate.objects.all()


class RearPortTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = RearPortTemplate.objects.all()
    table = tables.RearPortTemplateTable


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


class DeviceBayTemplateBulkRenameView(generic.BulkRenameView):
    queryset = DeviceBayTemplate.objects.all()


class DeviceBayTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = DeviceBayTemplate.objects.all()
    table = tables.DeviceBayTemplateTable


#
# Device roles
#


class DeviceRoleListView(generic.ObjectListView):
    queryset = DeviceRole.objects.annotate(
        device_count=count_related(Device, "device_role"),
        vm_count=count_related(VirtualMachine, "role"),
    )
    filterset = filters.DeviceRoleFilterSet
    table = tables.DeviceRoleTable


class DeviceRoleView(generic.ObjectView):
    queryset = DeviceRole.objects.all()

    def get_extra_context(self, request, instance):

        # Devices
        # v2 TODO(jathan): Replace prefetch_related with select_related
        devices = (
            Device.objects.restrict(request.user, "view")
            .filter(device_role=instance)
            .prefetch_related("status", "site", "tenant", "rack", "device_type")
        )

        device_table = tables.DeviceTable(devices)
        device_table.columns.hide("device_role")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(device_table)

        return {
            "device_table": device_table,
        }


class DeviceRoleEditView(generic.ObjectEditView):
    queryset = DeviceRole.objects.all()
    model_form = forms.DeviceRoleForm


class DeviceRoleDeleteView(generic.ObjectDeleteView):
    queryset = DeviceRole.objects.all()


class DeviceRoleBulkImportView(generic.BulkImportView):
    queryset = DeviceRole.objects.all()
    model_form = forms.DeviceRoleCSVForm
    table = tables.DeviceRoleTable


class DeviceRoleBulkDeleteView(generic.BulkDeleteView):
    queryset = DeviceRole.objects.all()
    table = tables.DeviceRoleTable


#
# Platforms
#


class PlatformListView(generic.ObjectListView):
    queryset = Platform.objects.annotate(
        device_count=count_related(Device, "platform"),
        vm_count=count_related(VirtualMachine, "platform"),
    )
    filterset = filters.PlatformFilterSet
    table = tables.PlatformTable


class PlatformView(generic.ObjectView):
    queryset = Platform.objects.all()

    def get_extra_context(self, request, instance):

        # Devices
        # v2 TODO(jathan): Replace prefetch_related with select_related
        devices = (
            Device.objects.restrict(request.user, "view")
            .filter(platform=instance)
            .prefetch_related("status", "site", "tenant", "rack", "device_type", "device_role")
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


class PlatformEditView(generic.ObjectEditView):
    queryset = Platform.objects.all()
    model_form = forms.PlatformForm


class PlatformDeleteView(generic.ObjectDeleteView):
    queryset = Platform.objects.all()


class PlatformBulkImportView(generic.BulkImportView):
    queryset = Platform.objects.all()
    model_form = forms.PlatformCSVForm
    table = tables.PlatformTable


class PlatformBulkDeleteView(generic.BulkDeleteView):
    queryset = Platform.objects.all()
    table = tables.PlatformTable


#
# Devices
#


class DeviceListView(generic.ObjectListView):
    queryset = Device.objects.all()
    filterset = filters.DeviceFilterSet
    filterset_form = forms.DeviceFilterForm
    table = tables.DeviceTable
    template_name = "dcim/device_list.html"


class DeviceView(generic.ObjectView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Device.objects.prefetch_related(
        "site__region",
        "rack__group",
        "tenant__group",
        "device_role",
        "platform",
        "primary_ip4",
        "primary_ip6",
        "status",
    )

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

        return {
            "services": services,
            "vc_members": vc_members,
            "active_tab": "device",
        }


class DeviceConsolePortsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = "dcim/device/consoleports.html"

    def get_extra_context(self, request, instance):
        # v2 TODO(jathan): Replace prefetch_related with select_related
        consoleports = (
            ConsolePort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related(
                "cable",
                "_path__destination",
            )
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        consoleserverports = (
            ConsoleServerPort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related(
                "cable",
                "_path__destination",
            )
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        powerports = (
            PowerPort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related(
                "cable",
                "_path__destination",
            )
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        poweroutlets = (
            PowerOutlet.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related(
                "cable",
                "power_port",
                "_path__destination",
            )
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
        # v2 TODO(jathan): Replace prefetch_related with select_related (except
        # tags/ip_address/member_interfaces: m2m)
        interfaces = instance.vc_interfaces.restrict(request.user, "view").prefetch_related(
            Prefetch("ip_addresses", queryset=IPAddress.objects.restrict(request.user)),
            Prefetch("member_interfaces", queryset=Interface.objects.restrict(request.user)),
            "lag",
            "cable",
            "_path__destination",
            "tags",
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        frontports = (
            FrontPort.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related(
                "rear_port",
                "cable",
            )
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        rearports = RearPort.objects.restrict(request.user, "view").filter(device=instance).prefetch_related("cable")
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        devicebays = (
            DeviceBay.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related(
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        inventoryitems = (
            InventoryItem.objects.restrict(request.user, "view")
            .filter(device=instance)
            .prefetch_related("manufacturer")
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
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
    queryset = Device.objects.annotate_config_context_data()
    base_template = "dcim/device/base.html"


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
    model_form = forms.DeviceCSVForm
    table = tables.DeviceImportTable
    template_name = "dcim/device_import.html"


class ChildDeviceBulkImportView(generic.BulkImportView):
    queryset = Device.objects.all()
    model_form = forms.ChildDeviceCSVForm
    table = tables.DeviceImportTable
    template_name = "dcim/device_import_child.html"

    def _save_obj(self, obj_form, request):

        obj = obj_form.save()

        # Save the reverse relation to the parent device bay
        device_bay = obj.parent_bay
        device_bay.installed_device = obj
        device_bay.save()

        return obj


class DeviceBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Device.objects.prefetch_related(
        "tenant", "site", "rack", "device_role", "device_type__manufacturer", "secrets_group", "device_redundancy_group"
    )
    filterset = filters.DeviceFilterSet
    table = tables.DeviceTable
    form = forms.DeviceBulkEditForm


class DeviceBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Device.objects.prefetch_related("tenant", "site", "rack", "device_role", "device_type__manufacturer")
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
    model_form = forms.ConsolePortCSVForm
    table = tables.ConsolePortTable


class ConsolePortBulkEditView(generic.BulkEditView):
    queryset = ConsolePort.objects.all()
    filterset = filters.ConsolePortFilterSet
    table = tables.ConsolePortTable
    form = forms.ConsolePortBulkEditForm


class ConsolePortBulkRenameView(generic.BulkRenameView):
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
    model_form = forms.ConsoleServerPortCSVForm
    table = tables.ConsoleServerPortTable


class ConsoleServerPortBulkEditView(generic.BulkEditView):
    queryset = ConsoleServerPort.objects.all()
    filterset = filters.ConsoleServerPortFilterSet
    table = tables.ConsoleServerPortTable
    form = forms.ConsoleServerPortBulkEditForm


class ConsoleServerPortBulkRenameView(generic.BulkRenameView):
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
    model_form = forms.PowerPortCSVForm
    table = tables.PowerPortTable


class PowerPortBulkEditView(generic.BulkEditView):
    queryset = PowerPort.objects.all()
    filterset = filters.PowerPortFilterSet
    table = tables.PowerPortTable
    form = forms.PowerPortBulkEditForm


class PowerPortBulkRenameView(generic.BulkRenameView):
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
    model_form = forms.PowerOutletCSVForm
    table = tables.PowerOutletTable


class PowerOutletBulkEditView(generic.BulkEditView):
    queryset = PowerOutlet.objects.all()
    filterset = filters.PowerOutletFilterSet
    table = tables.PowerOutletTable
    form = forms.PowerOutletBulkEditForm


class PowerOutletBulkRenameView(generic.BulkRenameView):
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        ipaddress_table = InterfaceIPAddressTable(
            data=instance.ip_addresses.restrict(request.user, "view").prefetch_related("vrf", "tenant"),
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

        # v2 TODO(jathan): Replace prefetch_related with select_related
        for vlan in instance.tagged_vlans.restrict(request.user).prefetch_related("site", "group", "tenant", "role"):
            vlan.tagged = True
            vlans.append(vlan)
        vlan_table = InterfaceVLANTable(interface=instance, data=vlans, orderable=False)

        return {
            "ipaddress_table": ipaddress_table,
            "vlan_table": vlan_table,
            "breadcrumb_url": "dcim:device_interfaces",
            "child_interfaces_table": child_interfaces_tables,
        }


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
    model_form = forms.InterfaceCSVForm
    table = tables.InterfaceTable


class InterfaceBulkEditView(generic.BulkEditView):
    queryset = Interface.objects.all()
    filterset = filters.InterfaceFilterSet
    table = tables.InterfaceTable
    form = forms.InterfaceBulkEditForm


class InterfaceBulkRenameView(generic.BulkRenameView):
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
    model_form = forms.FrontPortCSVForm
    table = tables.FrontPortTable


class FrontPortBulkEditView(generic.BulkEditView):
    queryset = FrontPort.objects.all()
    filterset = filters.FrontPortFilterSet
    table = tables.FrontPortTable
    form = forms.FrontPortBulkEditForm


class FrontPortBulkRenameView(generic.BulkRenameView):
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
    model_form = forms.RearPortCSVForm
    table = tables.RearPortTable


class RearPortBulkEditView(generic.BulkEditView):
    queryset = RearPort.objects.all()
    filterset = filters.RearPortFilterSet
    table = tables.RearPortTable
    form = forms.RearPortBulkEditForm


class RearPortBulkRenameView(generic.BulkRenameView):
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
                f"{removed_device,} has been removed from {device_bay}.",
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
    model_form = forms.DeviceBayCSVForm
    table = tables.DeviceBayTable


class DeviceBayBulkEditView(generic.BulkEditView):
    queryset = DeviceBay.objects.all()
    filterset = filters.DeviceBayFilterSet
    table = tables.DeviceBayTable
    form = forms.DeviceBayBulkEditForm


class DeviceBayBulkRenameView(generic.BulkRenameView):
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
    model_form = forms.InventoryItemCSVForm
    table = tables.InventoryItemTable


class InventoryItemBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = InventoryItem.objects.prefetch_related("device", "manufacturer")
    filterset = filters.InventoryItemFilterSet
    table = tables.InventoryItemTable
    form = forms.InventoryItemBulkEditForm


class InventoryItemBulkRenameView(generic.BulkRenameView):
    queryset = InventoryItem.objects.all()


class InventoryItemBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = InventoryItem.objects.prefetch_related("device", "manufacturer")
    table = tables.InventoryItemTable
    template_name = "dcim/inventoryitem_bulk_delete.html"


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
            # v2 TODO(jathan): Replace prefetch_related with select_related
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

        # Set initial site and rack based on side A termination (if not already set)
        termination_a_site = getattr(obj.termination_a.parent, "site", None)
        if termination_a_site and "termination_b_region" not in initial_data:
            initial_data["termination_b_region"] = termination_a_site.region
        if "termination_b_site" not in initial_data:
            initial_data["termination_b_site"] = termination_a_site
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
    model_form = forms.CableCSVForm
    table = tables.CableTable


class CableBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Cable.objects.prefetch_related("termination_a", "termination_b")
    filterset = filters.CableFilterSet
    table = tables.CableTable
    form = forms.CableBulkEditForm


class CableBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Cable.objects.prefetch_related("termination_a", "termination_b")
    filterset = filters.CableFilterSet
    table = tables.CableTable


#
# Connections
#


class ConnectionsListView(generic.ObjectListView):

    CSVRow = namedtuple("CSVRow", ["device", "name", "dest_device", "dest_name", "reachable"])

    def queryset_to_csv_body_data(self):
        """
        The headers may differ from view to view but the formatting of the CSV data is the same.
        """
        csv_body_data = []
        for obj in self.queryset:
            # The connected endpoint may or may not be associated with a Device (e.g., CircuitTerminations are not)
            # and may or may not have a name of its own (e.g., CircuitTerminations do not)
            dest_device = None
            dest_name = None
            if obj.connected_endpoint:
                if hasattr(obj.connected_endpoint, "device"):
                    dest_device = obj.connected_endpoint.device.identifier
                if hasattr(obj.connected_endpoint, "name"):
                    dest_name = obj.connected_endpoint.name

            # In the case where a connection exists between two like endpoints,
            # for consistency of output we want to ensure that it's always represented as
            # ("device a", "interface a", "device b", "interface b") rather than
            # ("device b", "interface b", "device a", "interface a")
            if obj.__class__ == obj.connected_endpoint.__class__ and (
                obj.device.identifier > obj.connected_endpoint.device.identifier
                or (
                    obj.device.identifier == obj.connected_endpoint.device.identifier
                    and obj.name > obj.connected_endpoint.name
                )
            ):
                # Swap the two endpoints around for consistent output as described above
                row = self.CSVRow(
                    device=dest_device,
                    name=dest_name,
                    dest_device=obj.device.identifier,
                    dest_name=obj.name,
                    reachable=str(obj.path.is_active),
                )
            else:
                # Existing order of endpoints is fine and correct
                row = self.CSVRow(
                    device=obj.device.identifier,
                    name=obj.name,
                    dest_device=dest_device,
                    dest_name=dest_name,
                    reachable=str(obj.path.is_active),
                )

            csv_body_data.append(csv_format(row))

        return sorted(csv_body_data)


class ConsoleConnectionsListView(ConnectionsListView):
    queryset = ConsolePort.objects.filter(_path__isnull=False)
    filterset = filters.ConsoleConnectionFilterSet
    filterset_form = forms.ConsoleConnectionFilterForm
    table = tables.ConsoleConnectionTable
    action_buttons = ("export",)

    def queryset_to_csv(self):
        csv_data = [
            # Headers
            ",".join(["device", "console_port", "console_server", "port", "reachable"])
        ]
        csv_data.extend(self.queryset_to_csv_body_data())

        return "\n".join(csv_data)

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
    action_buttons = ("export",)

    def queryset_to_csv(self):
        csv_data = [
            # Headers
            ",".join(["device", "power_port", "pdu", "outlet", "reachable"])
        ]
        csv_data.extend(self.queryset_to_csv_body_data())

        return "\n".join(csv_data)

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
            # The below at least ensures uniqueness, but doesn't guarantee whether we get (A, B) or (B, A);
            # we fix it up to be consistently (A, B) in queryset_to_csv_body_data().
            # TODO: this is very problematic when filtering the view via FilterSet - if the filterset matches (A), then
            #       the connection will appear in the table, but if it only matches (B) then the connection will not!
            _path__destination_type=ContentType.objects.get_for_model(Interface),
            pk__lt=F("_path__destination_id"),
        )
        if self.queryset is None:
            self.queryset = qs

        return self.queryset

    def queryset_to_csv(self):
        csv_data = [
            # Headers
            ",".join(["device_a", "interface_a", "device_b", "interface_b", "reachable"])
        ]
        csv_data.extend(self.queryset_to_csv_body_data())

        return "\n".join(csv_data)

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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = VirtualChassis.objects.prefetch_related("master").annotate(
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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        members_queryset = virtual_chassis.members.prefetch_related("rack").order_by("vc_position")

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
        # v2 TODO(jathan): Replace prefetch_related with select_related
        members_queryset = virtual_chassis.members.prefetch_related("rack").order_by("vc_position")

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
    model_form = forms.VirtualChassisCSVForm
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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = PowerPanel.objects.prefetch_related("site", "rack_group").annotate(
        powerfeed_count=count_related(PowerFeed, "power_panel")
    )
    filterset = filters.PowerPanelFilterSet
    filterset_form = forms.PowerPanelFilterForm
    table = tables.PowerPanelTable


class PowerPanelView(generic.ObjectView):
    queryset = PowerPanel.objects.prefetch_related("site", "rack_group")

    def get_extra_context(self, request, instance):
        # v2 TODO(jathan): Replace prefetch_related with select_related
        power_feeds = PowerFeed.objects.restrict(request.user).filter(power_panel=instance).prefetch_related("rack")
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
    model_form = forms.PowerPanelCSVForm
    table = tables.PowerPanelTable


class PowerPanelBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = PowerPanel.objects.prefetch_related("site", "rack_group")
    filterset = filters.PowerPanelFilterSet
    table = tables.PowerPanelTable
    form = forms.PowerPanelBulkEditForm


class PowerPanelBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = PowerPanel.objects.prefetch_related("site", "rack_group").annotate(
        powerfeed_count=count_related(PowerFeed, "power_panel")
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
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = PowerFeed.objects.prefetch_related("power_panel", "rack")


class PowerFeedEditView(generic.ObjectEditView):
    queryset = PowerFeed.objects.all()
    model_form = forms.PowerFeedForm
    template_name = "dcim/powerfeed_edit.html"


class PowerFeedDeleteView(generic.ObjectDeleteView):
    queryset = PowerFeed.objects.all()


class PowerFeedBulkImportView(generic.BulkImportView):
    queryset = PowerFeed.objects.all()
    model_form = forms.PowerFeedCSVForm
    table = tables.PowerFeedTable


class PowerFeedBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = PowerFeed.objects.prefetch_related("power_panel", "rack")
    filterset = filters.PowerFeedFilterSet
    table = tables.PowerFeedTable
    form = forms.PowerFeedBulkEditForm


class PowerFeedBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = PowerFeed.objects.prefetch_related("power_panel", "rack")
    filterset = filters.PowerFeedFilterSet
    table = tables.PowerFeedTable


class DeviceRedundancyGroupUIViewSet(NautobotUIViewSet):
    bulk_create_form_class = forms.DeviceRedundancyGroupCSVForm
    bulk_update_form_class = forms.DeviceRedundancyGroupBulkEditForm
    filterset_class = filters.DeviceRedundancyGroupFilterSet
    filterset_form_class = forms.DeviceRedundancyGroupFilterForm
    form_class = forms.DeviceRedundancyGroupForm
    queryset = (
        DeviceRedundancyGroup.objects.select_related("status")
        .prefetch_related("members")
        .annotate(member_count=count_related(Device, "device_redundancy_group"))
    )
    serializer_class = serializers.DeviceRedundancyGroupSerializer
    table_class = tables.DeviceRedundancyGroupTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        if self.action == "retrieve" and instance:
            members = instance.members_sorted.restrict(request.user)
            members_table = tables.DeviceTable(members)
            members_table.columns.show("device_redundancy_group_priority")
            context["members_table"] = members_table
        return context
