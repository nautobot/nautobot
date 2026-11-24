from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.circuits.tables import CircuitTable
from nautobot.cloud.api.serializers import (
    CloudAccountGroupSerializer,
    CloudAccountSerializer,
    CloudNetworkSerializer,
    CloudResourceGroupSerializer,
    CloudResourceTypeSerializer,
    CloudServiceSerializer,
)
from nautobot.cloud.filters import (
    CloudAccountFilterSet,
    CloudAccountGroupFilterSet,
    CloudNetworkFilterSet,
    CloudResourceGroupFilterSet,
    CloudResourceTypeFilterSet,
    CloudServiceFilterSet,
)
from nautobot.cloud.forms import (
    CloudAccountBulkEditForm,
    CloudAccountFilterForm,
    CloudAccountForm,
    CloudAccountGroupBulkEditForm,
    CloudAccountGroupFilterForm,
    CloudAccountGroupForm,
    CloudNetworkBulkEditForm,
    CloudNetworkFilterForm,
    CloudNetworkForm,
    CloudResourceGroupBulkEditForm,
    CloudResourceGroupFilterForm,
    CloudResourceGroupForm,
    CloudResourceTypeBulkEditForm,
    CloudResourceTypeFilterForm,
    CloudResourceTypeForm,
    CloudServiceBulkEditForm,
    CloudServiceFilterForm,
    CloudServiceForm,
)
from nautobot.cloud.models import (
    CloudAccount,
    CloudAccountGroup,
    CloudNetwork,
    CloudResourceGroup,
    CloudResourceType,
    CloudService,
)
from nautobot.cloud.tables import (
    CloudAccountGroupTable,
    CloudAccountTable,
    CloudNetworkTable,
    CloudResourceGroupTable,
    CloudResourceTypeTable,
    CloudServiceTable,
)
from nautobot.core.ui import object_detail
from nautobot.core.ui.breadcrumbs import (
    Breadcrumbs,
    context_object_attr,
    InstanceBreadcrumbItem,
    InstanceParentBreadcrumbItem,
    ModelBreadcrumbItem,
)
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.ipam.tables import IPAddressTable, PrefixTable
from nautobot.load_balancers.tables import VirtualServerTable
from nautobot.vpn.tables import VPNTunnelEndpointTable


class RelatedObjectsTablePanel(object_detail.ObjectsTablePanel):
    """An objects table panel that is only rendered when the object has related objects of this kind."""

    def __init__(self, *, related_attribute, **kwargs):
        self.related_attribute = related_attribute
        super().__init__(**kwargs)

    def should_render(self, context):
        return super().should_render(context) and getattr(context["object"], self.related_attribute).exists()


class CloudAccountUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = CloudAccountBulkEditForm
    queryset = CloudAccount.objects.all()
    filterset_class = CloudAccountFilterSet
    filterset_form_class = CloudAccountFilterForm
    serializer_class = CloudAccountSerializer
    table_class = CloudAccountTable
    form_class = CloudAccountForm
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(),
                InstanceParentBreadcrumbItem(
                    parent_key="provider",
                ),
            ]
        }
    )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=CloudResourceGroupTable,
                table_filter="cloud_account",
                exclude_columns=["cloud_account"],
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                table_class=CloudNetworkTable,
                table_filter="cloud_account",
                exclude_columns=["cloud_account"],
            ),
            object_detail.ObjectsTablePanel(
                weight=300,
                section=SectionChoices.FULL_WIDTH,
                table_class=CloudServiceTable,
                table_filter="cloud_account",
                exclude_columns=["cloud_account"],
            ),
        )
    )


class CloudAccountGroupUIViewSet(NautobotUIViewSet):
    queryset = CloudAccountGroup.objects.all()
    filterset_class = CloudAccountGroupFilterSet
    filterset_form_class = CloudAccountGroupFilterForm
    serializer_class = CloudAccountGroupSerializer
    table_class = CloudAccountGroupTable
    form_class = CloudAccountGroupForm
    bulk_update_form_class = CloudAccountGroupBulkEditForm

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("name", "parent", "cloud_resource_type", "description"),
            ),
            object_detail.ObjectTextPanel(
                section=SectionChoices.LEFT_HALF,
                weight=200,
                object_field="extra_config",
                label="Extra Config",
                render_as=object_detail.ObjectTextPanel.RenderOptions.JSON,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                table_class=CloudAccountGroupTable,
                table_filter="parent",
                table_title="Child Groups",
                exclude_columns=["cloud_account_count"],
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                table_class=CloudAccountTable,
                table_filter="cloud_account_group",
                exclude_columns=["cloud_account_group"],
            ),
        )
    )


class CloudResourceGroupUIViewSet(NautobotUIViewSet):
    queryset = CloudResourceGroup.objects.all()
    filterset_class = CloudResourceGroupFilterSet
    filterset_form_class = CloudResourceGroupFilterForm
    serializer_class = CloudResourceGroupSerializer
    table_class = CloudResourceGroupTable
    form_class = CloudResourceGroupForm
    bulk_update_form_class = CloudResourceGroupBulkEditForm
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(),
                InstanceBreadcrumbItem(instance=context_object_attr("cloud_account")),
            ]
        }
    )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=(
                    "name",
                    "provider_resource_id",
                    "cloud_account",
                    "cloud_resource_type",
                    "location",
                    "description",
                ),
            ),
            object_detail.ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="extra_config",
                label="Extra Config",
                render_as=object_detail.ObjectTextPanel.RenderOptions.JSON,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=200,
                table_class=CloudNetworkTable,
                table_filter="cloud_resource_group",
                exclude_columns=["cloud_account", "cloud_resource_group"],
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=300,
                table_class=CloudServiceTable,
                table_filter="cloud_resource_group",
                exclude_columns=["cloud_account", "cloud_resource_group"],
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
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(model_key="object"),
                InstanceBreadcrumbItem(
                    instance=context_object_attr("parent"), should_render=context_object_attr("parent")
                ),
            ]
        }
    )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=(
                    "name",
                    "provider_resource_id",
                    "status",
                    "role",
                    "cloud_resource_type",
                    "cloud_account",
                    "cloud_resource_group",
                    "parent",
                    "location",
                    "tenant",
                    "description",
                ),
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
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(),
                InstanceParentBreadcrumbItem(parent_key="provider"),
            ]
        }
    )

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
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(),
                InstanceBreadcrumbItem(instance=context_object_attr("cloud_resource_type")),
            ]
        }
    )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=(
                    "name",
                    "provider_resource_id",
                    "status",
                    "role",
                    "cloud_account",
                    "cloud_resource_group",
                    "cloud_resource_type",
                    "location",
                    "tenant",
                    "description",
                ),
            ),
            object_detail.ObjectTextPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="extra_config",
                label="Extra Config",
                render_as=object_detail.ObjectTextPanel.RenderOptions.JSON,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                table_class=IPAddressTable,
                table_filter="cloud_services",
                table_title="IP Addresses",
                include_columns=["address", "status", "role", "dns_name"],
                add_button_route=None,
            ),
            RelatedObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=300,
                related_attribute="virtual_servers",
                table_class=VirtualServerTable,
                table_filter="cloud_service",
                table_title="Virtual Servers",
                include_columns=["name", "vip", "dns_name", "port", "protocol", "load_balancer_pool"],
                add_button_route=None,
            ),
            RelatedObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=400,
                related_attribute="vpn_tunnel_endpoints",
                table_class=VPNTunnelEndpointTable,
                table_filter="cloud_service",
                table_title="VPN Tunnel Endpoints",
                include_columns=["name", "source_ipaddress", "vpn_profile"],
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=300,
                table_class=CloudNetworkTable,
                table_filter="cloud_services",
                table_title="Cloud Networks",
                exclude_columns=["cloud_service_count"],
                add_button_route=None,
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
