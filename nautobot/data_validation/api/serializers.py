"""API serializers for data_validation."""

from django.contrib.contenttypes.models import ContentType

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin
from nautobot.core.api import ContentTypeField
from nautobot.data_validation.models import (
    DataCompliance,
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.extras.utils import FeatureQuery


class RegularExpressionValidationRuleSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for `RegularExpressionValidationRule` objects."""

    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()),
    )

    class Meta:
        """Serializer metadata for RegularExpressionValidationRule objects."""

        model = RegularExpressionValidationRule
        fields = "__all__"


class MinMaxValidationRuleSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for `MinMaxValidationRule` objects."""

    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()),
    )

    class Meta:
        """Serializer metadata for MinMaxValidationRule objects."""

        model = MinMaxValidationRule
        fields = "__all__"


class RequiredValidationRuleSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for `RequiredValidationRule` objects."""

    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()),
    )

    class Meta:
        """Serializer metadata for RequiredValidationRule objects."""

        model = RequiredValidationRule
        fields = "__all__"


class UniqueValidationRuleSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for `UniqueValidationRule` objects."""

    content_type = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()),
    )

    class Meta:
        """Serializer metadata for UniqueValidationRule objects."""

        model = UniqueValidationRule
        fields = "__all__"


class DataComplianceSerializer(NautobotModelSerializer):
    """Serializer for DataCompliance."""

    class Meta:
        """Meta class for serializer."""

        model = DataCompliance
        fields = "__all__"
