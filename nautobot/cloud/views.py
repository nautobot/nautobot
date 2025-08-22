from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.circuits.tables import CircuitTable
from nautobot.cloud.api.serializers import (
    CloudAccountSerializer,
    CloudNetworkSerializer,
    CloudResourceTypeSerializer,
    CloudServiceSerializer,
)
from nautobot.cloud.filters import (
    CloudAccountFilterSet,
    CloudNetworkFilterSet,
    CloudResourceTypeFilterSet,
    CloudServiceFilterSet,
)
from nautobot.cloud.forms import (
    CloudAccountBulkEditForm,
    CloudAccountFilterForm,
    CloudAccountForm,
    CloudNetworkBulkEditForm,
    CloudNetworkFilterForm,
    CloudNetworkForm,
    CloudResourceTypeBulkEditForm,
    CloudResourceTypeFilterForm,
    CloudResourceTypeForm,
    CloudServiceBulkEditForm,
    CloudServiceFilterForm,
    CloudServiceForm,
)
from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudResourceType, CloudService
from nautobot.cloud.tables import CloudAccountTable, CloudNetworkTable, CloudResourceTypeTable, CloudServiceTable
from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.ipam.tables import PrefixTable


class CloudAccountUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = CloudAccountBulkEditForm
    queryset = CloudAccount.objects.all()
    filterset_class = CloudAccountFilterSet
    filterset_form_class = CloudAccountFilterForm
    serializer_class = CloudAccountSerializer
    table_class = CloudAccountTable
    form_class = CloudAccountForm

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        )
    )


class CloudNetworkUIViewSet(NautobotUIViewSet):
    queryset = CloudNetwork.objects.all()
    filterset_class = CloudNetworkFilterSet
    filterset_form_class = CloudNetworkFilterForm
    serializer_class = CloudNetworkSerializer
    table_class = CloudNetworkTable
    form_class = CloudNetworkForm
    bulk_update_form_class = CloudNetworkBulkEditForm
    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("name", "cloud_resource_type", "cloud_account", "parent", "description"),
            ),
            object_detail.ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="extra_config",
                label="Extra Config",
                render_as=object_detail.ObjectTextPanel.RenderOptions.JSON,
            ),
        ),
        extra_tabs=(
            object_detail.DistinctViewTab(
                weight=700,
                tab_id="children",
                label="Children",
                url_name="cloud:cloudnetwork_children",
                related_object_attribute="children",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        label="Children",
                        table_class=CloudNetworkTable,
                        table_filter="parent",
                        tab_id="children",
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=800,
                tab_id="prefixes",
                label="Prefixes",
                url_name="cloud:cloudnetwork_prefixes",
                related_object_attribute="prefixes",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=PrefixTable,
                        table_filter="cloud_networks",
                        exclude_columns=("location_count", "vlan"),
                        tab_id="prefixes",
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=900,
                tab_id="circuits",
                label="Circuits",
                url_name="cloud:cloudnetwork_circuits",
                related_object_attribute="circuit_terminations",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=CircuitTable,
                        table_filter=["circuit_termination_a__cloud_network", "circuit_termination_z__cloud_network"],
                        related_field_name="cloud_network",
                        exclude_columns=("circuit_termination_a", "circuit_termination_z"),
                        tab_id="circuits",
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=1000,
                tab_id="cloud_services",
                label="Cloud Services",
                url_name="cloud:cloudnetwork_cloud_services",
                related_object_attribute="cloud_services",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=CloudServiceTable,
                        table_filter="cloud_networks",
                        exclude_columns=("cloud_network_count"),
                        tab_id="cloud_services",
                        include_paginator=True,
                    ),
                ),
            ),
        ),
    )

    @action(detail=True, url_path="children", custom_view_base_action="view")
    def children(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="prefixes",
        custom_view_base_action="view",
        custom_view_additional_permissions=["ipam.view_prefix"],
    )
    def prefixes(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="circuits",
        custom_view_base_action="view",
        custom_view_additional_permissions=["circuits.view_circuit"],
    )
    def circuits(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="cloud-services",
        url_name="cloud_services",
        custom_view_base_action="view",
        custom_view_additional_permissions=["cloud.view_cloudservice"],
    )
    def cloud_services(self, request, *args, **kwargs):
        return Response({})


class CloudResourceTypeUIViewSet(NautobotUIViewSet):
    queryset = CloudResourceType.objects.all()
    filterset_class = CloudResourceTypeFilterSet
    filterset_form_class = CloudResourceTypeFilterForm
    serializer_class = CloudResourceTypeSerializer
    table_class = CloudResourceTypeTable
    form_class = CloudResourceTypeForm
    bulk_update_form_class = CloudResourceTypeBulkEditForm
    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("name", "provider", "content_types", "description"),
            ),
            object_detail.ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="config_schema",
                label="Config Schema",
                render_as=object_detail.ObjectTextPanel.RenderOptions.JSON,
            ),
        ),
        extra_tabs=(
            object_detail.DistinctViewTab(
                weight=900,
                tab_id="networks",
                label="Cloud Networks",
                url_name="cloud:cloudresourcetype_networks",
                related_object_attribute="cloud_networks",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=CloudNetworkTable,
                        table_filter="cloud_resource_type",
                        tab_id="networks",
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=1000,
                tab_id="services",
                label="Cloud Services",
                url_name="cloud:cloudresourcetype_services",
                related_object_attribute="cloud_services",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=CloudServiceTable,
                        table_filter="cloud_resource_type",
                        tab_id="services",
                        include_paginator=True,
                    ),
                ),
            ),
        ),
    )

    @action(
        detail=True,
        url_path="networks",
        custom_view_base_action="view",
        custom_view_additional_permissions=["cloud.view_cloudnetwork"],
    )
    def networks(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="services",
        custom_view_base_action="view",
        custom_view_additional_permissions=["cloud.view_cloudservice"],
    )
    def services(self, request, *args, **kwargs):
        return Response({})


class CloudServiceUIViewSet(NautobotUIViewSet):
    queryset = CloudService.objects.all()
    filterset_class = CloudServiceFilterSet
    filterset_form_class = CloudServiceFilterForm
    serializer_class = CloudServiceSerializer
    table_class = CloudServiceTable
    form_class = CloudServiceForm
    bulk_update_form_class = CloudServiceBulkEditForm

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("name", "cloud_account", "cloud_resource_type", "description"),
            ),
            object_detail.ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="extra_config",
                label="Extra Config",
                render_as=object_detail.ObjectTextPanel.RenderOptions.JSON,
            ),
        ),
        extra_tabs=(
            object_detail.DistinctViewTab(
                weight=800,
                tab_id="cloud_networks",
                label="Cloud Networks",
                url_name="cloud:cloudservice_cloud_networks",
                related_object_attribute="cloud_networks",
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=CloudNetworkTable,
                        table_filter="cloud_services",
                        tab_id="cloud_networks",
                        add_button_route=None,
                        include_paginator=True,
                    ),
                ),
            ),
        ),
    )

    @action(
        detail=True,
        url_path="cloud-networks",
        url_name="cloud_networks",
        custom_view_base_action="view",
        custom_view_additional_permissions=["cloud.view_cloudnetwork"],
    )
    def cloud_networks(self, request, *args, **kwargs):
        return Response({})
