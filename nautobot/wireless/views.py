from django.core.exceptions import ValidationError
from django_tables2 import RequestConfig

from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.wireless.api.serializers import (
    RadioProfileSerializer,
    SupportedDataRateSerializer,
    WirelessNetworkSerializer,
)
from nautobot.wireless.filters import (
    RadioProfileFilterSet,
    SupportedDataRateFilterSet,
    WirelessNetworkFilterSet,
)
from nautobot.wireless.forms import (
    RadioProfileBulkEditForm,
    RadioProfileFilterForm,
    RadioProfileForm,
    SupportedDataRateBulkEditForm,
    SupportedDataRateFilterForm,
    SupportedDataRateForm,
    WirelessNetworkBulkEditForm,
    WirelessNetworkControllerManagedDeviceGroupFormSet,
    WirelessNetworkFilterForm,
    WirelessNetworkForm,
)
from nautobot.wireless.models import RadioProfile, SupportedDataRate, WirelessNetwork
from nautobot.wireless.tables import (
    ControllerManagedDeviceGroupWirelessNetworkAssignmentTable,
    RadioProfileTable,
    SupportedDataRateTable,
    WirelessNetworkTable,
)


class RadioProfileUIViewSet(NautobotUIViewSet):
    queryset = RadioProfile.objects.all()
    filterset_class = RadioProfileFilterSet
    filterset_form_class = RadioProfileFilterForm
    serializer_class = RadioProfileSerializer
    table_class = RadioProfileTable
    form_class = RadioProfileForm
    bulk_update_form_class = RadioProfileBulkEditForm

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # Supported Data Rates
            supported_data_rates = instance.supported_data_rates.restrict(request.user, "view")
            supported_data_rates_table = SupportedDataRateTable(supported_data_rates)
            RequestConfig(
                request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            ).configure(supported_data_rates_table)
            context["supported_data_rates_table"] = supported_data_rates_table

        return context


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

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # Controller Managed Device Groups
            controller_managed_device_groups = instance.controller_managed_device_group_assignments.restrict(
                request.user, "view"
            )
            controller_managed_device_groups_table = ControllerManagedDeviceGroupWirelessNetworkAssignmentTable(
                controller_managed_device_groups
            )
            controller_managed_device_groups_table.columns.hide("wireless_network")
            controller_managed_device_groups_table.columns.hide("ssid")
            controller_managed_device_groups_table.columns.hide("mode")
            controller_managed_device_groups_table.columns.hide("enabled")
            controller_managed_device_groups_table.columns.hide("authentication")
            controller_managed_device_groups_table.columns.hide("hidden")
            controller_managed_device_groups_table.columns.hide("secrets_group")
            RequestConfig(
                request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            ).configure(controller_managed_device_groups_table)
            context["controller_managed_device_groups_table"] = controller_managed_device_groups_table

        if self.action in ["create", "update"]:
            context["controller_managed_device_groups"] = WirelessNetworkControllerManagedDeviceGroupFormSet(
                instance=instance,
                data=request.POST if request.method == "POST" else None,
            )

        return context

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)

        ctx = self.get_extra_context(self.request, obj)
        controller_managed_device_groups = ctx.get("controller_managed_device_groups")
        if controller_managed_device_groups.is_valid():
            controller_managed_device_groups.save()
        else:
            raise ValidationError(controller_managed_device_groups.errors)

        return obj
