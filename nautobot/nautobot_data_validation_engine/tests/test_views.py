"""Unit tests for nautobot_data_validation_engine views."""

from unittest import skipIf
from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.http.request import QueryDict
from packaging import version

from nautobot.core.testing import TestCase, ViewTestCases
from nautobot.dcim.models import Device, Location, LocationType, PowerFeed
from nautobot.extras.models import Status
from nautobot.nautobot_data_validation_engine.models import (
    DataCompliance,
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.nautobot_data_validation_engine.tables import DataComplianceTableTab
from nautobot.nautobot_data_validation_engine.tests.test_data_compliance_rules import TestFailedDataComplianceRule
from nautobot.nautobot_data_validation_engine.views import DataComplianceObjectView

try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata

_NAUTOBOT_VERSION = version.parse(metadata.version("nautobot"))
# Related to this issue: https://github.com/nautobot/nautobot/issues/2948
_FAILING_OBJECT_LIST_NAUTOBOT_VERSIONS = [version.parse("1.5.2"), version.parse("1.5.3"), version.parse("1.5.4")]


class RegularExpressionValidationRuleTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the RegularExpressionValidationRule model."""

    model = RegularExpressionValidationRule

    @skipIf(
        _NAUTOBOT_VERSION in _FAILING_OBJECT_LIST_NAUTOBOT_VERSIONS,
        f"Skip test in Nautobot version {_NAUTOBOT_VERSION} due to Nautobot issue #2948",
    )
    def test_list_objects_with_permission(self):
        super().test_list_objects_with_permission()

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


class MinMaxValidationRuleTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the MinMaxValidationRule model."""

    model = MinMaxValidationRule

    @skipIf(
        _NAUTOBOT_VERSION in _FAILING_OBJECT_LIST_NAUTOBOT_VERSIONS,
        f"Skip test in Nautobot version {_NAUTOBOT_VERSION} due to Nautobot issue #2948",
    )
    def test_list_objects_with_permission(self):
        super().test_list_objects_with_permission()

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


class RequiredValidationRuleTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the RequiredValidationRule model."""

    model = RequiredValidationRule

    @skipIf(
        _NAUTOBOT_VERSION in _FAILING_OBJECT_LIST_NAUTOBOT_VERSIONS,
        f"Skip test in Nautobot version {_NAUTOBOT_VERSION} due to Nautobot issue #2948",
    )
    def test_list_objects_with_permission(self):
        super().test_list_objects_with_permission()

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


class UniqueValidationRuleTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    """View test cases for the UniqueValidationRule model."""

    model = UniqueValidationRule

    @skipIf(
        _NAUTOBOT_VERSION in _FAILING_OBJECT_LIST_NAUTOBOT_VERSIONS,
        f"Skip test in Nautobot version {_NAUTOBOT_VERSION} due to Nautobot issue #2948",
    )
    def test_list_objects_with_permission(self):
        super().test_list_objects_with_permission()

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

    @skipIf(
        _NAUTOBOT_VERSION in _FAILING_OBJECT_LIST_NAUTOBOT_VERSIONS,
        f"Skip test in Nautobot version {_NAUTOBOT_VERSION} due to Nautobot issue #2948",
    )
    def test_list_objects_with_permission(self):
        super().test_list_objects_with_permission()

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
        location_type = LocationType(name="Region")
        location_type.validated_save()
        s = Location(
            name="Test Location 1",
            location_type=LocationType.objects.get_by_natural_key("Region"),
            status=Status.objects.get_by_natural_key("Active"),
        )
        s.save()
        t = TestFailedDataComplianceRule(s)
        t.clean()

    def test_get_extra_context(self):
        view = DataComplianceObjectView()
        location = Location.objects.first()
        mock_request = MagicMock()
        mock_request.GET = QueryDict("tab=nautobot_data_validation_engine:1")
        result = view.get_extra_context(mock_request, location)
        self.assertEqual(result["active_tab"], "nautobot_data_validation_engine:1")
        self.assertIsInstance(result["table"], DataComplianceTableTab)

    @patch("nautobot.core.views.generic.ObjectView.dispatch")
    def test_dispatch(self, mocked_dispatch):
        view = DataComplianceObjectView()
        mock_request = MagicMock()
        kwargs = {"model": "dcim.location", "other_arg": "other_arg", "another_arg": "another_arg"}
        view.dispatch(mock_request, **kwargs)
        mocked_dispatch.assert_called()
        mocked_dispatch.assert_called_with(mock_request, other_arg="other_arg", another_arg="another_arg")
