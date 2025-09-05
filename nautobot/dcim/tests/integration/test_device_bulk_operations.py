import uuid

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from nautobot.core.testing.integration import (
    BulkOperationsTestCases,
    SeleniumTestCase,
)
from nautobot.dcim.models import Device
from nautobot.extras.tests.integration import create_test_device


class DeviceBulkOperationsTestCase(BulkOperationsTestCases.BulkOperationsTestCase):
    """
    Test devices bulk edit / delete operations.
    """

    model_menu_path = ("Devices", "Devices")
    model_base_viewname = "dcim:device"
    model_edit_data = {"serial": "Test serial"}
    model_filter_by = {"location": "Test Location 2"}
    model_class = Device

    def setup_items(self):
        Device.objects.all().delete()
        test_uuid = str(uuid.uuid4())

        # Create device for test
        create_test_device("Test Device Integration Test 1", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 2", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 3", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 4", "Test Location 2", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 5", "Test Location 2", test_uuid=test_uuid)


class DeviceBulkUrlParamTestCase(SeleniumTestCase):
    """
    Integration test to check that when a bulk edit is initiated from a filtered device list view it does not fill in bulk edit form.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.device1 = create_test_device("Device 1")

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_param_fills_device_type(self):
        """
        This test:
         1 Go to device list page with param for device_type
         2 Selects the row checkbox for the device with that device_type
         3 Submits the bulk edit form
         4 Checks that the device_type field is blank (i.e. "---------") on the bulk edit form
        """

        # Go to Device list page
        self.browser.visit(
            self.live_server_url + reverse("dcim:device_list") + f"?device_type={self.device1.device_type.pk}"
        )

        # 2) Check the row checkbox exactly matching the PK
        pk = str(self.device1.pk)
        cb_xpath = f'//input[@type="checkbox" and @name="pk" and @value="{pk}"]'
        checkbox = WebDriverWait(self.browser.driver, 2).until(
            expected_conditions.element_to_be_clickable((By.XPATH, cb_xpath))
        )
        self.browser.driver.execute_script("arguments[0].click();", checkbox)

        # Click the bulk-edit button (it uses formaction)
        bulk_url = reverse("dcim:device_bulk_edit")
        btn_xpath = f'//button[@type="submit" and @formaction="{bulk_url}"]'
        bulk_btn = WebDriverWait(self.browser.driver, 2).until(
            expected_conditions.element_to_be_clickable((By.XPATH, btn_xpath))
        )
        # We know this works since if nothing is selected, you will be redirected back to the list view with a message
        bulk_btn.click()

        self.assertTrue(
            WebDriverWait(self.browser.driver, 2).until(
                lambda d: d.find_element(By.CLASS_NAME, "select2-selection__placeholder").text.strip() == "---------"
            )
        )
