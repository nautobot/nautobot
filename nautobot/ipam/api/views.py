from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
import netaddr
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.serializers import IntegerField, ListSerializer

from nautobot.core.api.authentication import TokenPermissions
from nautobot.core.constants import MAX_PAGE_SIZE_DEFAULT, PAGINATE_COUNT_DEFAULT
from nautobot.core.models.querysets import count_related
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.models import Location
from nautobot.extras.api.views import ModelViewSet, NautobotModelViewSet
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
    queryset = VRF.objects.all()
    serializer_class = serializers.VRFSerializer
    filterset_class = filters.VRFFilterSet


class VRFDeviceAssignmentViewSet(ModelViewSet):
    queryset = VRFDeviceAssignment.objects.all()
    serializer_class = serializers.VRFDeviceAssignmentSerializer
    filterset_class = filters.VRFDeviceAssignmentFilterSet


class VRFPrefixAssignmentViewSet(ModelViewSet):
    queryset = VRFPrefixAssignment.objects.all()
    serializer_class = serializers.VRFPrefixAssignmentSerializer
    filterset_class = filters.VRFPrefixAssignmentFilterSet


#
# Route targets
#


class RouteTargetViewSet(NautobotModelViewSet):
    queryset = RouteTarget.objects.all()
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
    queryset = Prefix.objects.all()
    serializer_class = serializers.PrefixSerializer
    filterset_class = filters.PrefixFilterSet

    def get_serializer_class(self):
        if (
            not getattr(self, "swagger_fake_view", False)
            and hasattr(self.request, "major_version")
            and self.request.major_version == 2
            and self.request.minor_version < 2
        ):
            # API version 2.0 or 2.1 - use the legacy serializer
            return serializers.PrefixLegacySerializer
        return super().get_serializer_class()

    @staticmethod
    def get_ipaddress_param(request, name, default):
        """Extract IP address parameter from request.
        :param request: django-rest request object
        :param name: name of the query parameter which contains the IP address string
        :param default: fallback IP address string in case no value is present in the query parameter
        :return: tuple of mutually exclusive (Response|None, netaddr.IPAddress object|None).
                 Will return a Response in case the client sent incorrectly formatted IP Address in
                 the parameter. It is up to the caller to return the Response.
        """
        response, result = None, None
        try:
            result = netaddr.IPAddress(request.query_params.get(name, default))
        except (netaddr.core.AddrFormatError, ValueError, TypeError) as e:
            response = Response(
                {"detail": (f"Incorrectly formatted address in parameter {name}: {e}")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return response, result

    class LocationIncompatibleLegacyBehavior(APIException):
        status_code = 412
        default_detail = (
            "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
            "Please correct the data or use a later API version."
        )
        default_code = "precondition_failed"

    def retrieve(self, request, *args, pk=None, **kwargs):
        try:
            return super().retrieve(request, *args, pk=pk, **kwargs)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
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
                requested_prefixes = request.data if isinstance(request.data, list) else [request.data]
                for requested_prefix in requested_prefixes:
                    # If the prefix_length is not an integer, return a 400 using the
                    # serializer.is_valid(raise_exception=True) method call below
                    if not isinstance(requested_prefix["prefix_length"], int):
                        return Response(
                            {"prefix_length": "This field must be an integer."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
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
                self.perform_create(serializer)

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

    @extend_schema(
        methods=["get", "post"],
        parameters=[
            OpenApiParameter(
                name="range_start",
                location="query",
                description="IP from which enumeration/allocation should start.",
                type={
                    "oneOf": [
                        {"type": "string", "format": "ipv6"},
                        {"type": "string", "format": "ipv4"},
                    ]
                },
            ),
            OpenApiParameter(
                name="range_end",
                location="query",
                description="IP from which enumeration/allocation should stop.",
                type={
                    "oneOf": [
                        {"type": "string", "format": "ipv6"},
                        {"type": "string", "format": "ipv4"},
                    ]
                },
            ),
        ],
    )
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

        default_first, default_last = netaddr.IPAddress(prefix.prefix.first), netaddr.IPAddress(prefix.prefix.last)
        ((error_response_start, range_start), (error_response_end, range_end)) = (
            self.get_ipaddress_param(request, "range_start", default_first),
            self.get_ipaddress_param(request, "range_end", default_last),
        )
        if response := error_response_start or error_response_end:
            return response

        available_ips = prefix.get_available_ips()
        # range_start and range_end are inclusive
        if range_start > default_first:
            available_ips.remove(netaddr.IPRange(default_first, range_start - 1))
        if range_end < default_last:
            available_ips.remove(netaddr.IPRange(range_end + 1, default_last))

        # Create the next available IP within the prefix
        if request.method == "POST":
            with cache.lock(
                "nautobot.ipam.api.views.available_ips", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT
            ):
                # Normalize to a list of objects
                requested_ips = request.data if isinstance(request.data, list) else [request.data]

                # Determine if the requested number of IPs is available
                if available_ips.size < len(requested_ips):
                    return Response(
                        {
                            "detail": (
                                f"An insufficient number of IP addresses are available within the prefix {prefix} "
                                f"({len(requested_ips)} requested, {available_ips.size} available between "
                                f"{range_start} and {range_end})."
                            )
                        },
                        status=status.HTTP_204_NO_CONTENT,
                    )

                # Assign addresses from the list of available IPs and copy Namespace assignment from the parent Prefix
                prefix_length = prefix.prefix.prefixlen
                available_ips_iter = iter(available_ips)
                for requested_ip in requested_ips:
                    requested_ip["address"] = f"{next(available_ips_iter)}/{prefix_length}"
                    requested_ip["namespace"] = prefix.namespace

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request, "depth": 0}
                if isinstance(request.data, list):
                    serializer = serializers.IPAddressSerializer(data=requested_ips, many=True, context=context)
                else:
                    serializer = serializers.IPAddressSerializer(data=requested_ips[0], context=context)

                # Create the new IP address(es)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Determine the maximum number of IPs to return
        else:
            try:
                limit = int(
                    request.query_params.get(
                        "limit", get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)
                    )
                )
            except ValueError:
                limit = get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)
            if get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT):
                limit = min(limit, get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT))

            # Calculate available IPs within the prefix
            ip_list = []
            for index, ip in enumerate(available_ips, start=1):
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


class PrefixLocationAssignmentViewSet(ModelViewSet):
    queryset = PrefixLocationAssignment.objects.all()
    serializer_class = serializers.PrefixLocationAssignmentSerializer
    filterset_class = filters.PrefixLocationAssignmentFilterSet


#
# IP addresses
#


class IPAddressViewSet(NautobotModelViewSet):
    queryset = IPAddress.objects.select_related("parent__namespace")
    serializer_class = serializers.IPAddressSerializer
    filterset_class = filters.IPAddressFilterSet


#
# IP address to interface
#


class IPAddressToInterfaceViewSet(NautobotModelViewSet):
    queryset = IPAddressToInterface.objects.all()
    serializer_class = serializers.IPAddressToInterfaceSerializer
    filterset_class = filters.IPAddressToInterfaceFilterSet


#
# VLAN groups
#


class VLANGroupViewSet(NautobotModelViewSet):
    queryset = VLANGroup.objects.annotate(vlan_count=count_related(VLAN, "vlan_group"))
    serializer_class = serializers.VLANGroupSerializer
    filterset_class = filters.VLANGroupFilterSet

    @staticmethod
    def vlan_group_queryset():
        return (
            VLANGroup.objects.select_related("location")
            .prefetch_related("tags")
            .annotate(vlan_count=count_related(VLAN, "vlan_group"))
        )

    class AvailableVLANPermissions(TokenPermissions):
        """As nautobot.core.api.authentication.TokenPermissions, but enforcing `add_vlan` and `view_vlan` permission."""

        perms_map = {
            "GET": ["ipam.view_vlangroup", "ipam.view_vlan"],
            "POST": ["ipam.view_vlangroup", "ipam.view_vlan", "ipam.add_vlan"],
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
        queryset=VLAN.objects.all(),
    )
    def available_vlans(self, request, pk=None):
        """
        A convenience method for listing available VLAN IDs within a VLANGroup.
        By default, the number of VIDs returned will be equivalent to PAGINATE_COUNT.
        An arbitrary limit (up to MAX_PAGE_SIZE, if set) may be passed, however results will not be paginated.
        """
        vlan_group = get_object_or_404(self.vlan_group_queryset().restrict(user=request.user), pk=pk)

        if request.method == "POST":
            with cache.lock(
                "nautobot.ipam.api.views.available_vlans", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT
            ):
                # Normalize to a list of objects
                requested_vlans = request.data if isinstance(request.data, list) else [request.data]

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
                    if "vlan_group" in requested_vlan:
                        requested_vlan_group = None
                        requested_vlan_group_pk = requested_vlan["vlan_group"]
                        try:
                            requested_vlan_group = VLANGroup.objects.get(pk=requested_vlan_group_pk)
                        except VLANGroup.DoesNotExist:
                            return Response(
                                {"detail": f"VLAN Group with pk {requested_vlan_group_pk} does not exist."},
                                status=status.HTTP_204_NO_CONTENT,
                            )

                        if requested_vlan_group != vlan_group:
                            return Response(
                                {
                                    "detail": f"Invalid VLAN Group requested: {requested_vlan_group}. "
                                    f"Only VLAN Group {vlan_group} is permitted."
                                },
                                status=status.HTTP_204_NO_CONTENT,
                            )
                    else:
                        requested_vlan["vlan_group"] = vlan_group.pk

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request, "depth": 0}

                if isinstance(request.data, list):
                    serializer = serializers.VLANSerializer(data=requested_vlans, many=True, context=context)
                else:
                    serializer = serializers.VLANSerializer(data=requested_vlans[0], context=context)

                # Create the new VLANs
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

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
                limit = int(
                    request.query_params.get(
                        "limit", get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)
                    )
                )
            except ValueError:
                limit = get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)

            if get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT):
                limit = min(limit, get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT))

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
    queryset = VLAN.objects.annotate(prefix_count=count_related(Prefix, "vlan"))
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
            and hasattr(self.request, "major_version")
            and self.request.major_version == 2
            and self.request.minor_version < 2
        ):
            # API version 2.1 or earlier - use the legacy serializer
            return serializers.VLANLegacySerializer
        return super().get_serializer_class()

    def retrieve(self, request, *args, pk=None, **kwargs):
        try:
            return super().retrieve(request, *args, pk=pk, **kwargs)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Location.MultipleObjectsReturned as e:
            raise self.LocationIncompatibleLegacyBehavior from e


class VLANLocationAssignmentViewSet(ModelViewSet):
    queryset = VLANLocationAssignment.objects.all()
    serializer_class = serializers.VLANLocationAssignmentSerializer
    filterset_class = filters.VLANLocationAssignmentFilterSet


#
# Services
#


class ServiceViewSet(NautobotModelViewSet):
    queryset = Service.objects.all()
    serializer_class = serializers.ServiceSerializer
    filterset_class = filters.ServiceFilterSet
