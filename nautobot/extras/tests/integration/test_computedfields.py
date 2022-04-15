from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.dcim.models import Device
from nautobot.extras.models import ComputedField
from nautobot.utilities.testing.integration import SeleniumTestCase

from . import create_test_device


class ComputedFieldsTestCase(SeleniumTestCase):
    """
    Integration test to check nautobot.extras.models.ComputedField.advanced_ui functionality
    and computed fields appearing in an object list
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)
        self.device = create_test_device()
        self.computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Device),
            slug="device_computed_field",
            label="Device Computed Field",
            template="{{ obj.name }} is awesome!",
        )

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_computed_field_advanced_ui(self):
        """
        This test creates a device and a computed field for that device.
        It first leaves the computed field advanced_ui default of False to be show on the primary information
        tab in the UI and checks it is there.
        It secondly sets the computed field to be shown only in the "Advanced" tab in the UI
        and checks it appears ONLY there!.
        """
        # Visit the device detail page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device", kwargs={"pk": self.device.pk})}')
        # Check the computed field appears in the primary information tab
        self.assertTrue(self.browser.is_text_present("Device Computed Field"))
        self.assertTrue(self.browser.is_text_present(f"{self.device.name} is awesome!"))
        # # Check the computed field does NOT appear in the advanced tab
        self.browser.links.find_by_partial_text("Advanced")[0].click()
        self.assertFalse(self.browser.is_text_present("Device Computed Field"))
        self.assertFalse(self.browser.is_text_present(f"{self.device.name} is awesome!"))
        # Set the custom_field to only show in the advanced tab
        self.computed_field.advanced_ui = True
        self.computed_field.save()
        # Visit the device detail page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device", kwargs={"pk": self.device.pk})}')
        # Check the computed field does NOT appear in the primary information tab
        self.assertFalse(self.browser.is_text_present("Device Computed Field"))
        self.assertFalse(self.browser.is_text_present(f"{self.device.name} is awesome!"))
        # Check the computed field appears in the advanced tab
        self.browser.links.find_by_partial_text("Advanced")[0].click()
        self.assertTrue(self.browser.is_text_present("Device Computed Field"))
        self.assertTrue(self.browser.is_text_present(f"{self.device.name} is awesome!"))

    def test_computed_field_appears_in_object_list(self):
        """
        This test sets the computed field to be visible on the object list
        and then checks to see if it actually appears there.
        """
        self.browser.visit(f"{self.live_server_url}/dcim/devices/")
        self.browser.find_by_xpath(".//button[@title='Configure table']").click()
        select_option = self.browser.find_by_xpath(
            ".//select[@id='id_columns']/option[contains(text(), 'Device Computed Field')]"
        )
        self.assertEqual(len(select_option), 1)
        select_option.click()
        self.browser.find_by_xpath(".//input[@value='Save']").click()
        self.assertTrue(self.browser.is_text_present(f"{self.device.name} is awesome!"))
        self.browser.find_by_xpath(".//button[@title='Configure table']").click()
        self.browser.find_by_xpath(".//input[@value='Reset']").click()
        self.assertFalse(self.browser.is_text_present(f"{self.device.name} is awesome!"))
