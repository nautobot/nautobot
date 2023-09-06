import socket
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.clickjacking import xframe_options_sameorigin
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import GenericViewSet, ViewSet

from nautobot.circuits.models import Circuit
from nautobot.core.api.exceptions import ServiceUnavailable
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.models.querysets import count_related
from nautobot.dcim import filters
from nautobot.dcim.models import (
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
    Location,
    LocationType,
    Manufacturer,
    InventoryItem,
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
from nautobot.extras.api.views import (
    ConfigContextQuerySetMixin,
    NautobotModelViewSet,
)
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.secrets.exceptions import SecretError
from nautobot.ipam.models import Prefix, VLAN
from nautobot.virtualization.models import VirtualMachine
from . import serializers
from .exceptions import MissingFilterException


class DCIMRootView(APIRootView):
    """
    DCIM API root view
    """

    def get_view_name(self):
        return "DCIM"


# Mixins


class PathEndpointMixin:
    # TODO: the OpenAPI schema for this endpoint is wrong since it defaults to the same as "retrieve".
    @action(detail=True, url_path="trace")
    def trace(self, request, pk):
        """
        Trace a complete cable path and return each segment as a three-tuple of (termination, cable, termination).
        """
        obj = get_object_or_404(self.queryset, pk=pk)

        # Initialize the path array
        path = []

        for near_end, cable, far_end in obj.trace():
            if near_end is None:
                # Split paths
                break

            # Serialize each object
            serializer_a = get_serializer_for_model(near_end)
            x = serializer_a(near_end, context={"request": request}).data
            if cable is not None:
                y = serializers.TracedCableSerializer(cable, context={"request": request}).data
            else:
                y = None
            if far_end is not None:
                serializer_b = get_serializer_for_model(far_end)
                z = serializer_b(far_end, context={"request": request}).data
            else:
                z = None

            path.append((x, y, z))

        return Response(path)


class PassThroughPortMixin:
    @extend_schema(filters=False, responses={200: serializers.CablePathSerializer(many=True)})
    @action(detail=True, url_path="paths")
    def paths(self, request, pk):
        """
        Return all CablePaths which traverse a given pass-through port.
        """
        obj = get_object_or_404(self.queryset, pk=pk)
        cablepaths = CablePath.objects.filter(path__contains=obj).prefetch_related("origin", "destination")
        serializer = serializers.CablePathSerializer(cablepaths, context={"request": request}, many=True)

        return Response(serializer.data)


#
# Location types
#


class LocationTypeViewSet(NautobotModelViewSet):
    queryset = LocationType.objects.select_related("parent").prefetch_related("content_types")
    serializer_class = serializers.LocationTypeSerializer
    filterset_class = filters.LocationTypeFilterSet


#
# Locations
#


class LocationViewSet(NautobotModelViewSet):
    queryset = (
        Location.objects.select_related("location_type", "parent", "status", "tenant")
        .prefetch_related("tags")
        .annotate(
            device_count=count_related(Device, "location"),
            rack_count=count_related(Rack, "location"),
            prefix_count=count_related(Prefix, "location"),
            vlan_count=count_related(VLAN, "location"),
            circuit_count=count_related(Circuit, "circuit_terminations__location"),
            virtual_machine_count=count_related(VirtualMachine, "cluster__location"),
        )
    )
    serializer_class = serializers.LocationSerializer
    filterset_class = filters.LocationFilterSet


#
# Rack groups
#


class RackGroupViewSet(NautobotModelViewSet):
    queryset = RackGroup.objects.annotate(rack_count=count_related(Rack, "rack_group")).select_related("location")
    serializer_class = serializers.RackGroupSerializer
    filterset_class = filters.RackGroupFilterSet


#
# Racks
#


class RackViewSet(NautobotModelViewSet):
    queryset = (
        Rack.objects.select_related("location", "rack_group__location", "status", "role", "tenant")
        .prefetch_related("tags")
        .annotate(
            device_count=count_related(Device, "rack"),
            power_feed_count=count_related(PowerFeed, "rack"),
        )
    )
    serializer_class = serializers.RackSerializer
    filterset_class = filters.RackFilterSet

    @extend_schema(
        filters=False,
        parameters=[serializers.RackElevationDetailFilterSerializer],
        responses={200: serializers.RackUnitSerializer(many=True)},
    )
    @action(detail=True)
    @xframe_options_sameorigin
    def elevation(self, request, pk=None):
        """
        Rack elevation representing the list of rack units. Also supports rendering the elevation as an SVG.
        """
        rack = get_object_or_404(self.queryset, pk=pk)
        serializer = serializers.RackElevationDetailFilterSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["render"] == "svg":
            # Render and return the elevation as an SVG drawing with the correct content type
            drawing = rack.get_elevation_svg(
                face=data["face"],
                user=request.user,
                unit_width=data["unit_width"],
                unit_height=data["unit_height"],
                legend_width=data["legend_width"],
                include_images=data["include_images"],
                base_url=request.build_absolute_uri("/"),
                display_fullname=data["display_fullname"],
            )
            return HttpResponse(drawing.tostring(), content_type="image/svg+xml")

        else:
            # Return a JSON representation of the rack units in the elevation
            elevation = rack.get_rack_units(
                face=data["face"],
                user=request.user,
                exclude=data["exclude"],
                expand_devices=data["expand_devices"],
            )

            # Enable filtering rack units by ID
            q = data["q"]
            if q:
                elevation = [u for u in elevation if q in str(u["id"]) or q in str(u["name"])]

            page = self.paginate_queryset(elevation)
            if page is not None:
                rack_units = serializers.RackUnitSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(rack_units.data)

        return None


#
# Rack reservations
#


class RackReservationViewSet(NautobotModelViewSet):
    queryset = RackReservation.objects.select_related("rack", "user", "tenant")
    serializer_class = serializers.RackReservationSerializer
    filterset_class = filters.RackReservationFilterSet


#
# Manufacturers
#


class ManufacturerViewSet(NautobotModelViewSet):
    queryset = Manufacturer.objects.annotate(
        device_type_count=count_related(DeviceType, "manufacturer"),
        inventory_item_count=count_related(InventoryItem, "manufacturer"),
        platform_count=count_related(Platform, "manufacturer"),
    )
    serializer_class = serializers.ManufacturerSerializer
    filterset_class = filters.ManufacturerFilterSet


#
# Device types
#


class DeviceTypeViewSet(NautobotModelViewSet):
    queryset = (
        DeviceType.objects.select_related("manufacturer")
        .prefetch_related("tags")
        .annotate(device_count=count_related(Device, "device_type"))
    )
    serializer_class = serializers.DeviceTypeSerializer
    filterset_class = filters.DeviceTypeFilterSet


#
# Device type components
#


class ConsolePortTemplateViewSet(NautobotModelViewSet):
    queryset = ConsolePortTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.ConsolePortTemplateSerializer
    filterset_class = filters.ConsolePortTemplateFilterSet


class ConsoleServerPortTemplateViewSet(NautobotModelViewSet):
    queryset = ConsoleServerPortTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.ConsoleServerPortTemplateSerializer
    filterset_class = filters.ConsoleServerPortTemplateFilterSet


class PowerPortTemplateViewSet(NautobotModelViewSet):
    queryset = PowerPortTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.PowerPortTemplateSerializer
    filterset_class = filters.PowerPortTemplateFilterSet


class PowerOutletTemplateViewSet(NautobotModelViewSet):
    queryset = PowerOutletTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.PowerOutletTemplateSerializer
    filterset_class = filters.PowerOutletTemplateFilterSet


class InterfaceTemplateViewSet(NautobotModelViewSet):
    queryset = InterfaceTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.InterfaceTemplateSerializer
    filterset_class = filters.InterfaceTemplateFilterSet


class FrontPortTemplateViewSet(NautobotModelViewSet):
    queryset = FrontPortTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.FrontPortTemplateSerializer
    filterset_class = filters.FrontPortTemplateFilterSet


class RearPortTemplateViewSet(NautobotModelViewSet):
    queryset = RearPortTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.RearPortTemplateSerializer
    filterset_class = filters.RearPortTemplateFilterSet


class DeviceBayTemplateViewSet(NautobotModelViewSet):
    queryset = DeviceBayTemplate.objects.select_related("device_type__manufacturer")
    serializer_class = serializers.DeviceBayTemplateSerializer
    filterset_class = filters.DeviceBayTemplateFilterSet


#
# Platforms
#


class PlatformViewSet(NautobotModelViewSet):
    queryset = Platform.objects.annotate(
        device_count=count_related(Device, "platform"),
        virtual_machine_count=count_related(VirtualMachine, "platform"),
    )
    serializer_class = serializers.PlatformSerializer
    filterset_class = filters.PlatformFilterSet


#
# Devices
#


class DeviceViewSet(ConfigContextQuerySetMixin, NautobotModelViewSet):
    queryset = Device.objects.select_related(
        "device_type__manufacturer",
        "role",
        "tenant",
        "platform",
        "rack",
        "location",
        "parent_bay",
        "primary_ip4",
        "primary_ip6",
        "virtual_chassis__master",
        "device_redundancy_group",
        "secrets_group",
        "status",
    ).prefetch_related("tags", "primary_ip4__nat_outside_list", "primary_ip6__nat_outside_list")
    serializer_class = serializers.DeviceSerializer
    filterset_class = filters.DeviceFilterSet

    @extend_schema(
        filters=False,
        parameters=[OpenApiParameter(name="method", location="query", required=True, type=OpenApiTypes.STR)],
        responses={"200": serializers.DeviceNAPALMSerializer},
    )
    @action(detail=True, url_path="napalm")
    def napalm(self, request, pk):
        """
        Execute a NAPALM method on a Device
        """
        device = get_object_or_404(self.queryset, pk=pk)
        if device.platform is None:
            raise ServiceUnavailable("No platform is configured for this device.")
        if not device.platform.napalm_driver:
            raise ServiceUnavailable(f"No NAPALM driver is configured for this device's platform: {device.platform}.")

        # Check for primary IP address from Nautobot object
        if device.primary_ip:
            host = str(device.primary_ip.address.ip)
        else:
            # Raise exception for no IP address and no Name if device.name does not exist
            if not device.name:
                raise ServiceUnavailable(
                    "This device does not have a primary IP address or device name to lookup configured."
                )
            try:
                # Attempt to complete a DNS name resolution if no primary_ip is set
                host = socket.gethostbyname(device.name)
            except socket.gaierror:
                # Name lookup failure
                raise ServiceUnavailable(
                    f"Name lookup failure, unable to resolve IP address for {device.name}. Please set Primary IP or "
                    f"setup name resolution."
                )

        # Check that NAPALM is installed
        try:
            import napalm
            from napalm.base.exceptions import ModuleImportError
        except ModuleNotFoundError as e:
            if getattr(e, "name") == "napalm":
                raise ServiceUnavailable("NAPALM is not installed. Please see the documentation for instructions.")
            raise e

        # Validate the configured driver
        try:
            driver = napalm.get_network_driver(device.platform.napalm_driver)
        except ModuleImportError:
            raise ServiceUnavailable(
                f"NAPALM driver for platform {device.platform} not found: {device.platform.napalm_driver}."
            )

        # Verify user permission
        if not request.user.has_perm("dcim.napalm_read_device"):
            return HttpResponseForbidden()

        napalm_methods = request.GET.getlist("method")
        response = OrderedDict([(m, None) for m in napalm_methods])

        # Get NAPALM credentials for the device, or fall back to the legacy global NAPALM credentials
        if device.secrets_group:
            try:
                try:
                    username = device.secrets_group.get_secret_value(
                        SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                        SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                        obj=device,
                    )
                except ObjectDoesNotExist:
                    # No defined secret, fall through to legacy behavior
                    username = settings.NAPALM_USERNAME
                try:
                    password = device.secrets_group.get_secret_value(
                        SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                        SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
                        obj=device,
                    )
                except ObjectDoesNotExist:
                    # No defined secret, fall through to legacy behavior
                    password = settings.NAPALM_PASSWORD
            except SecretError as exc:
                raise ServiceUnavailable(f"Unable to retrieve device credentials: {exc.message}") from exc
        else:
            username = settings.NAPALM_USERNAME
            password = settings.NAPALM_PASSWORD

        optional_args = settings.NAPALM_ARGS.copy()
        if device.platform.napalm_args is not None:
            optional_args.update(device.platform.napalm_args)

        # Get NAPALM enable-secret from the device if present
        if device.secrets_group:
            # Work around inconsistent enable password arg in NAPALM drivers
            enable_password_arg = "secret"
            if device.platform.napalm_driver.lower() == "eos":
                enable_password_arg = "enable_password"
            try:
                optional_args[enable_password_arg] = device.secrets_group.get_secret_value(
                    SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                    SecretsGroupSecretTypeChoices.TYPE_SECRET,
                    obj=device,
                )
            except ObjectDoesNotExist:
                # No defined secret, this is OK
                pass
            except SecretError as exc:
                raise ServiceUnavailable(f"Unable to retrieve device credentials: {exc.message}") from exc

        # Update NAPALM parameters according to the request headers
        for header in request.headers:
            if header[:9].lower() != "x-napalm-":
                continue

            key = header[9:]
            if key.lower() == "username":
                username = request.headers[header]
            elif key.lower() == "password":
                password = request.headers[header]
            elif key:
                optional_args[key.lower()] = request.headers[header]

        # Connect to the device
        d = driver(
            hostname=host,
            username=username,
            password=password,
            timeout=settings.NAPALM_TIMEOUT,
            optional_args=optional_args,
        )
        try:
            d.open()
        except Exception as e:
            raise ServiceUnavailable(f"Error connecting to the device at {host}: {e}")

        # Validate and execute each specified NAPALM method
        for method in napalm_methods:
            if not hasattr(driver, method):
                response[method] = {"error": "Unknown NAPALM method"}
                continue
            if not method.startswith("get_"):
                response[method] = {"error": "Only get_* NAPALM methods are supported"}
                continue
            try:
                response[method] = getattr(d, method)()
            except NotImplementedError:
                response[method] = {"error": f"Method {method} not implemented for NAPALM driver {driver}"}
            except Exception as e:
                response[method] = {"error": f"Method {method} failed: {e}"}
        d.close()

        return Response(response)


#
# Device components
#


class ConsolePortViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = ConsolePort.objects.select_related("device", "cable").prefetch_related(
        "_path__destination", "_cable_peer", "tags"
    )
    serializer_class = serializers.ConsolePortSerializer
    filterset_class = filters.ConsolePortFilterSet


class ConsoleServerPortViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = ConsoleServerPort.objects.select_related("device", "cable").prefetch_related(
        "_path__destination", "_cable_peer", "tags"
    )
    serializer_class = serializers.ConsoleServerPortSerializer
    filterset_class = filters.ConsoleServerPortFilterSet


class PowerPortViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = PowerPort.objects.select_related("device", "cable").prefetch_related(
        "_path__destination", "_cable_peer", "tags"
    )
    serializer_class = serializers.PowerPortSerializer
    filterset_class = filters.PowerPortFilterSet


class PowerOutletViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = PowerOutlet.objects.select_related("device", "cable").prefetch_related(
        "_path__destination", "_cable_peer", "tags"
    )
    serializer_class = serializers.PowerOutletSerializer
    filterset_class = filters.PowerOutletFilterSet


class InterfaceViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = Interface.objects.select_related(
        "device",
        "parent_interface",
        "bridge",
        "lag",
        "status",
        "cable",
    ).prefetch_related("tags", "_path__destination", "_cable_peer", "ip_addresses")
    serializer_class = serializers.InterfaceSerializer
    filterset_class = filters.InterfaceFilterSet


class FrontPortViewSet(PassThroughPortMixin, NautobotModelViewSet):
    queryset = FrontPort.objects.select_related(
        "device__device_type__manufacturer", "rear_port", "cable"
    ).prefetch_related("tags")
    serializer_class = serializers.FrontPortSerializer
    filterset_class = filters.FrontPortFilterSet


class RearPortViewSet(PassThroughPortMixin, NautobotModelViewSet):
    queryset = RearPort.objects.select_related("device__device_type__manufacturer", "cable").prefetch_related("tags")
    serializer_class = serializers.RearPortSerializer
    filterset_class = filters.RearPortFilterSet


class DeviceBayViewSet(NautobotModelViewSet):
    queryset = DeviceBay.objects.select_related("installed_device").prefetch_related("tags")
    serializer_class = serializers.DeviceBaySerializer
    filterset_class = filters.DeviceBayFilterSet


class InventoryItemViewSet(NautobotModelViewSet):
    queryset = InventoryItem.objects.select_related("device", "manufacturer").prefetch_related("tags")
    serializer_class = serializers.InventoryItemSerializer
    filterset_class = filters.InventoryItemFilterSet


#
# Connections
# TODO: remove these in favor of using the ConsolePort/PowerPort/Interface API endpoints and/or Cable endpoint.
#


class ConsoleConnectionViewSet(ListModelMixin, GenericViewSet):
    queryset = ConsolePort.objects.select_related("device", "_path").filter(_path__destination_id__isnull=False)
    serializer_class = serializers.ConsolePortSerializer
    filterset_class = filters.ConsoleConnectionFilterSet


class PowerConnectionViewSet(ListModelMixin, GenericViewSet):
    queryset = PowerPort.objects.select_related("device", "_path").filter(_path__destination_id__isnull=False)
    serializer_class = serializers.PowerPortSerializer
    filterset_class = filters.PowerConnectionFilterSet


class InterfaceConnectionViewSet(ListModelMixin, GenericViewSet):
    queryset = Interface.objects.select_related("device", "_path").filter(
        # Avoid duplicate connections by only selecting the lower PK in a connected pair
        _path__destination_id__isnull=False,
        pk__lt=F("_path__destination_id"),
    )
    serializer_class = serializers.InterfaceConnectionSerializer
    filterset_class = filters.InterfaceConnectionFilterSet


#
# Cables
#


class CableViewSet(NautobotModelViewSet):
    queryset = Cable.objects.select_related("status").prefetch_related("termination_a", "termination_b")
    serializer_class = serializers.CableSerializer
    filterset_class = filters.CableFilterSet


#
# Virtual chassis
#


class VirtualChassisViewSet(NautobotModelViewSet):
    queryset = VirtualChassis.objects.prefetch_related("tags").annotate(
        member_count=count_related(Device, "virtual_chassis")
    )
    serializer_class = serializers.VirtualChassisSerializer
    filterset_class = filters.VirtualChassisFilterSet


#
# Power panels
#


class PowerPanelViewSet(NautobotModelViewSet):
    queryset = PowerPanel.objects.select_related("location", "rack_group").annotate(
        power_feed_count=count_related(PowerFeed, "power_panel")
    )
    serializer_class = serializers.PowerPanelSerializer
    filterset_class = filters.PowerPanelFilterSet


#
# Power feeds
#


class PowerFeedViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = PowerFeed.objects.select_related(
        "power_panel",
        "rack",
        "cable",
        "status",
    ).prefetch_related("tags", "_cable_peer", "_path__destination")
    serializer_class = serializers.PowerFeedSerializer
    filterset_class = filters.PowerFeedFilterSet


#
# Device Redundancy Groups
#


class DeviceRedundancyGroupViewSet(NautobotModelViewSet):
    queryset = DeviceRedundancyGroup.objects.select_related("status").prefetch_related("devices")
    serializer_class = serializers.DeviceRedundancyGroupSerializer
    filterset_class = filters.DeviceRedundancyGroupFilterSet


#
# Interface Redundancy Groups
#


class InterfaceRedundancyGroupViewSet(NautobotModelViewSet):
    queryset = InterfaceRedundancyGroup.objects.select_related("status").prefetch_related("interfaces")
    serializer_class = serializers.InterfaceRedundancyGroupSerializer
    filterset_class = filters.InterfaceRedundancyGroupFilterSet


class InterfaceRedundancyGroupAssociationViewSet(NautobotModelViewSet):
    queryset = InterfaceRedundancyGroupAssociation.objects.all()
    serializer_class = serializers.InterfaceRedundancyGroupAssociationSerializer
    filterset_class = filters.InterfaceRedundancyGroupAssociationFilterSet


#
# Miscellaneous
#


class ConnectedDeviceViewSet(ViewSet):
    """
    This endpoint allows a user to determine what device (if any) is connected to a given peer device and peer
    interface. This is useful in a situation where a device boots with no configuration, but can detect its neighbors
    via a protocol such as LLDP. Two query parameters must be included in the request:

    * `peer_device`: The name of the peer device
    * `peer_interface`: The name of the peer interface
    """

    permission_classes = [IsAuthenticated]
    _device_param = OpenApiParameter(
        name="peer_device",
        location="query",
        description="The name of the peer device",
        required=True,
        type=OpenApiTypes.STR,
    )
    _interface_param = OpenApiParameter(
        name="peer_interface",
        location="query",
        description="The name of the peer interface",
        required=True,
        type=OpenApiTypes.STR,
    )

    def get_view_name(self):
        return "Connected Device Locator"

    @extend_schema(
        parameters=[_device_param, _interface_param],
        responses={"200": serializers.DeviceSerializer},
    )
    def list(self, request):
        peer_device_name = request.query_params.get(self._device_param.name)
        peer_interface_name = request.query_params.get(self._interface_param.name)

        if not peer_device_name or not peer_interface_name:
            raise MissingFilterException(detail='Request must include "peer_device" and "peer_interface" filters.')

        # Determine local interface from peer interface's connection
        peer_interface = get_object_or_404(
            Interface.objects.all(),
            device__name=peer_device_name,
            name=peer_interface_name,
        )
        local_interface = peer_interface.connected_endpoint

        if local_interface is None:
            return Response()

        return Response(serializers.DeviceSerializer(local_interface.device, context={"request": request}).data)
