"""Unit tests for data_validation views."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.core.testing import TestCase, ViewTestCases
from nautobot.data_validation.models import (
    DataCompliance,
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.data_validation.tests import ValidationRuleTestCaseMixin
from nautobot.data_validation.tests.test_data_compliance_rules import (
    TestFailedDataComplianceRule,
    TestFailedDataComplianceRuleAlt,
)
from nautobot.dcim.models import Device, Location, LocationType, PowerFeed
from nautobot.extras.models import Status

User = get_user_model()


class RegularExpressionValidationRuleTestCase(ValidationRuleTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the RegularExpressionValidationRule model."""

    model = RegularExpressionValidationRule

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

        cls.form_data = {
            "name": "Regex rule x",
            "content_type": ContentType.objects.get_for_model(Location).pk,
            "field": "contact_name",
            "regular_expression": "^.*$",
        }

        cls.csv_data = (
            "name,content_type,field,regular_expression",
            "Regex rule 4,dcim.location,contact_phone,^.*$",
            "Regex rule 5,dcim.location,physical_address,^.*$",
            "Regex rule 6,dcim.location,shipping_address,^.*$",
        )

        cls.bulk_edit_data = {
            "regular_expression": "^.*.*$",
            "enabled": False,
            "error_message": "no soup",
        }


class MinMaxValidationRuleTestCase(ValidationRuleTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the MinMaxValidationRule model."""

    model = MinMaxValidationRule

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

        cls.form_data = {
            "name": "Min max rule x",
            "content_type": ContentType.objects.get_for_model(Device).pk,
            "field": "position",
            "min": 5.0,
            "max": 6.0,
        }

        cls.csv_data = (
            "name,content_type,field,min,max",
            "Min max rule 4,dcim.device,vc_position,5,6",
            "Min max rule 5,dcim.device,vc_priority,5,6",
            "Min max rule 6,dcim.location,longitude,5,6",
        )

        cls.bulk_edit_data = {
            "min": 5.0,
            "max": 6.0,
            "enabled": False,
            "error_message": "no soup",
        }


class RequiredValidationRuleTestCase(ValidationRuleTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the RequiredValidationRule model."""

    model = RequiredValidationRule

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="asn",
        )
        RequiredValidationRule.objects.create(
            name="Required rule 2",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
        )
        RequiredValidationRule.objects.create(
            name="Required rule 3",
            content_type=ContentType.objects.get_for_model(Location),
            field="comments",
        )

        cls.form_data = {
            "name": "Required rule x",
            "content_type": ContentType.objects.get_for_model(Location).pk,
            "field": "contact_name",
        }

        cls.csv_data = (
            "name,content_type,field",
            "Required rule 4,dcim.location,contact_phone",
            "Required rule 5,dcim.location,physical_address",
            "Required rule 6,dcim.location,shipping_address",
        )

        cls.bulk_edit_data = {
            "enabled": False,
            "error_message": "no soup",
        }


class UniqueValidationRuleTestCase(ValidationRuleTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the UniqueValidationRule model."""

    model = UniqueValidationRule

    @classmethod
    def setUpTestData(cls):
        """
        Create test data
        """
        UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="asn",
            max_instances=1,
        )
        UniqueValidationRule.objects.create(
            name="Unique rule 2",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            max_instances=2,
        )
        UniqueValidationRule.objects.create(
            name="Unique rule 3",
            content_type=ContentType.objects.get_for_model(Location),
            field="comments",
            max_instances=3,
        )

        cls.form_data = {
            "name": "Unique rule x",
            "content_type": ContentType.objects.get_for_model(Location).pk,
            "field": "contact_name",
            "max_instances": 4,
        }

        cls.csv_data = (
            "name,content_type,field,max_instances",
            "Unique rule 4,dcim.location,contact_phone,1",
            "Unique rule 5,dcim.location,physical_address,2",
            "Unique rule 6,dcim.location,shipping_address,3",
        )

        cls.bulk_edit_data = {
            "max_instances": 4,
            "enabled": False,
            "error_message": "no soup",
        }


class DataComplianceTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    """Test cases for DataCompliance Viewset."""

    model = DataCompliance

    @classmethod
    def setUpTestData(cls):
        location_type = LocationType(name="Region")
        location_type.validated_save()
        s = Location(
            name="Test Location 1",
            location_type=LocationType.objects.get_by_natural_key("Region"),
            status=Status.objects.get_by_natural_key("Active"),
        )
        s.save()
        for _ in range(4):
            t = TestFailedDataComplianceRule(s)
            t.clean()


class DataComplianceObjectTestCase(TestCase):
    """Test cases for DataComplianceObjectView."""

    def setUp(self):
        self.device = Device.objects.first()

        t = TestFailedDataComplianceRuleAlt(self.device)
        t.clean()
        self.user = User.objects.create_user(username="testuser", is_superuser=True)

    def test_data_compliance_action(self):
        self.add_permissions("data_validation.view_datacompliance")
        self.client.force_login(self.user)
        url = reverse("dcim:device_data-compliance", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("active_tab", response.context)
        self.assertEqual(response.context["active_tab"], "data_compliance")
        self.assertBodyContains(response, "The tenant is wrong")
        self.assertBodyContains(response, "The name is wrong")
        self.assertBodyContains(response, "The status is wrong")
