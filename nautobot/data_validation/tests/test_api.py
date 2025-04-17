"""Unit tests for data_validation."""

from django.contrib.contenttypes.models import ContentType

from nautobot.core.testing import APIViewTestCases
from nautobot.data_validation.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.data_validation.tests import ValidationRuleTestCaseMixin
from nautobot.dcim.models import Location, Manufacturer, Platform, PowerFeed


class RegularExpressionValidationRuleTest(ValidationRuleTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """
    API view test cases for the RegularExpressionValidationRule model
    """

    model = RegularExpressionValidationRule
    choices_fields = {"content_type"}

    create_data = [
        {
            "name": "Regex rule 4",
            "content_type": "dcim.location",
            "field": "contact_name",
            "regular_expression": "^.*$",
        },
        {
            "name": "Regex rule 5",
            "content_type": "dcim.location",
            "field": "physical_address",
            "regular_expression": "^.*$",
        },
        {
            "name": "Regex rule 6",
            "content_type": "dcim.location",
            "field": "shipping_address",
            "regular_expression": "^.*$",
        },
    ]
    bulk_update_data = {
        "enabled": False,
    }

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="name",
            regular_expression="^.*$",
        )
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 2",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            regular_expression="^.*$",
        )
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 3",
            content_type=ContentType.objects.get_for_model(Location),
            field="comments",
            regular_expression="^.*$",
        )


class MinMaxValidationRuleTest(ValidationRuleTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """
    API view test cases for the MinMaxValidationRule model
    """

    model = MinMaxValidationRule
    choices_fields = {"content_type"}

    create_data = [
        {
            "name": "Min max rule 4",
            "content_type": "dcim.device",
            "field": "vc_position",
            "min": 0,
            "max": 1,
        },
        {
            "name": "Min max rule 5",
            "content_type": "dcim.device",
            "field": "vc_priority",
            "min": -5.6,
            "max": 0,
        },
        {
            "name": "Min max rule 6",
            "content_type": "dcim.device",
            "field": "position",
            "min": 5,
            "max": 6,
        },
    ]
    bulk_update_data = {
        "enabled": False,
    }

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
            min=1,
        )
        MinMaxValidationRule.objects.create(
            name="Min max rule 2",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="max_utilization",
            min=1,
        )
        MinMaxValidationRule.objects.create(
            name="Min max rule 3",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="voltage",
            min=1,
        )


class RequiredValidationRuleTest(ValidationRuleTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """
    API view test cases for the RequiredValidationRule model
    """

    model = RequiredValidationRule
    choices_fields = {"content_type"}

    create_data = [
        {
            "name": "Required rule 4",
            "content_type": "dcim.location",
            "field": "physical_address",
        },
        {
            "name": "Required rule 5",
            "content_type": "dcim.location",
            "field": "asn",
        },
        {
            "name": "Required rule 6",
            "content_type": "dcim.location",
            "field": "facility",
        },
    ]
    bulk_update_data = {
        "enabled": False,
    }

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
        )
        RequiredValidationRule.objects.create(
            name="Required rule 2",
            content_type=ContentType.objects.get_for_model(Platform),
            field="description",
        )
        RequiredValidationRule.objects.create(
            name="Required rule 3",
            content_type=ContentType.objects.get_for_model(Manufacturer),
            field="description",
        )


class UniqueValidationRuleTest(ValidationRuleTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """
    API view test cases for the UniqueValidationRule model
    """

    model = UniqueValidationRule
    choices_fields = {"content_type"}

    create_data = [
        {
            "name": "Unique rule 4",
            "content_type": "dcim.location",
            "field": "physical_address",
            "max_instances": 1,
        },
        {
            "name": "Unique rule 5",
            "content_type": "dcim.location",
            "field": "asn",
            "max_instances": 2,
        },
        {
            "name": "Unique rule 6",
            "content_type": "dcim.location",
            "field": "facility",
            "max_instances": 3,
        },
    ]
    bulk_update_data = {
        "enabled": False,
    }

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            max_instances=1,
        )
        UniqueValidationRule.objects.create(
            name="Unique rule 2",
            content_type=ContentType.objects.get_for_model(Platform),
            field="description",
            max_instances=2,
        )
        UniqueValidationRule.objects.create(
            name="Unique rule 3",
            content_type=ContentType.objects.get_for_model(Manufacturer),
            field="description",
            max_instances=3,
        )
