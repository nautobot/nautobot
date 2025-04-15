from django.db.models import Q
from django.urls import reverse
from django_tables2 import RequestConfig
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.circuits.models import Circuit
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
from nautobot.core.tables import ButtonsColumn
from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
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
            ),
            object_detail.DistinctViewTab(
                weight=800,
                tab_id="prefixes",
                label="Prefixes",
                url_name="cloud:cloudnetwork_prefixes",
                related_object_attribute="prefixes",
            ),
            object_detail.DistinctViewTab(
                weight=900,
                tab_id="circuits",
                label="Circuits",
                url_name="cloud:cloudnetwork_circuits",
                related_object_attribute="circuit_terminations",
            ),
            object_detail.DistinctViewTab(
                weight=1000,
                tab_id="cloud_services",
                label="Cloud Services",
                url_name="cloud:cloudnetwork_cloud_services",
                related_object_attribute="cloud_services",
            ),
        ),
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context.update({"object_detail_content": self.object_detail_content})
        return context

    @action(detail=True, url_path="children")
    def children(self, request, *args, **kwargs):
        instance = self.get_object()
        children = instance.children.restrict(request.user, "view")
        children_table = CloudNetworkTable(
            data=children, extra_columns=[("actions", ButtonsColumn(model=CloudNetwork, buttons=("changelog",)))]
        )
        children_table.columns.hide("parent")
        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(children_table)
        child_url = reverse("cloud:cloudnetwork_add")
        child_table_add_url = f"{child_url}?parent={instance.id}"
        return Response(
            {"children_table": children_table, "active_tab": "children", "child_table_add_url": child_table_add_url}
        )

    @action(detail=True, url_path="prefixes")
    def prefixes(self, request, *args, **kwargs):
        instance = self.get_object()
        prefixes = instance.prefixes.restrict(request.user, "view")
        prefixes_table = PrefixTable(prefixes.select_related("namespace"), hide_hierarchy_ui=True)
        prefixes_table.columns.hide("location_count")
        prefixes_table.columns.hide("vlan")
        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(prefixes_table)
        return Response(
            {
                "prefixes_table": prefixes_table,
                "active_tab": "prefixes",
            }
        )

    @action(detail=True, url_path="circuits")
    def circuits(self, request, *args, **kwargs):
        instance = self.get_object()
        circuits = Circuit.objects.restrict(request.user, "view").filter(
            Q(circuit_termination_a__cloud_network=instance.pk) | Q(circuit_termination_z__cloud_network=instance.pk)
        )
        circuits_table = CircuitTable(circuits)
        circuits_table.columns.hide("circuit_termination_a")
        circuits_table.columns.hide("circuit_termination_z")
        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(circuits_table)
        return Response(
            {
                "circuits_table": circuits_table,
                "active_tab": "circuits",
            }
        )

    @action(detail=True, url_path="cloud-services", url_name="cloud_services")
    def cloud_services(self, request, *args, **kwargs):
        instance = self.get_object()
        cloud_services = instance.cloud_services.restrict(request.user, "view")
        cloud_services_table = CloudServiceTable(
            data=cloud_services,
            extra_columns=[("actions", ButtonsColumn(model=CloudService, return_url_extra="?tab=cloud_services"))],
        )
        cloud_services_table.columns.hide("cloud_network_count")
        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(cloud_services_table)
        return Response(
            {
                "cloud_services_table": cloud_services_table,
                "active_tab": "cloudservices",
            }
        )


class CloudResourceTypeUIViewSet(NautobotUIViewSet):
    queryset = CloudResourceType.objects.all()
    filterset_class = CloudResourceTypeFilterSet
    filterset_form_class = CloudResourceTypeFilterForm
    serializer_class = CloudResourceTypeSerializer
    table_class = CloudResourceTypeTable
    form_class = CloudResourceTypeForm
    bulk_update_form_class = CloudResourceTypeBulkEditForm

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}

            networks = instance.cloud_networks.restrict(request.user, "view")
            networks_table = CloudNetworkTable(networks)
            networks_table.columns.hide("cloud_resource_type")
            RequestConfig(request, paginate).configure(networks_table)

            services = instance.cloud_services.restrict(request.user, "view")
            services_table = CloudServiceTable(services)
            services_table.columns.hide("cloud_resource_type")
            RequestConfig(request, paginate).configure(services_table)

            context.update(
                {
                    "networks_count": networks.count(),
                    "networks_table": networks_table,
                    "services_count": services.count(),
                    "services_table": services_table,
                }
            )

        return context


class CloudServiceUIViewSet(NautobotUIViewSet):
    queryset = CloudService.objects.all()
    filterset_class = CloudServiceFilterSet
    filterset_form_class = CloudServiceFilterForm
    serializer_class = CloudServiceSerializer
    table_class = CloudServiceTable
    form_class = CloudServiceForm
    bulk_update_form_class = CloudServiceBulkEditForm

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}

            networks = instance.cloud_networks.restrict(request.user, "view")
            networks_table = CloudNetworkTable(networks)
            RequestConfig(request, paginate).configure(networks_table)

            context.update(
                {
                    "networks_count": networks.count(),
                    "networks_table": networks_table,
                }
            )

        return context
