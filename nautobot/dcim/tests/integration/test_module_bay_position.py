from django.urls import reverse

from nautobot.core.testing.integration import ObjectsListMixin, SeleniumTestCase
from nautobot.dcim.models import DeviceType, Manufacturer, Module, ModuleBay, ModuleType
from nautobot.extras.models import Status
from nautobot.extras.tests.integration import create_test_device


class ModuleBayPositionTestCase(SeleniumTestCase, ObjectsListMixin):
    """
    Test creating a module bay component in device and device type.
    """

    def _validate_position_field(self):
        # Fill name pattern
        name_pattern_field = self.browser.find_by_css("#id_name_pattern")
        name_pattern_value = "name-0/0/[0-9]"
        for _ in name_pattern_field.type(name_pattern_value, slowly=True):
            pass

        # Verify that position is filled
        position_field = self.browser.find_by_css("#id_position_pattern")
        self.assertEqual(position_field.value, name_pattern_value, "Position field value is not properly set")

        # Change pattern manually and name to verify if it's not updating then
        position_field.fill("")
        for _ in position_field.type("new pattern", slowly=True):
            pass

        for _ in name_pattern_field.type("v2", slowly=True):
            pass

        self.assertEqual(position_field.value, "new pattern", "Position field value has unexpectedly changed")

        # Regenerate position
        self.browser.find_by_css('button[data-original-title="Regenerate position"]').click()
        self.assertEqual(position_field.value, f"{name_pattern_value}v2", "Position field value is not re-populated")

    def test_create_device_type_module_bay(self):
        self.login_as_superuser()

        manufacturer, _ = Manufacturer.objects.get_or_create(
            name="Test Manufacturer",
        )
        device_type, _ = DeviceType.objects.get_or_create(manufacturer=manufacturer, model="Test Model Module Bay")

        details_url = self.live_server_url + reverse("dcim:devicetype", kwargs={"pk": device_type.pk})
        self.browser.visit(details_url)

        # Navigate to module bay create page
        self.browser.find_by_css("#device-type-add-components-button").click()
        self.browser.find_by_xpath(
            "//*[@id='device-type-add-components-button']/following-sibling::*//a[normalize-space()='Module Bays']"
        ).click()

        self._validate_position_field()

    def test_create_device_module_bay(self):
        self.login_as_superuser()

        device = create_test_device("Test Device Module Bay Integration Test 1")
        details_url = self.live_server_url + reverse("dcim:device", kwargs={"pk": device.pk})
        self.browser.visit(details_url)

        # Navigate to module bay create page
        self.browser.find_by_css("#device-add-components-button").click()
        self.browser.find_by_xpath(
            "//*[@id='device-add-components-button']/following-sibling::*//a[normalize-space()='Module Bays']"
        ).click()

        self._validate_position_field()

    def test_bulk_create_device_module_bay(self):
        self.login_as_superuser()

        device = create_test_device("Test Device Module Bay Integration Test 1", test_uuid="a15a58b0b")
        self.browser.visit(self.live_server_url + reverse("dcim:device_list"))

        self.apply_filter("location", "a15a58b0b")

        self.select_one_item(pk=device.pk)
        self.browser.find_by_css("#device-bulk-add-components-button").click()
        self.browser.find_by_xpath(
            "//*[@id='device-bulk-add-components-button']/following-sibling::*//a[normalize-space()='Module Bays']"
        ).click()

        self._validate_position_field()

    def test_create_module_type_module_bay(self):
        self.login_as_superuser()

        manufacturer, _ = Manufacturer.objects.get_or_create(name="Test Manufacturer")
        module_type = ModuleType.objects.create(model="Module_Type", manufacturer=manufacturer)

        details_url = self.live_server_url + reverse("dcim:moduletype", kwargs={"pk": module_type.pk})
        self.browser.visit(details_url)

        self.browser.find_by_css("#module-type-add-components-button").click()
        self.browser.find_by_xpath(
            "//*[@id='module-type-add-components-button']/following-sibling::*//a[normalize-space()='Module Bays']"
        ).click()

        self._validate_position_field()

    def test_bulk_create_module_module_bay(self):
        self.login_as_superuser()

        device = create_test_device("Test Device Module Bay Integration Test 2", test_uuid="60a7d5e")
        module_type = ModuleType.objects.create(model="Module_Type", manufacturer=device.device_type.manufacturer)
        device_module_bay = ModuleBay.objects.create(parent_device=device, name="Test Bay")
        module = Module.objects.create(
            module_type=module_type,
            status=Status.objects.get_for_model(Module).first(),
            parent_module_bay=device_module_bay,
        )

        self.browser.visit(self.live_server_url + reverse("dcim:module_list"))
        self.select_one_item(pk=module.pk)

        self.browser.find_by_css("#module-bulk-add-components-button").click()
        self.browser.find_by_xpath(
            "//*[@id='module-bulk-add-components-button']/following-sibling::*//a[normalize-space()='Module Bays']"
        ).click()

        self._validate_position_field()
