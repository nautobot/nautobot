"""Views for nautobot_load_balancer_models."""

from nautobot.core.ui.object_detail import (
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
    SectionChoices,
    StatsPanel,
)
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.load_balancers import filters, forms, models, tables
from nautobot.load_balancers.api import serializers


class VirtualServerUIViewSet(NautobotUIViewSet):
    """ViewSet for VirtualServer."""

    bulk_update_form_class = forms.VirtualServerBulkEditForm
    filterset_class = filters.VirtualServerFilterSet
    filterset_form_class = forms.VirtualServerFilterForm
    form_class = forms.VirtualServerForm
    lookup_field = "pk"
    queryset = models.VirtualServer.objects.all()
    serializer_class = serializers.VirtualServerSerializer
    table_class = tables.VirtualServerTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "vip",
                    "enabled",
                    "tenant",
                ],
            ),
            ObjectFieldsPanel(
                weight=200,
                label="Configuration",
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "port",
                    "protocol",
                    "load_balancer_pool",
                    "load_balancer_type",
                    "source_nat_pool",
                    "source_nat_type",
                    "health_check_monitor",
                    "ssl_offload",
                ],
            ),
            ObjectFieldsPanel(
                weight=300,
                label="Assignment",
                section=SectionChoices.RIGHT_HALF,
                fields=[
                    "device",
                    "device_redundancy_group",
                    "cloud_service",
                    "virtual_chassis",
                ],
            ),
            ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=500,
                table_class=tables.CertificateProfileTable,
                table_filter="virtual_servers",
                table_title="Certificate Profiles",
                exclude_columns=["tenant", "actions"],
                add_button_route=None,
            ),
        ]
    )


class LoadBalancerPoolUIViewSet(NautobotUIViewSet):
    """ViewSet for LoadBalancerPool."""

    bulk_update_form_class = forms.LoadBalancerPoolBulkEditForm
    filterset_class = filters.LoadBalancerPoolFilterSet
    filterset_form_class = forms.LoadBalancerPoolFilterForm
    form_class = forms.LoadBalancerPoolForm
    lookup_field = "pk"
    queryset = models.LoadBalancerPool.objects.all()
    serializer_class = serializers.LoadBalancerPoolSerializer
    table_class = tables.LoadBalancerPoolTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["name", "tenant"],
            ),
            ObjectFieldsPanel(
                weight=200,
                label="Configuration",
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "load_balancing_algorithm",
                    "health_check_monitor",
                ],
            ),
            ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=300,
                table_class=tables.VirtualServerTable,
                table_filter="load_balancer_pool",
                table_title="Virtual Servers",
                exclude_columns=["load_balancer_pool", "tenant", "actions"],
                add_button_route=None,
            ),
            ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=400,
                table_class=tables.LoadBalancerPoolMemberTable,
                table_filter="load_balancer_pool",
                table_title="Load Balancer Pool Members",
                exclude_columns=["load_balancer_pool", "ssl_offload", "tenant", "actions"],
                add_button_route=None,
            ),
        ],
    )


class LoadBalancerPoolMemberUIViewSet(NautobotUIViewSet):
    """ViewSet for LoadBalancerPoolMember."""

    bulk_update_form_class = forms.LoadBalancerPoolMemberBulkEditForm
    filterset_class = filters.LoadBalancerPoolMemberFilterSet
    filterset_form_class = forms.LoadBalancerPoolMemberFilterForm
    form_class = forms.LoadBalancerPoolMemberForm
    lookup_field = "pk"
    queryset = models.LoadBalancerPoolMember.objects.all()
    serializer_class = serializers.LoadBalancerPoolMemberSerializer
    table_class = tables.LoadBalancerPoolMemberTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["ip_address", "port", "label", "tenant", "load_balancer_pool"],
            ),
            ObjectFieldsPanel(
                weight=200,
                label="Configuration",
                section=SectionChoices.RIGHT_HALF,
                fields=[
                    "ssl_offload",
                    "health_check_monitor",
                ],
            ),
            ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=400,
                table_class=tables.CertificateProfileTable,
                table_filter="load_balancer_pool_members",
                table_title="Certificate Profiles",
                exclude_columns=["tenant", "actions"],
                add_button_route=None,
            ),
        ],
    )


class HealthCheckMonitorUIViewSet(NautobotUIViewSet):
    """ViewSet for HealthCheckMonitor."""

    bulk_update_form_class = forms.HealthCheckMonitorBulkEditForm
    filterset_class = filters.HealthCheckMonitorFilterSet
    filterset_form_class = forms.HealthCheckMonitorFilterForm
    form_class = forms.HealthCheckMonitorForm
    lookup_field = "pk"
    queryset = models.HealthCheckMonitor.objects.all()
    serializer_class = serializers.HealthCheckMonitorSerializer
    table_class = tables.HealthCheckMonitorTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "health_check_type",
                    "port",
                    "interval",
                    "timeout",
                    "retry",
                    "tenant",
                ],
            ),
            StatsPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                label="Stats",
                filter_name="health_check_monitor",
                related_models=[models.VirtualServer, models.LoadBalancerPool, models.LoadBalancerPoolMember],
            ),
        ],
    )


class CertificateProfileUIViewSet(NautobotUIViewSet):
    """ViewSet for CertificateProfile."""

    bulk_update_form_class = forms.CertificateProfileBulkEditForm
    filterset_class = filters.CertificateProfileFilterSet
    filterset_form_class = forms.CertificateProfileFilterForm
    form_class = forms.CertificateProfileForm
    lookup_field = "pk"
    queryset = models.CertificateProfile.objects.all()
    serializer_class = serializers.CertificateProfileSerializer
    table_class = tables.CertificateProfileTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "certificate_type",
                    "certificate_file_path",
                    "chain_file_path",
                    "key_file_path",
                    "expiration_date",
                    "cipher",
                    "tenant",
                ],
            ),
            StatsPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=300,
                label="Stats",
                filter_name="certificate_profiles",
                related_models=[models.VirtualServer, models.LoadBalancerPoolMember],
            ),
        ],
    )
