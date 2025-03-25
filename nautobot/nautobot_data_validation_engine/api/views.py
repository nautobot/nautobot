"""API views for nautobot_data_validation_engine."""

from nautobot.apps.api import NautobotModelViewSet
from nautobot.nautobot_data_validation_engine import filters, models
from nautobot.nautobot_data_validation_engine.api import serializers


class RegularExpressionValidationRuleViewSet(NautobotModelViewSet):
    """View to manage regular expression validation rules."""

    queryset = models.RegularExpressionValidationRule.objects.all()
    serializer_class = serializers.RegularExpressionValidationRuleSerializer
    filterset_class = filters.RegularExpressionValidationRuleFilterSet


class MinMaxValidationRuleViewSet(NautobotModelViewSet):
    """View to manage min max expression validation rules."""

    queryset = models.MinMaxValidationRule.objects.all()
    serializer_class = serializers.MinMaxValidationRuleSerializer
    filterset_class = filters.MinMaxValidationRuleFilterSet


class RequiredValidationRuleViewSet(NautobotModelViewSet):
    """View to manage required field validation rules."""

    queryset = models.RequiredValidationRule.objects.all()
    serializer_class = serializers.RequiredValidationRuleSerializer
    filterset_class = filters.RequiredValidationRuleFilterSet


class UniqueValidationRuleViewSet(NautobotModelViewSet):
    """View to manage unique value validation rules."""

    queryset = models.UniqueValidationRule.objects.all()
    serializer_class = serializers.UniqueValidationRuleSerializer
    filterset_class = filters.UniqueValidationRuleFilterSet


class DataComplianceAPIView(NautobotModelViewSet):
    """API Views for DataCompliance."""

    queryset = models.DataCompliance.objects.all()
    serializer_class = serializers.DataComplianceSerializer
