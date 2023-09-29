from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import APIRootView

from nautobot.core.models.querysets import count_related
from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.api.views import NautobotModelViewSet
from nautobot.ipam import filters
from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from . import serializers


class IPAMRootView(APIRootView):
    """
    IPAM API root view
    """

    def get_view_name(self):
        return "IPAM"


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
    queryset = (
        VRF.objects.select_related("tenant").prefetch_related("import_targets", "export_targets", "tags")
        # FIXME(jathan): See if we need to revise the counts for prefixes/ips, here?
        # .annotate(
        #     ipaddress_count=count_related(IPAddress, "vrf"),
        #     prefix_count=count_related(Prefix, "vrf"),
        # )
    )
    serializer_class = serializers.VRFSerializer
    filterset_class = filters.VRFFilterSet


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


class PrefixViewSet(NautobotModelViewSet):
    queryset = Prefix.objects.select_related(
        "role",
        "status",
        "location",
        "tenant",
        "vlan",
        "namespace",
    ).prefetch_related("tags")
    serializer_class = serializers.PrefixSerializer
    filterset_class = filters.PrefixFilterSet

    def get_serializer_class(self):
        if self.action == "available_prefixes" and self.request.method == "POST":
            return serializers.PrefixLengthSerializer
        return super().get_serializer_class()

    @extend_schema(methods=["get"], responses={200: serializers.AvailablePrefixSerializer(many=True)})
    @extend_schema(methods=["post"], responses={201: serializers.PrefixSerializer(many=False)})
    @action(detail=True, url_path="available-prefixes", methods=["get", "post"], filterset_class=None)
    def available_prefixes(self, request, pk=None):
        """
        A convenience method for returning available child prefixes within a parent.

        The advisory lock decorator uses a PostgreSQL advisory lock to prevent this API from being
        invoked in parallel, which results in a race condition where multiple insertions can occur.
        """
        prefix = get_object_or_404(self.queryset, pk=pk)
        if request.method == "POST":
            with cache.lock("available-prefixes", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT):
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
                            requested_prefix["namespace"] = prefix.namespace.pk
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
                    serializer = serializers.PrefixSerializer(data=requested_prefixes, many=True, context=context)
                else:
                    serializer = serializers.PrefixSerializer(data=requested_prefixes[0], context=context)

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
        responses={201: serializers.AvailableIPSerializer(many=True)},
        request=serializers.AvailableIPSerializer(many=True),
    )
    @action(
        detail=True,
        url_path="available-ips",
        methods=["get", "post"],
        queryset=IPAddress.objects.all(),
        filterset_class=None,
    )
    def available_ips(self, request, pk=None):
        """
        A convenience method for returning available IP addresses within a prefix. By default, the number of IPs
        returned will be equivalent to PAGINATE_COUNT. An arbitrary limit (up to MAX_PAGE_SIZE, if set) may be passed,
        however results will not be paginated.

        The advisory lock decorator uses a PostgreSQL advisory lock to prevent this API from being
        invoked in parallel, which results in a race condition where multiple insertions can occur.
        """
        prefix = get_object_or_404(Prefix.objects.restrict(request.user), pk=pk)

        # Create the next available IP within the prefix
        if request.method == "POST":
            with cache.lock("available-ips", blocking_timeout=5, timeout=settings.REDIS_LOCK_TIMEOUT):
                # Normalize to a list of objects
                requested_ips = request.data if isinstance(request.data, list) else [request.data]

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
                    requested_ip["namespace"] = prefix.namespace.pk

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


#
# IP addresses
#


class IPAddressViewSet(NautobotModelViewSet):
    queryset = IPAddress.objects.select_related(
        "parent",
        "nat_inside",
        "status",
        "role",
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
    queryset = VLANGroup.objects.select_related("location").annotate(vlan_count=count_related(VLAN, "vlan_group"))
    serializer_class = serializers.VLANGroupSerializer
    filterset_class = filters.VLANGroupFilterSet


#
# VLANs
#


class VLANViewSet(NautobotModelViewSet):
    queryset = (
        VLAN.objects.select_related(
            "vlan_group",
            "location",
            "status",
            "role",
            "tenant",
        )
        .prefetch_related("tags")
        .annotate(prefix_count=count_related(Prefix, "vlan"))
    )
    serializer_class = serializers.VLANSerializer
    filterset_class = filters.VLANFilterSet


#
# Services
#


class ServiceViewSet(NautobotModelViewSet):
    queryset = Service.objects.select_related("device", "virtual_machine").prefetch_related("tags", "ip_addresses")
    serializer_class = serializers.ServiceSerializer
    filterset_class = filters.ServiceFilterSet
