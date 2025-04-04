from django.db.models import Q
from django_tables2 import RequestConfig

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


class CloudNetworkUIViewSet(NautobotUIViewSet):
    queryset = CloudNetwork.objects.all()
    filterset_class = CloudNetworkFilterSet
    filterset_form_class = CloudNetworkFilterForm
    serializer_class = CloudNetworkSerializer
    table_class = CloudNetworkTable
    form_class = CloudNetworkForm
    bulk_update_form_class = CloudNetworkBulkEditForm

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            prefixes = instance.prefixes.restrict(request.user, "view")
            prefixes_table = PrefixTable(prefixes.select_related("namespace"), hide_hierarchy_ui=True)
            prefixes_table.columns.hide("location_count")
            prefixes_table.columns.hide("vlan")

            children = instance.children.restrict(request.user, "view")
            children_table = CloudNetworkTable(children)
            children_table.columns.hide("parent")

            circuits = Circuit.objects.restrict(request.user, "view").filter(
                Q(circuit_termination_a__cloud_network=instance.pk)
                | Q(circuit_termination_z__cloud_network=instance.pk)
            )
            circuits_table = CircuitTable(circuits)
            circuits_table.columns.hide("circuit_termination_a")
            circuits_table.columns.hide("circuit_termination_z")

            cloud_services = instance.cloud_services.restrict(request.user, "view")
            cloud_services_table = CloudServiceTable(cloud_services)
            cloud_services_table.columns.hide("cloud_network_count")

            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            RequestConfig(request, paginate).configure(children_table)
            RequestConfig(request, paginate).configure(circuits_table)
            RequestConfig(request, paginate).configure(prefixes_table)
            RequestConfig(request, paginate).configure(cloud_services_table)

            context.update(
                {
                    "prefix_count": prefixes.count(),
                    "prefixes_table": prefixes_table,
                    "children_count": children.count(),
                    "children_table": children_table,
                    "circuit_count": circuits.count(),
                    "circuits_table": circuits_table,
                    "cloud_service_count": cloud_services.count(),
                    "cloud_services_table": cloud_services_table,
                }
            )

        return context


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
