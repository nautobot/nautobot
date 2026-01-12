"""Unit tests for data_validation views."""

from constance import config
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse

from nautobot.core import settings
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
from nautobot.dcim.choices import DeviceUniquenessChoices
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


class DeviceConstraintsViewTest(TestCase):
    """Tests for the DeviceConstraintsView."""

    def setUp(self):
        self.initial_setting = config.DEVICE_UNIQUENESS
        self.url = reverse("data_validation:device-constraints")
        self.device_ct = ContentType.objects.get_for_model(Device)

    def tearDown(self):
        """Reset Constance config and clear cache."""
        config.DEVICE_UNIQUENESS = self.initial_setting
        cache = caches[settings.CONSTANCE_DATABASE_CACHE_BACKEND]
        cache.clear()

    @override_settings(
        DEVICE_UNIQUENESS=DeviceUniquenessChoices.NONE,
    )
    def test_page_reflects_correct_settings_for_non_staff(self):
        """Non-staff view still shows the actual configuration, but in disabled form."""
        user = get_user_model().objects.create_user(username="testuser")
        self.client.force_login(user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # Ensure fields are disabled but reflect correct config values
        self.assertContains(response, f'value="{DeviceUniquenessChoices.NONE}" selected')
        self.assertContains(response, "disabled")
        self.assertContains(response, "You do not have permission to modify these settings.")

        # DEVICE_NAME_REQUIRED should NOT be checked, because RequiredValidationRule not exist
        device_ct = ContentType.objects.get_for_model(Device)
        self.assertFalse(RequiredValidationRule.objects.filter(content_type=device_ct, field="name").exists())
        self.assertNotContains(response, 'name="DEVICE_NAME_REQUIRED" checked')

        # Footer buttons should NOT be rendered
        self.assertNotContains(response, '<button type="submit"')
        self.assertNotContains(response, "-->Update")
        self.assertNotContains(response, "-->Cancel")

    @override_settings(
        DEVICE_UNIQUENESS=DeviceUniquenessChoices.NAME,
    )
    def test_page_reflects_correct_settings_for_staff(self):
        """Page should reflect the true values of DEVICE_UNIQUENESS and DEVICE_NAME_REQUIRED."""
        # Create RequiredValidationRule to check proper value of DEVICE_NAME_REQUIRED
        device_ct = ContentType.objects.get_for_model(Device)
        RequiredValidationRule.objects.create(
            name="Required Name rule",
            content_type=device_ct,
            field="name",
        )
        user = get_user_model().objects.create_user(username="testuser", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data_validation/device_constraints.html")

        self.assertIn("form", response.context)
        self.assertContains(response, "Device Constraints")

        # Check that the correct DEVICE_UNIQUENESS option is selected
        self.assertContains(response, f'value="{DeviceUniquenessChoices.NAME}" selected')

        self.assertNotContains(response, "disabled")
        self.assertNotContains(response, "You do not have permission to modify these settings.")

        # Check that DEVICE_NAME_REQUIRED checkbox is checked when RequiredValidationRule exist
        self.assertTrue(RequiredValidationRule.objects.filter(content_type=device_ct, field="name").exists())
        self.assertContains(response, 'id="id_DEVICE_NAME_REQUIRED" checked')

        # Footer buttons should be rendered
        self.assertContains(response, '<button type="submit"')
        self.assertContains(response, "-->Update")
        self.assertContains(response, "-->Cancel")

    def test_post_as_non_admin_denied(self):
        """POST by non-admin should be denied."""
        user = get_user_model().objects.create_user(username="normaluser")
        self.client.force_login(user)

        response = self.client.post(
            self.url,
            data={
                "DEVICE_UNIQUENESS": DeviceUniquenessChoices.LOCATION_TENANT_NAME,
                "DEVICE_NAME_REQUIRED": True,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 403)

        # No rule should be created
        self.assertFalse(RequiredValidationRule.objects.filter(content_type=self.device_ct, field="name").exists())
        self.assertEqual(config.DEVICE_UNIQUENESS, self.initial_setting)

    def test_post_updates_device_uniqueness_and_creates_required_rule(self):
        """POST with DEVICE_NAME_REQUIRED=True should create a RequiredValidationRule."""
        user = get_user_model().objects.create_user(username="testuser", is_staff=True)
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            {
                "DEVICE_UNIQUENESS": DeviceUniquenessChoices.NAME,
                "DEVICE_NAME_REQUIRED": True,
            },
            follow=True,
        )

        self.assertRedirects(response, self.url)
        self.assertEqual(config.DEVICE_UNIQUENESS, "name")

        rule_exists = RequiredValidationRule.objects.filter(
            content_type=self.device_ct,
            field="name",
        ).exists()
        self.assertTrue(rule_exists)

    def test_post_disables_required_rule(self):
        """POST with DEVICE_NAME_REQUIRED=False should delete the RequiredValidationRule."""
        user = get_user_model().objects.create_user(username="testuser", is_staff=True)
        self.client.force_login(user)
        RequiredValidationRule.objects.create(
            name="Required Name rule",
            content_type=self.device_ct,
            field="name",
        )
        self.assertTrue(RequiredValidationRule.objects.filter(content_type=self.device_ct, field="name").exists())

        response = self.client.post(
            self.url,
            {
                "DEVICE_UNIQUENESS": DeviceUniquenessChoices.LOCATION_TENANT_NAME,
                "DEVICE_NAME_REQUIRED": False,
            },
            follow=True,
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(config.DEVICE_UNIQUENESS, DeviceUniquenessChoices.LOCATION_TENANT_NAME)

        self.assertFalse(RequiredValidationRule.objects.filter(content_type=self.device_ct, field="name").exists())

    def test_invalid_post_rerenders_form(self):
        """If form is invalid, the view should re-render without redirect for multiple invalid inputs."""
        user = get_user_model().objects.create_user(username="testuser", is_staff=True)
        self.client.force_login(user)

        invalid_inputs = [
            {"DEVICE_UNIQUENESS": ""},
            {"DEVICE_UNIQUENESS": "invalid_value"},
        ]

        for post_data in invalid_inputs:
            with self.subTest(post_data=post_data):
                response = self.client.post(self.url, post_data)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "data_validation/device_constraints.html")
                self.assertIn("form", response.context)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(config.DEVICE_UNIQUENESS, self.initial_setting)
