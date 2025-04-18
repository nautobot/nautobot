"""Views for data_validation."""

from django.apps import apps as global_apps
from django.contrib.contenttypes.models import ContentType
from django_tables2 import RequestConfig

from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import (
    ObjectDetailContent,
    ObjectFieldsPanel,
)
from nautobot.core.views.generic import ObjectView
from nautobot.core.views.mixins import (
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
)
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.data_validation import filters, forms, tables
from nautobot.data_validation.api import serializers
from nautobot.data_validation.models import (
    DataCompliance,
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.extras.utils import get_base_template

#
# RegularExpressionValidationRules
#


class RegularExpressionValidationRuleUIViewSet(NautobotUIViewSet):
    """Views for the RegularExpressionValidationRule model."""

    bulk_update_form_class = forms.RegularExpressionValidationRuleBulkEditForm
    filterset_class = filters.RegularExpressionValidationRuleFilterSet
    filterset_form_class = forms.RegularExpressionValidationRuleFilterForm
    form_class = forms.RegularExpressionValidationRuleForm
    queryset = RegularExpressionValidationRule.objects.all()
    serializer_class = serializers.RegularExpressionValidationRuleSerializer
    table_class = tables.RegularExpressionValidationRuleTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        ),
    )


#
# MinMaxValidationRules
#


class MinMaxValidationRuleUIViewSet(NautobotUIViewSet):
    """Views for the MinMaxValidationRuleUIViewSet model."""

    bulk_update_form_class = forms.MinMaxValidationRuleBulkEditForm
    filterset_class = filters.MinMaxValidationRuleFilterSet
    filterset_form_class = forms.MinMaxValidationRuleFilterForm
    form_class = forms.MinMaxValidationRuleForm
    queryset = MinMaxValidationRule.objects.all()
    serializer_class = serializers.MinMaxValidationRuleSerializer
    table_class = tables.MinMaxValidationRuleTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        ),
    )


#
# RequiredValidationRules
#


class RequiredValidationRuleUIViewSet(NautobotUIViewSet):
    """Views for the RequiredValidationRuleUIViewSet model."""

    bulk_update_form_class = forms.RequiredValidationRuleBulkEditForm
    filterset_class = filters.RequiredValidationRuleFilterSet
    filterset_form_class = forms.RequiredValidationRuleFilterForm
    form_class = forms.RequiredValidationRuleForm
    queryset = RequiredValidationRule.objects.all()
    serializer_class = serializers.RequiredValidationRuleSerializer
    table_class = tables.RequiredValidationRuleTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        ),
    )


#
# UniqueValidationRules
#


class UniqueValidationRuleUIViewSet(NautobotUIViewSet):
    """Views for the UniqueValidationRuleUIViewSet model."""

    bulk_update_form_class = forms.UniqueValidationRuleBulkEditForm
    filterset_class = filters.UniqueValidationRuleFilterSet
    filterset_form_class = forms.UniqueValidationRuleFilterForm
    form_class = forms.UniqueValidationRuleForm
    queryset = UniqueValidationRule.objects.all()
    serializer_class = serializers.UniqueValidationRuleSerializer
    table_class = tables.UniqueValidationRuleTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        ),
    )


#
# DataCompliance
#


class DataComplianceUIViewSet(  # pylint: disable=W0223
    ObjectListViewMixin,
    ObjectDetailViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """Views for the DataComplianceUIViewSet model."""

    lookup_field = "pk"
    queryset = DataCompliance.objects.all()
    table_class = tables.DataComplianceTable
    filterset_class = filters.DataComplianceFilterSet
    filterset_form_class = forms.DataComplianceFilterForm
    serializer_class = serializers.DataComplianceSerializer
    action_buttons = ("export",)
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        )
    )


class DataComplianceObjectView(ObjectView):
    """View for the Audit Results tab dynamically generated on specific object detail views."""

    template_name = "data_validation/datacompliance_tab.html"
    queryset = None

    def dispatch(self, request, *args, **kwargs):
        """Set the queryset for the given object and call the inherited dispatch method."""
        model = kwargs.pop("model")
        if not self.queryset:
            self.queryset = global_apps.get_model(model).objects.all()
        return super().dispatch(request, *args, **kwargs)

    def get_extra_context(self, request, instance):
        """Generate extra context for rendering the DataComplianceObjectView template."""
        compliance_objects = DataCompliance.objects.filter(
            content_type=ContentType.objects.get_for_model(instance), object_id=instance.id
        )
        compliance_table = tables.DataComplianceTableTab(compliance_objects)
        base_template = get_base_template(None, instance)

        paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        RequestConfig(request, paginate).configure(compliance_table)
        return {"active_tab": request.GET["tab"], "table": compliance_table, "base_template": base_template}
