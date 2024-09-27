from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.wireless.api.serializers import (
    AccessPointGroupSerializer,
    RadioProfileSerializer,
    SupportedDataRateSerializer,
    WirelessNetworkSerializer,
)
from nautobot.wireless.filters import (
    AccessPointGroupFilterSet,
    RadioProfileFilterSet,
    SupportedDataRateFilterSet,
    WirelessNetworkFilterSet,
)
from nautobot.wireless.forms import (
    AccessPointGroupBulkEditForm,
    AccessPointGroupFilterForm,
    AccessPointGroupForm,
    RadioProfileBulkEditForm,
    RadioProfileFilterForm,
    RadioProfileForm,
    SupportedDataRateBulkEditForm,
    SupportedDataRateFilterForm,
    SupportedDataRateForm,
    WirelessNetworkBulkEditForm,
    WirelessNetworkFilterForm,
    WirelessNetworkForm,
)
from nautobot.wireless.models import AccessPointGroup, RadioProfile, SupportedDataRate, WirelessNetwork
from nautobot.wireless.tables import (
    AccessPointGroupTable,
    RadioProfileTable,
    SupportedDataRateTable,
    WirelessNetworkTable,
)


class AccessPointGroupUIViewSet(NautobotUIViewSet):
    queryset = AccessPointGroup.objects.all()
    filterset_class = AccessPointGroupFilterSet
    filterset_form_class = AccessPointGroupFilterForm
    serializer_class = AccessPointGroupSerializer
    table_class = AccessPointGroupTable
    form_class = AccessPointGroupForm
    bulk_update_form_class = AccessPointGroupBulkEditForm


class RadioProfileUIViewSet(NautobotUIViewSet):
    queryset = RadioProfile.objects.all()
    filterset_class = RadioProfileFilterSet
    filterset_form_class = RadioProfileFilterForm
    serializer_class = RadioProfileSerializer
    table_class = RadioProfileTable
    form_class = RadioProfileForm
    bulk_update_form_class = RadioProfileBulkEditForm


class SupportedDataRateUIViewSet(NautobotUIViewSet):
    queryset = SupportedDataRate.objects.all()
    filterset_class = SupportedDataRateFilterSet
    filterset_form_class = SupportedDataRateFilterForm
    serializer_class = SupportedDataRateSerializer
    table_class = SupportedDataRateTable
    form_class = SupportedDataRateForm
    bulk_update_form_class = SupportedDataRateBulkEditForm


class WirelessNetworkUIViewSet(NautobotUIViewSet):
    queryset = WirelessNetwork.objects.all()
    filterset_class = WirelessNetworkFilterSet
    filterset_form_class = WirelessNetworkFilterForm
    serializer_class = WirelessNetworkSerializer
    table_class = WirelessNetworkTable
    form_class = WirelessNetworkForm
    bulk_update_form_class = WirelessNetworkBulkEditForm
