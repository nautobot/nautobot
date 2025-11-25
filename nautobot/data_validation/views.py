"""Views for data_validation."""

from constance import config
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, render

from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import (
    ObjectDetailContent,
    ObjectFieldsPanel,
)
from nautobot.core.ui.titles import Titles
from nautobot.core.views.generic import GenericView
from nautobot.core.views.mixins import (
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
)
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.data_validation import filters, forms, models, tables
from nautobot.data_validation.api import serializers
from nautobot.dcim.models import Device

#
# RegularExpressionValidationRules
#


class RegularExpressionValidationRuleUIViewSet(NautobotUIViewSet):
    """Views for the RegularExpressionValidationRule model."""

    bulk_update_form_class = forms.RegularExpressionValidationRuleBulkEditForm
    filterset_class = filters.RegularExpressionValidationRuleFilterSet
    filterset_form_class = forms.RegularExpressionValidationRuleFilterForm
    form_class = forms.RegularExpressionValidationRuleForm
    queryset = models.RegularExpressionValidationRule.objects.all()
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
    queryset = models.MinMaxValidationRule.objects.all()
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
    queryset = models.RequiredValidationRule.objects.all()
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
    queryset = models.UniqueValidationRule.objects.all()
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
    queryset = models.DataCompliance.objects.all()
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
                fields=[
                    "content_type",
                    "compliance_class_name",
                    "last_validation_date",
                    "validated_object",
                    "validated_attribute",
                    "validated_attribute_value",
                    "valid",
                    "message",
                ],
            ),
        )
    )


class DeviceConstraintsView(GenericView):
    template_name = "data_validation/device_constraints.html"
    view_titles = Titles(titles={"*": "Device Constraints"})

    def get(self, request):
        form = forms.DeviceConstraintsForm(user=request.user)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "view_titles": self.get_view_titles(),
            },
        )

    def post(self, request):
        if not request.user.is_staff:
            return self.handle_no_permission()
        form = forms.DeviceConstraintsForm(request.POST)
        if form.is_valid():
            config.DEVICE_UNIQUENESS = form.cleaned_data["DEVICE_UNIQUENESS"]
            device_ct = ContentType.objects.get_for_model(Device)
            if form.cleaned_data["DEVICE_NAME_REQUIRED"]:
                models.RequiredValidationRule.objects.get_or_create(
                    content_type=device_ct,
                    field="name",
                    defaults={"name": "Require Device Name"},
                )
            else:
                models.RequiredValidationRule.objects.filter(
                    content_type=device_ct,
                    field="name",
                ).delete()

            messages.success(request, "Device constraints have been updated successfully.")
            return redirect("data_validation:device-constraints")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "view_titles": self.get_view_titles(),
                "breadcrumbs": self.get_breadcrumbs(),
            },
        )
