"""DataComplianceRule test cases."""

from django.test import TestCase

from nautobot.data_validation.custom_validators import ComplianceError, DataComplianceRule
from nautobot.data_validation.models import DataCompliance
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status


class TestFailedDataComplianceRule(DataComplianceRule):
    """Test implementation of DataComplianceRule."""

    model = "dcim.location"

    def audit(self):
        """Raises an AuditError."""
        # this should create 4 different Audits, one for each
        # attribute
        raise ComplianceError(
            {
                "tenant": "The tenant is wrong",
                "name": "The name is wrong",
                "status": "The status is wrong",
            }
        )


class TestPassedDataComplianceRule(DataComplianceRule):
    """Test implementation of DataComplianceRule."""

    model = "dcim.location"

    def audit(self):
        """No exception means the audit passes."""


class TestFailedDataComplianceRuleAlt(TestFailedDataComplianceRule):
    """Test implementation of DataComplianceRule, for dcim.rack."""

    model = "dcim.device"


class TestCompliance(TestCase):
    """Test DataComplianceRule methods."""

    def setUp(self):
        self.location_type = LocationType(name="Region")
        self.location_type.save()
        self.s = Location(
            name="Test 1",
            location_type=LocationType.objects.get_by_natural_key("Region"),
            status=Status.objects.get_by_natural_key("Active"),
        )
        self.s.save()
        TestFailedDataComplianceRule(self.s).clean()
        TestPassedDataComplianceRule(self.s).clean()

    def test_audit_success(self):
        result = DataCompliance.objects.filter(valid=True).all()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.compliance_class_name, "TestPassedDataComplianceRule")
        self.assertEqual(result.validated_object, self.s)
        self.assertEqual(result.validated_attribute, "__all__")
        self.assertEqual(result.validated_attribute_value, "")

    def test_audit_fail(self):
        result = DataCompliance.objects.filter(valid=False).all()
        self.assertEqual(len(result), 4)
        result = DataCompliance.objects.get(validated_attribute="tenant")
        self.assertEqual(result.compliance_class_name, "TestFailedDataComplianceRule")
        self.assertEqual(result.validated_object, self.s)
        self.assertIn(result.validated_attribute, "tenant")
        self.assertEqual(result.validated_attribute_value, "")

    def test_validate_replaces_results(self):
        self.assertEqual(
            len(DataCompliance.objects.filter(compliance_class_name=TestFailedDataComplianceRule.__name__)), 4
        )
        TestFailedDataComplianceRule(self.s).clean()
        self.assertEqual(
            len(DataCompliance.objects.filter(compliance_class_name=TestFailedDataComplianceRule.__name__)),
            4,
        )
