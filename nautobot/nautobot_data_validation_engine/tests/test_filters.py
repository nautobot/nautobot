"""
Filterset test cases
"""

from django.contrib.contenttypes.models import ContentType

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


class RegularExpressionValidationRuleFilterTestCase(FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the RegularExpressionValidationRule model
    """

    queryset = RegularExpressionValidationRule.objects.all()
    filterset = RegularExpressionValidationRuleFilterSet
    # TODO Look into enabling the generic filter tests to replace the filter tests that are defined.
    generic_filter_tests = []

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
            content_type=ContentType.objects.get_for_model(Location),
            field="comments",
            regular_expression="GHI",
            error_message="C",
        )

    def test_id(self):
        """Test ID lookups."""
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        """Test content type lookups."""
        params = {"content_type": ["dcim.rack", "dcim.location"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_regular_expression(self):
        """Test regex lookups."""
        # TODO(john): revisit this once this is sorted: https://github.com/nautobot/nautobot/issues/477
        params = {"regular_expression": "^ABC$"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_error_message(self):
        """Test error message lookups."""
        params = {"error_message": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_field(self):
        """Test field lookups."""
        params = {"field": ["name", "description"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class MinMaxValidationRuleFilterTestCase(FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the MinMaxValidationRule model
    """

    queryset = MinMaxValidationRule.objects.all()
    filterset = MinMaxValidationRuleFilterSet
    # TODO Look into enabling the generic filter tests to replace the filter tests that are defined.
    generic_filter_tests = []

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

    def test_id(self):
        """Test ID lookups."""
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        """Test content type lookups."""
        params = {"content_type": ["dcim.powerfeed"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_error_message(self):
        """Test error message lookups."""
        params = {"error_message": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_field(self):
        """Test field lookups."""
        params = {"field": ["voltage", "max_utilization"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class RequiredValidationRuleFilterTestCase(FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the RequiredValidationRule model
    """

    queryset = RequiredValidationRule.objects.all()
    filterset = RequiredValidationRuleFilterSet
    # TODO Look into enabling the generic filter tests to replace the filter tests that are defined.
    generic_filter_tests = []

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
            field="description",
            error_message="B",
        )
        RequiredValidationRule.objects.create(
            name="Required rule 3",
            content_type=ContentType.objects.get_for_model(Manufacturer),
            field="description",
            error_message="C",
        )

    def test_id(self):
        """Test ID lookups."""
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        """Test content type lookups."""
        params = {"content_type": ["dcim.location"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_error_message(self):
        """Test error message lookups."""
        params = {"error_message": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_field(self):
        """Test field lookups."""
        params = {"field": ["asn"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class UniqueValidationRuleFilterTestCase(FilterTestCases.NameOnlyFilterTestCase):
    """
    Filterset test cases for the UniqueValidationRule model
    """

    queryset = UniqueValidationRule.objects.all()
    filterset = UniqueValidationRuleFilterSet
    # TODO Look into enabling the generic filter tests to replace the filter tests that are defined.
    generic_filter_tests = []

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
            field="description",
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

    def test_id(self):
        """Test ID lookups."""
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        """Test content type lookups."""
        params = {"content_type": ["dcim.location"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_error_message(self):
        """Test error message lookups."""
        params = {"error_message": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_field(self):
        """Test field lookups."""
        params = {"field": ["asn"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_max_instances(self):
        """Test field lookups."""
        params = {"max_instances__gte": [2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
