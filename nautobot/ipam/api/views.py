from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.serializers import IntegerField, ListSerializer

from nautobot.core.api.authentication import TokenPermissions
from nautobot.core.models.querysets import count_related
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.models import Location
from nautobot.extras.api.views import NautobotModelViewSet
from nautobot.ipam import filters
from nautobot.ipam.api import serializers
from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    PrefixLocationAssignment,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VLANLocationAssignment,
    VRF,
    VRFDeviceAssignment,
    VRFPrefixAssignment,
)

#
# Namespace
#


class NamespaceViewSet(NautobotModelViewSet):
    queryset = Namespace.objects.all()
    serializer_class = serializers.NamespaceSerializer
    filterset_class = filters.NamespaceFilterSet


#
# VRFs
#


class VRFViewSet(NautobotModelViewSet):
    queryset = VRF.objects.select_related("namespace", "tenant").prefetch_related(
        "devices", "virtual_machines", "prefixes", "import_targets", "export_targets", "tags"
    )
    serializer_class = serializers.VRFSerializer
    filterset_class = filters.VRFFilterSet


class VRFDeviceAssignmentViewSet(NautobotModelViewSet):
    queryset = VRFDeviceAssignment.objects.select_related("vrf", "device", "virtual_machine")
    serializer_class = serializers.VRFDeviceAssignmentSerializer
    filterset_class = filters.VRFDeviceAssignmentFilterSet


class VRFPrefixAssignmentViewSet(NautobotModelViewSet):
    queryset = VRFPrefixAssignment.objects.select_related("vrf", "prefix")
    serializer_class = serializers.VRFPrefixAssignmentSerializer
    filterset_class = filters.VRFPrefixAssignmentFilterSet


#
# Route targets
#


class RouteTargetViewSet(NautobotModelViewSet):
    queryset = RouteTarget.objects.select_related("tenant").prefetch_related("tags")
    serializer_class = serializers.RouteTargetSerializer
    filterset_class = filters.RouteTargetFilterSet


#
# RIRs
#


class RIRViewSet(NautobotModelViewSet):
    queryset = RIR.objects.annotate(assigned_prefix_count=count_related(Prefix, "rir"))
    serializer_class = serializers.RIRSerializer
    filterset_class = filters.RIRFilterSet


#
# Prefixes
#


@extend_schema_view(
    bulk_update=extend_schema(
        responses={"200": serializers.PrefixLegacySerializer(many=True)}, versions=["2.0", "2.1"]
    ),
    bulk_partial_update=extend_schema(
        responses={"200": serializers.PrefixLegacySerializer(many=True)}, versions=["2.0", "2.1"]
    ),
    create=extend_schema(responses={"201": serializers.PrefixLegacySerializer}, versions=["2.0", "2.1"]),
    list=extend_schema(responses={"200": serializers.PrefixLegacySerializer(many=True)}, versions=["2.0", "2.1"]),
    partial_update=extend_schema(responses={"200": serializers.PrefixLegacySerializer}, versions=["2.0", "2.1"]),
    retrieve=extend_schema(responses={"200": serializers.PrefixLegacySerializer}, versions=["2.0", "2.1"]),
    update=extend_schema(responses={"200": serializers.PrefixLegacySerializer}, versions=["2.0", "2.1"]),
)
class PrefixViewSet(NautobotModelViewSet):
    queryset = Prefix.objects.select_related(
        "namespace",
        "parent",
        "rir",
        "role",
        "status",
        "tenant",
        "vlan",
    ).prefetch_related("locations", "tags")
    serializer_class = serializers.PrefixSerializer
    filterset_class = filters.PrefixFilterSet

    def get_serializer_class(self):
        if (
            not getattr(self, "swagger_fake_view", False)
            and self.request.major_version == 2
            and self.request.minor_version < 2
        ):
            # API version 2.0 or 2.1 - use the legacy serializer
            return serializers.PrefixLegacySerializer
        return super().get_serializer_class()

    class LocationIncompatibleLegacyBehavior(APIException):
        status_code = 412
        default_detail = (
            "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
            "Please correct the data or use a later API version."
        )
        default_code = "precondition_failed"

    def retrieve(self, request, pk=None):
        try:
            return super().retrieve(request, pk)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def list(self, request):
        try:
            return super().list(request)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    @extend_schema(methods=["get"], responses={200: serializers.AvailablePrefixSerializer(many=True)})
    @extend_schema(
        methods=["post"],
        request=serializers.PrefixLengthSerializer,
        responses={201: serializers.PrefixSerializer(many=True)},
    )
    @action(
        detail=True,
        name="Available Prefixes",
        url_path="available-prefixes",
        methods=["get", "post"],
        filterset_class=None,
    )
    def available_prefixes(self, request, pk=None):
        """
        A convenience method for listing and/or allocating available child prefixes within a parent.

        This uses a Redis lock to prevent this API from being invoked in parallel, in order to avoid a race condition
        if multiple clients tried to simultaneously request allocation from the same parent prefix.
        """
        prefix = get_object_or_404(self.queryset, pk=pk)
        if request.method == "POST":
            with cache.lock(
                "nautobot.ipam.api.views.available_prefixes", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT
            ):
                available_prefixes = prefix.get_available_prefixes()

                # Validate Requested Prefixes' length
                serializer = serializers.PrefixLengthSerializer(
                    data=request.data if isinstance(request.data, list) else [request.data],
                    many=True,
                    context={
                        "request": request,
                        "prefix": prefix,
                    },
                )
                serializer.is_valid(raise_exception=True)

                requested_prefixes = serializer.validated_data
                # Allocate prefixes to the requested objects based on availability within the parent
                for requested_prefix in requested_prefixes:
                    # Find the first available prefix equal to or larger than the requested size
                    for available_prefix in available_prefixes.iter_cidrs():
                        if requested_prefix["prefix_length"] >= available_prefix.prefixlen:
                            allocated_prefix = f"{available_prefix.network}/{requested_prefix['prefix_length']}"
                            requested_prefix["prefix"] = allocated_prefix
                            requested_prefix["namespace"] = prefix.namespace
                            break
                    else:
                        return Response(
                            {"detail": "Insufficient space is available to accommodate the requested prefix size(s)"},
                            status=status.HTTP_204_NO_CONTENT,
                        )

                    # The serializer usage above has mapped "custom_fields" dict to "_custom_field_data".
                    # We need to convert it back to "custom_fields" as we're going to deserialize it a second time below
                    requested_prefix["custom_fields"] = requested_prefix.pop("_custom_field_data", {})

                    # Remove the allocated prefix from the list of available prefixes
                    available_prefixes.remove(allocated_prefix)

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request, "depth": 0}
                if isinstance(request.data, list):
                    serializer = self.get_serializer_class()(data=requested_prefixes, many=True, context=context)
                else:
                    serializer = self.get_serializer_class()(data=requested_prefixes[0], context=context)

                # Create the new Prefix(es)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        else:
            available_prefixes = prefix.get_available_prefixes()
            serializer = serializers.AvailablePrefixSerializer(
                available_prefixes.iter_cidrs(),
                many=True,
                context={
                    "request": request,
                },
            )

            return Response(serializer.data)

    @extend_schema(methods=["get"], responses={200: serializers.AvailableIPSerializer(many=True)})
    @extend_schema(
        methods=["post"],
        responses={201: serializers.IPAddressSerializer(many=True)},
        request=serializers.IPAllocationSerializer(many=True),
    )
    @action(
        detail=True,
        name="Available IPs",
        url_path="available-ips",
        methods=["get", "post"],
        queryset=IPAddress.objects.all(),
        filterset_class=None,
    )
    def available_ips(self, request, pk=None):
        """
        A convenience method for listing and/or allocating available IP addresses within a prefix.

        By default, the number of IPs returned will be equivalent to PAGINATE_COUNT.
        An arbitrary limit (up to MAX_PAGE_SIZE, if set) may be passed, however results will not be paginated.

        This uses a Redis lock to prevent this API from being invoked in parallel, in order to avoid a race condition
        if multiple clients tried to simultaneously request allocation from the same parent prefix.
        """
        prefix = get_object_or_404(Prefix.objects.restrict(request.user), pk=pk)

        # Create the next available IP within the prefix
        if request.method == "POST":
            with cache.lock(
                "nautobot.ipam.api.views.available_ips", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT
            ):
                # Normalize to a list of objects
                serializer = serializers.IPAllocationSerializer(
                    data=request.data if isinstance(request.data, list) else [request.data],
                    many=True,
                    context={
                        "request": request,
                        "prefix": prefix,
                    },
                )
                serializer.is_valid(raise_exception=True)

                requested_ips = serializer.validated_data

                # Determine if the requested number of IPs is available
                available_ips = prefix.get_available_ips()
                if available_ips.size < len(requested_ips):
                    return Response(
                        {
                            "detail": (
                                f"An insufficient number of IP addresses are available within the prefix {prefix} "
                                f"({len(requested_ips)} requested, {len(available_ips)} available)"
                            )
                        },
                        status=status.HTTP_204_NO_CONTENT,
                    )

                # Assign addresses from the list of available IPs and copy Namespace assignment from the parent Prefix
                available_ips = iter(available_ips)
                prefix_length = prefix.prefix.prefixlen
                for requested_ip in requested_ips:
                    requested_ip["address"] = f"{next(available_ips)}/{prefix_length}"
                    requested_ip["namespace"] = prefix.namespace
                    # The serializer usage above has mapped "custom_fields" dict to "_custom_field_data".
                    # We need to convert it back to "custom_fields" as we're going to deserialize it a second time below
                    requested_ip["custom_fields"] = requested_ip.pop("_custom_field_data", {})

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request, "depth": 0}
                if isinstance(request.data, list):
                    serializer = serializers.IPAddressSerializer(data=requested_ips, many=True, context=context)
                else:
                    serializer = serializers.IPAddressSerializer(data=requested_ips[0], context=context)

                # Create the new IP address(es)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Determine the maximum number of IPs to return
        else:
            try:
                limit = int(request.query_params.get("limit", get_settings_or_config("PAGINATE_COUNT")))
            except ValueError:
                limit = get_settings_or_config("PAGINATE_COUNT")
            if get_settings_or_config("MAX_PAGE_SIZE"):
                limit = min(limit, get_settings_or_config("MAX_PAGE_SIZE"))

            # Calculate available IPs within the prefix
            ip_list = []
            for index, ip in enumerate(prefix.get_available_ips(), start=1):
                ip_list.append(ip)
                if index == limit:
                    break
            serializer = serializers.AvailableIPSerializer(
                ip_list,
                many=True,
                context={
                    "request": request,
                    "prefix": prefix.prefix,
                },
            )

            return Response(serializer.data)


class PrefixLocationAssignmentViewSet(NautobotModelViewSet):
    queryset = PrefixLocationAssignment.objects.select_related("prefix", "location")
    serializer_class = serializers.PrefixLocationAssignmentSerializer
    filterset_class = filters.PrefixLocationAssignmentFilterSet


#
# IP addresses
#


class IPAddressViewSet(NautobotModelViewSet):
    queryset = IPAddress.objects.select_related(
        "nat_inside",
        "parent",
        "role",
        "status",
        "tenant",
    ).prefetch_related("tags", "nat_outside_list")
    serializer_class = serializers.IPAddressSerializer
    filterset_class = filters.IPAddressFilterSet


#
# IP address to interface
#


class IPAddressToInterfaceViewSet(NautobotModelViewSet):
    queryset = IPAddressToInterface.objects.select_related("interface", "ip_address", "vm_interface")
    serializer_class = serializers.IPAddressToInterfaceSerializer
    filterset_class = filters.IPAddressToInterfaceFilterSet


#
# VLAN groups
#


class VLANGroupViewSet(NautobotModelViewSet):
    queryset = (
        VLANGroup.objects.select_related("location")
        .prefetch_related("tags")
        .annotate(vlan_count=count_related(VLAN, "vlan_group"))
    )
    serializer_class = serializers.VLANGroupSerializer
    filterset_class = filters.VLANGroupFilterSet

    def restrict_queryset(self, request, *args, **kwargs):
        """
        Apply "view" permissions on the POST /available-vlans/ endpoint, otherwise as ModelViewSetMixin.
        """
        if request.user.is_authenticated and self.action == "available_vlans":
            self.queryset = self.queryset.restrict(request.user, "view")
        else:
            super().restrict_queryset(request, *args, **kwargs)

    class AvailableVLANPermissions(TokenPermissions):
        """As nautobot.core.api.authentication.TokenPermissions, but enforcing add_vlan permission."""

        perms_map = {
            "GET": ["ipam.view_vlangroup"],
            "POST": ["ipam.view_vlangroup", "ipam.add_vlan"],
        }

    @extend_schema(methods=["get"], responses={200: ListSerializer(child=IntegerField())})
    @extend_schema(
        methods=["post"],
        responses={201: serializers.VLANSerializer(many=True)},
        request=serializers.VLANAllocationSerializer(many=True),
    )
    @action(
        detail=True,
        name="Available VLAN IDs",
        url_path="available-vlans",
        methods=["get", "post"],
        permission_classes=[AvailableVLANPermissions],
        filterset_class=None,
    )
    def available_vlans(self, request, pk=None):
        """
        A convenience method for listing available VLAN IDs within a VLANGroup.
        By default, the number of VIDs returned will be equivalent to PAGINATE_COUNT.
        An arbitrary limit (up to MAX_PAGE_SIZE, if set) may be passed, however results will not be paginated.
        """
        vlan_group = get_object_or_404(self.queryset, pk=pk)

        if request.method == "POST":
            with cache.lock(
                "nautobot.ipam.api.views.available_vlans", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT
            ):
                # Normalize to a list of objects
                serializer = serializers.VLANAllocationSerializer(
                    data=request.data if isinstance(request.data, list) else [request.data],
                    many=True,
                    context={
                        "request": request,
                        "vlan_group": vlan_group,
                    },
                )
                serializer.is_valid(raise_exception=True)
                requested_vlans = serializer.validated_data

                # Determine if the requested number of VLANs is available
                available_vids = vlan_group.available_vids
                if len(available_vids) < len(requested_vlans):
                    return Response(
                        {
                            "detail": (
                                f"An insufficient number of VLANs are available within the VLANGroup {vlan_group} "
                                f"({len(requested_vlans)} requested, {len(available_vids)} available)"
                            )
                        },
                        status=status.HTTP_204_NO_CONTENT,
                    )

                # Prioritise and check for explicitly requested VIDs. Remove them from available_vids
                for requested_vlan in requested_vlans:
                    # Check requested `vid` for availability.
                    # This will also catch if same `vid` was requested multiple times in a request.
                    if "vid" in requested_vlan and requested_vlan["vid"] not in available_vids:
                        return Response(
                            {"detail": f"VLAN {requested_vlan['vid']} is not available within the VLANGroup."},
                            status=status.HTTP_204_NO_CONTENT,
                        )
                    elif "vid" in requested_vlan and requested_vlan["vid"] in available_vids:
                        available_vids.remove(requested_vlan["vid"])

                # Assign VLAN IDs from the list of VLANGroup's available VLAN IDs.
                # Available_vids now does not contain explicitly requested vids.
                _available_vids = iter(available_vids)

                for requested_vlan in requested_vlans:
                    if "vid" not in requested_vlan:
                        requested_vlan["vid"] = next(_available_vids)

                    # Check requested `vlan_group`
                    if "vlan_group" in requested_vlan and requested_vlan["vlan_group"] != vlan_group:
                        return Response(
                            {
                                "detail": f"Invalid VLAN Group requested: {requested_vlan['vlan_group']}. "
                                f"Only VLAN Group {vlan_group} is permitted."
                            },
                            status=status.HTTP_204_NO_CONTENT,
                        )
                    else:
                        requested_vlan["vlan_group"] = vlan_group.pk

                    # Rewrite custom field data
                    requested_vlan["custom_fields"] = requested_vlan.pop("_custom_field_data", {})

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request, "depth": 0}

                if isinstance(request.data, list):
                    serializer = serializers.VLANSerializer(data=requested_vlans, many=True, context=context)
                else:
                    serializer = serializers.VLANSerializer(data=requested_vlans[0], context=context)

                # Create the new VLANs
                serializer.is_valid(raise_exception=True)
                serializer.save()

                data = serializer.data

                return Response(
                    data={
                        "count": len(data),
                        "next": None,
                        "previous": None,
                        "results": data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        else:
            try:
                limit = int(request.query_params.get("limit", get_settings_or_config("PAGINATE_COUNT")))
            except ValueError:
                limit = get_settings_or_config("PAGINATE_COUNT")

            if get_settings_or_config("MAX_PAGE_SIZE"):
                limit = min(limit, get_settings_or_config("MAX_PAGE_SIZE"))

            if isinstance(limit, int) and limit >= 0:
                vids = vlan_group.available_vids[0:limit]
            else:
                vids = vlan_group.available_vids

            serializer = ListSerializer(
                child=IntegerField(),
                data=vids,
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            return Response(
                {
                    "count": len(data),
                    "next": None,
                    "previous": None,
                    "results": data,
                }
            )


#
# VLANs
#


@extend_schema_view(
    bulk_update=extend_schema(responses={"200": serializers.VLANLegacySerializer(many=True)}, versions=["2.0", "2.1"]),
    bulk_partial_update=extend_schema(
        responses={"200": serializers.VLANLegacySerializer(many=True)}, versions=["2.0", "2.1"]
    ),
    create=extend_schema(responses={"201": serializers.VLANLegacySerializer}, versions=["2.0", "2.1"]),
    list=extend_schema(responses={"200": serializers.VLANLegacySerializer(many=True)}, versions=["2.0", "2.1"]),
    partial_update=extend_schema(responses={"200": serializers.VLANLegacySerializer}, versions=["2.0", "2.1"]),
    retrieve=extend_schema(responses={"200": serializers.VLANLegacySerializer}, versions=["2.0", "2.1"]),
    update=extend_schema(responses={"200": serializers.VLANLegacySerializer}, versions=["2.0", "2.1"]),
)
class VLANViewSet(NautobotModelViewSet):
    queryset = (
        VLAN.objects.select_related(
            "vlan_group",
            "status",
            "role",
            "tenant",
        )
        .prefetch_related("tags")
        .annotate(prefix_count=count_related(Prefix, "vlan"))
    )
    serializer_class = serializers.VLANSerializer
    filterset_class = filters.VLANFilterSet

    class LocationIncompatibleLegacyBehavior(APIException):
        status_code = 412
        default_detail = (
            "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
            "Please correct the data or use a later API version."
        )
        default_code = "precondition_failed"

    def get_serializer_class(self):
        if (
            not getattr(self, "swagger_fake_view", False)
            and self.request.major_version == 2
            and self.request.minor_version < 2
        ):
            # API version 2.1 or earlier - use the legacy serializer
            return serializers.VLANLegacySerializer
        return super().get_serializer_class()

    def retrieve(self, request, pk=None):
        try:
            return super().retrieve(request, pk)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def list(self, request):
        try:
            return super().list(request)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e


class VLANLocationAssignmentViewSet(NautobotModelViewSet):
    queryset = VLANLocationAssignment.objects.select_related("vlan", "location")
    serializer_class = serializers.VLANLocationAssignmentSerializer
    filterset_class = filters.VLANLocationAssignmentFilterSet


#
# Services
#


class ServiceViewSet(NautobotModelViewSet):
    queryset = Service.objects.select_related("device", "virtual_machine").prefetch_related("tags", "ip_addresses")
    serializer_class = serializers.ServiceSerializer
    filterset_class = filters.ServiceFilterSet
