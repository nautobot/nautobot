"""
Filterset test cases
"""

from django.contrib.contenttypes.models import ContentType

from nautobot.circuits.models import Provider
from nautobot.core.testing.filters import FilterTestCases
from nautobot.dcim.models import Location, Manufacturer, Platform, PowerFeed, Rack
from nautobot.extras.models import Tag
from nautobot.nautobot_data_validation_engine.filters import (
    MinMaxValidationRuleFilterSet,
    RegularExpressionValidationRuleFilterSet,
    RequiredValidationRuleFilterSet,
    UniqueValidationRuleFilterSet,
)
from nautobot.nautobot_data_validation_engine.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)


class ValidationRuleTestMixin:
    """
    Content type test mixin for validation rule filter test cases
    """

    def test_content_type(self):
        """Test content type lookups."""
        expected_queryset = self.queryset.filter(
            content_type__pk__in=[
                ContentType.objects.get_for_model(Location).pk,
                ContentType.objects.get_for_model(Manufacturer).pk,
            ]
        ).distinct()
        params = {"content_type": ["dcim.location", "dcim.manufacturer"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected_queryset)


class RegularExpressionValidationRuleFilterTestCase(ValidationRuleTestMixin, FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the RegularExpressionValidationRule model
    """

    queryset = RegularExpressionValidationRule.objects.all()
    filterset = RegularExpressionValidationRuleFilterSet
    generic_filter_tests = [
        ("id",),
        ("regular_expression",),
        ("error_message",),
        ("field",),
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        tag_1 = Tag.objects.first()
        tag_1.content_types.set([ContentType.objects.get_for_model(RegularExpressionValidationRule)])
        tag_2 = Tag.objects.last()
        tag_2.content_types.set([ContentType.objects.get_for_model(RegularExpressionValidationRule)])
        regex_1 = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Rack),
            field="name",
            regular_expression="^ABC$",
            error_message="A",
        )
        regex_1.tags.set([tag_1, tag_2])
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 2",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            regular_expression="DEF$",
            error_message="B",
        )
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 3",
            content_type=ContentType.objects.get_for_model(Provider),
            field="comments",
            regular_expression="GHI",
            error_message="C",
        )


class MinMaxValidationRuleFilterTestCase(ValidationRuleTestMixin, FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the MinMaxValidationRule model
    """

    queryset = MinMaxValidationRule.objects.all()
    filterset = MinMaxValidationRuleFilterSet
    generic_filter_tests = [
        ("id",),
        ("error_message",),
        ("field",),
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        tag_1 = Tag.objects.first()
        tag_1.content_types.set([ContentType.objects.get_for_model(MinMaxValidationRule)])
        tag_2 = Tag.objects.last()
        tag_2.content_types.set([ContentType.objects.get_for_model(MinMaxValidationRule)])
        min_max_1 = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
            min=1,
            error_message="A",
        )
        min_max_1.tags.set([tag_1, tag_2])
        MinMaxValidationRule.objects.create(
            name="Min max rule 2",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="max_utilization",
            min=1,
            error_message="B",
        )
        MinMaxValidationRule.objects.create(
            name="Min max rule 3",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="voltage",
            min=1,
            error_message="C",
        )

    def test_content_type(self):
        """Test content type lookups."""
        params = {"content_type": ["dcim.powerfeed"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class RequiredValidationRuleFilterTestCase(ValidationRuleTestMixin, FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the RequiredValidationRule model
    """

    queryset = RequiredValidationRule.objects.all()
    filterset = RequiredValidationRuleFilterSet
    generic_filter_tests = [
        ("id",),
        ("error_message",),
        ("field",),
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        tag_1 = Tag.objects.first()
        tag_1.content_types.set([ContentType.objects.get_for_model(RequiredValidationRule)])
        tag_2 = Tag.objects.last()
        tag_2.content_types.set([ContentType.objects.get_for_model(RequiredValidationRule)])
        required_1 = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="asn",
            error_message="A",
        )
        required_1.tags.set([tag_1, tag_2])
        RequiredValidationRule.objects.create(
            name="Required rule 2",
            content_type=ContentType.objects.get_for_model(Platform),
            field="name",
            error_message="B",
        )
        RequiredValidationRule.objects.create(
            name="Required rule 3",
            content_type=ContentType.objects.get_for_model(Manufacturer),
            field="description",
            error_message="C",
        )


class UniqueValidationRuleFilterTestCase(ValidationRuleTestMixin, FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the UniqueValidationRule model
    """

    queryset = UniqueValidationRule.objects.all()
    filterset = UniqueValidationRuleFilterSet
    generic_filter_tests = [
        ("id",),
        ("error_message",),
        ("field",),
        ("max_instances",),
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        tag_1 = Tag.objects.first()
        tag_1.content_types.set([ContentType.objects.get_for_model(UniqueValidationRule)])
        tag_2 = Tag.objects.last()
        tag_2.content_types.set([ContentType.objects.get_for_model(UniqueValidationRule)])
        unique_1 = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="asn",
            max_instances=1,
            error_message="A",
        )
        unique_1.tags.set([tag_1, tag_2])
        UniqueValidationRule.objects.create(
            name="Unique rule 2",
            content_type=ContentType.objects.get_for_model(Platform),
            field="name",
            max_instances=2,
            error_message="B",
        )
        UniqueValidationRule.objects.create(
            name="Unique rule 3",
            content_type=ContentType.objects.get_for_model(Manufacturer),
            field="description",
            max_instances=3,
            error_message="C",
        )
