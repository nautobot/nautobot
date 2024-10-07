from django.core.exceptions import ValidationError
from django_tables2 import RequestConfig
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.core.views.paginator import get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.tables import DeviceTable
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
    AccessPointGroupWirelessNetworkFormSet,
    RadioProfileBulkEditForm,
    RadioProfileFilterForm,
    RadioProfileForm,
    SupportedDataRateBulkEditForm,
    SupportedDataRateFilterForm,
    SupportedDataRateForm,
    WirelessNetworkAccessPointGroupFormSet,
    WirelessNetworkBulkEditForm,
    WirelessNetworkFilterForm,
    WirelessNetworkForm,
)
from nautobot.wireless.models import AccessPointGroup, RadioProfile, SupportedDataRate, WirelessNetwork
from nautobot.wireless.tables import (
    AccessPointGroupTable,
    AccessPointGroupWirelessNetworkAssignmentTable,
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

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # Devices
            devices = instance.devices.restrict(request.user, "view")
            context["device_count"] = devices.count()

            # Wireless Networks
            wireless_networks = instance.wireless_network_assignments.restrict(request.user, "view")
            wireless_networks_table = AccessPointGroupWirelessNetworkAssignmentTable(wireless_networks)
            wireless_networks_table.columns.hide("access_point_group")
            wireless_networks_table.columns.hide("controller")
            RequestConfig(request, paginate={"per_page": get_paginate_count(request)}).configure(
                wireless_networks_table
            )
            context["wireless_networks_table"] = wireless_networks_table

            # Radio Profiles
            radio_profiles = instance.radio_profiles.restrict(request.user, "view")
            radio_profiles_table = RadioProfileTable(radio_profiles)
            RequestConfig(request, paginate={"per_page": get_paginate_count(request)}).configure(radio_profiles_table)
            context["radio_profiles_table"] = radio_profiles_table

        if self.action in ["create", "update"]:
            context["wireless_networks"] = AccessPointGroupWirelessNetworkFormSet(
                instance=instance,
                data=request.POST if request.method == "POST" else None,
            )

        return context

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)

        ctx = self.get_extra_context(self.request, obj)
        wireless_networks = ctx.get("wireless_networks")
        if wireless_networks.is_valid():
            wireless_networks.save()
        else:
            raise ValidationError(wireless_networks.errors)

        return obj

    def extra_post_save_action(self, obj, form):
        if form.cleaned_data.get("add_radio_profiles", None):
            obj.radio_profiles.add(*form.cleaned_data["add_radio_profiles"])
        if form.cleaned_data.get("remove_radio_profiles", None):
            obj.radio_profiles.remove(*form.cleaned_data["remove_radio_profiles"])
        if form.cleaned_data.get("add_devices", None):
            obj.devices.add(*form.cleaned_data["add_devices"])
        if form.cleaned_data.get("remove_devices", None):
            obj.devices.remove(*form.cleaned_data["remove_devices"])

    @action(detail=True, url_path="devices")
    def devices(self, request, *args, **kwargs):
        instance = self.get_object()
        devices = instance.devices.restrict(request.user, "view")
        device_table = DeviceTable(devices)
        RequestConfig(request, paginate={"per_page": get_paginate_count(request)}).configure(device_table)

        return Response(
            {
                "device_table": device_table,
                "active_tab": "devices",
                "device_count": devices.count(),
            }
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
            RequestConfig(request, paginate={"per_page": get_paginate_count(request)}).configure(
                supported_data_rates_table
            )
            context["supported_data_rates_table"] = supported_data_rates_table

        return context

    def extra_post_save_action(self, obj, form):
        if form.cleaned_data.get("add_supported_data_rates", None):
            obj.supported_data_rates.add(*form.cleaned_data["add_supported_data_rates"])
        if form.cleaned_data.get("remove_supported_data_rates", None):
            obj.supported_data_rates.remove(*form.cleaned_data["remove_supported_data_rates"])
        if form.cleaned_data.get("add_access_point_groups", None):
            obj.access_point_groups.add(*form.cleaned_data["add_access_point_groups"])
        if form.cleaned_data.get("remove_access_point_groups", None):
            obj.access_point_groups.remove(*form.cleaned_data["remove_access_point_groups"])


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
            # Access Point Groups
            access_point_groups = instance.access_point_group_assignments.restrict(request.user, "view")
            access_point_groups_table = AccessPointGroupWirelessNetworkAssignmentTable(access_point_groups)
            access_point_groups_table.columns.hide("wireless_network")
            access_point_groups_table.columns.hide("ssid")
            access_point_groups_table.columns.hide("mode")
            access_point_groups_table.columns.hide("enabled")
            access_point_groups_table.columns.hide("authentication")
            access_point_groups_table.columns.hide("hidden")
            access_point_groups_table.columns.hide("secrets_group")
            RequestConfig(request, paginate={"per_page": get_paginate_count(request)}).configure(
                access_point_groups_table
            )
            context["access_point_groups_table"] = access_point_groups_table

        if self.action in ["create", "update"]:
            context["access_point_groups"] = WirelessNetworkAccessPointGroupFormSet(
                instance=instance,
                data=request.POST if request.method == "POST" else None,
            )

        return context

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)

        ctx = self.get_extra_context(self.request, obj)
        access_point_groups = ctx.get("access_point_groups")
        if access_point_groups.is_valid():
            access_point_groups.save()
        else:
            raise ValidationError(access_point_groups.errors)

        return obj
