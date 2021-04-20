from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import APIRootView

from nautobot.extras.api.views import CustomFieldModelViewSet, StatusViewSetMixin
from nautobot.ipam import filters
from nautobot.ipam.models import (
    Aggregate,
    IPAddress,
    Prefix,
    RIR,
    Role,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.utilities.utils import count_related
from . import serializers


class IPAMRootView(APIRootView):
    """
    IPAM API root view
    """

    def get_view_name(self):
        return "IPAM"


#
# VRFs
#


class VRFViewSet(CustomFieldModelViewSet):
    queryset = (
        VRF.objects.prefetch_related("tenant")
        .prefetch_related("import_targets", "export_targets", "tags")
        .annotate(
            ipaddress_count=count_related(IPAddress, "vrf"),
            prefix_count=count_related(Prefix, "vrf"),
        )
    )
    serializer_class = serializers.VRFSerializer
    filterset_class = filters.VRFFilterSet


#
# Route targets
#


class RouteTargetViewSet(CustomFieldModelViewSet):
    queryset = RouteTarget.objects.prefetch_related("tenant").prefetch_related("tags")
    serializer_class = serializers.RouteTargetSerializer
    filterset_class = filters.RouteTargetFilterSet


#
# RIRs
#


class RIRViewSet(CustomFieldModelViewSet):
    queryset = RIR.objects.annotate(aggregate_count=count_related(Aggregate, "rir"))
    serializer_class = serializers.RIRSerializer
    filterset_class = filters.RIRFilterSet


#
# Aggregates
#


class AggregateViewSet(CustomFieldModelViewSet):
    queryset = Aggregate.objects.prefetch_related("rir").prefetch_related("tags")
    serializer_class = serializers.AggregateSerializer
    filterset_class = filters.AggregateFilterSet


#
# Roles
#


class RoleViewSet(CustomFieldModelViewSet):
    queryset = Role.objects.annotate(
        prefix_count=count_related(Prefix, "role"),
        vlan_count=count_related(VLAN, "role"),
    )
    serializer_class = serializers.RoleSerializer
    filterset_class = filters.RoleFilterSet


#
# Prefixes
#


class PrefixViewSet(StatusViewSetMixin, CustomFieldModelViewSet):
    queryset = Prefix.objects.prefetch_related(
        "role",
        "site",
        "status",
        "tags",
        "tenant",
        "vlan",
        "vrf__tenant",
    )
    serializer_class = serializers.PrefixSerializer
    filterset_class = filters.PrefixFilterSet

    def get_serializer_class(self):
        if self.action == "available_prefixes" and self.request.method == "POST":
            return serializers.PrefixLengthSerializer
        return super().get_serializer_class()

    @swagger_auto_schema(method="get", responses={200: serializers.AvailablePrefixSerializer(many=True)})
    @swagger_auto_schema(method="post", responses={201: serializers.PrefixSerializer(many=False)})
    @action(detail=True, url_path="available-prefixes", methods=["get", "post"])
    def available_prefixes(self, request, pk=None):
        """
        A convenience method for returning available child prefixes within a parent.

        The advisory lock decorator uses a PostgreSQL advisory lock to prevent this API from being
        invoked in parallel, which results in a race condition where multiple insertions can occur.
        """
        prefix = get_object_or_404(self.queryset, pk=pk)
        if request.method == "POST":

            with cache.lock("available-prefixes", blocking_timeout=5):
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
                for i, requested_prefix in enumerate(requested_prefixes):

                    # Find the first available prefix equal to or larger than the requested size
                    for available_prefix in available_prefixes.iter_cidrs():
                        if requested_prefix["prefix_length"] >= available_prefix.prefixlen:
                            allocated_prefix = "{}/{}".format(
                                available_prefix.network, requested_prefix["prefix_length"]
                            )
                            requested_prefix["prefix"] = allocated_prefix
                            requested_prefix["vrf"] = prefix.vrf.pk if prefix.vrf else None
                            break
                    else:
                        return Response(
                            {"detail": "Insufficient space is available to accommodate the requested prefix size(s)"},
                            status=status.HTTP_204_NO_CONTENT,
                        )

                    # Remove the allocated prefix from the list of available prefixes
                    available_prefixes.remove(allocated_prefix)

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request}
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
                    "vrf": prefix.vrf,
                },
            )

            return Response(serializer.data)

    @swagger_auto_schema(method="get", responses={200: serializers.AvailableIPSerializer(many=True)})
    @swagger_auto_schema(
        method="post",
        responses={201: serializers.AvailableIPSerializer(many=True)},
        request_body=serializers.AvailableIPSerializer(many=True),
    )
    @action(
        detail=True,
        url_path="available-ips",
        methods=["get", "post"],
        queryset=IPAddress.objects.all(),
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

            with cache.lock("available-ips", blocking_timeout=5):

                # Normalize to a list of objects
                requested_ips = request.data if isinstance(request.data, list) else [request.data]

                # Determine if the requested number of IPs is available
                available_ips = prefix.get_available_ips()
                if available_ips.size < len(requested_ips):
                    return Response(
                        {
                            "detail": "An insufficient number of IP addresses are available within the prefix {} ({} "
                            "requested, {} available)".format(prefix, len(requested_ips), len(available_ips))
                        },
                        status=status.HTTP_204_NO_CONTENT,
                    )

                # Assign addresses from the list of available IPs and copy VRF assignment from the parent prefix
                available_ips = iter(available_ips)
                prefix_length = prefix.prefix.prefixlen
                for requested_ip in requested_ips:
                    requested_ip["address"] = "{}/{}".format(next(available_ips), prefix_length)
                    requested_ip["vrf"] = prefix.vrf.pk if prefix.vrf else None

                # Initialize the serializer with a list or a single object depending on what was requested
                context = {"request": request}
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
                limit = int(request.query_params.get("limit", settings.PAGINATE_COUNT))
            except ValueError:
                limit = settings.PAGINATE_COUNT
            if settings.MAX_PAGE_SIZE:
                limit = min(limit, settings.MAX_PAGE_SIZE)

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
                    "vrf": prefix.vrf,
                },
            )

            return Response(serializer.data)


#
# IP addresses
#


class IPAddressViewSet(StatusViewSetMixin, CustomFieldModelViewSet):
    queryset = IPAddress.objects.prefetch_related(
        "assigned_object",
        "nat_inside",
        "nat_outside",
        "status",
        "tags",
        "tenant",
        "vrf__tenant",
    )
    serializer_class = serializers.IPAddressSerializer
    filterset_class = filters.IPAddressFilterSet


#
# VLAN groups
#


class VLANGroupViewSet(CustomFieldModelViewSet):
    queryset = VLANGroup.objects.prefetch_related("site").annotate(vlan_count=count_related(VLAN, "group"))
    serializer_class = serializers.VLANGroupSerializer
    filterset_class = filters.VLANGroupFilterSet


#
# VLANs
#


class VLANViewSet(StatusViewSetMixin, CustomFieldModelViewSet):
    queryset = VLAN.objects.prefetch_related(
        "group",
        "site",
        "status",
        "role",
        "tags",
        "tenant",
    ).annotate(prefix_count=count_related(Prefix, "vlan"))
    serializer_class = serializers.VLANSerializer
    filterset_class = filters.VLANFilterSet


#
# Services
#


class ServiceViewSet(CustomFieldModelViewSet):
    queryset = Service.objects.prefetch_related("device", "virtual_machine", "tags", "ipaddresses")
    serializer_class = serializers.ServiceSerializer
    filterset_class = filters.ServiceFilterSet
