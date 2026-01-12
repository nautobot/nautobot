from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import ObjectsListMixin, SeleniumTestCase
from nautobot.dcim.models import Device
from nautobot.extras.models import DynamicGroup

from . import create_test_device


class DynamicGroupTestCase(SeleniumTestCase, ObjectsListMixin):
    """
    Integration test to check nautobot.extras.models.DynamicGroup add/edit functionality.
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def test_create_and_update(self):
        """
        Test initial add and then update of a new DynamicGroup
        """
        devices = [create_test_device() for _ in range(5)]
        content_type = ContentType.objects.get_for_model(Device)
        ct_label = f"{content_type.app_label}.{content_type.model}"

        # Navigate to the DynamicGroups list view
        self.click_navbar_entry("Organization", "Dynamic Groups")

        # Click add button
        self.click_add_item()

        # Fill out the form.
        name = "devices-active"
        self.fill_input("name", name)
        self.browser.select("content_type", ct_label)

        # Click that "Create" button
        self.click_edit_form_create_button()

        # Verify form redirect and presence of content.
        self.assertTrue(self.browser.is_text_present(f"Created dynamic group {name}"))
        self.assertTrue(self.browser.is_text_present("Edit"))

        # Edit the newly created DynamicGroup (Click that "Edit" button)
        self.click_button("#edit-button")

        # Find the "Status" dynamic multi-select and type into it. Xpath is used
        # to find the next "input" after the "status" select field.
        status_field = self.browser.find_by_name("filter-status").first
        status_input = status_field.find_by_xpath("./following::input[1]").first
        self.scroll_element_into_view(element=status_input)
        status_input.click()  # Force focus on the input field to bring it on-screen

        # Fill in "Status: Active".
        for _ in status_input.type("act", slowly=True):
            pass
        status_input.type(Keys.ENTER)

        # Click that "Update" button
        self.browser.find_by_xpath("//button[normalize-space()='Update']").click()

        # Verify form redirect and presence of content.
        self.assertTrue(self.browser.is_text_present(f"Modified dynamic group {name}"))
        self.assertTrue(self.browser.is_text_present("Edit"))

        # And just a cursory check to make sure that the filter worked.
        group = DynamicGroup.objects.get(name=name)
        self.assertEqual(group.filter, {"status": ["Active"]})
        # Because we don't auto-refresh the members on UI create/update any more:
        # TODO: a more complete integration test could click the "Refresh Members" JobButton, wait until the job completes,
        #       and so forth, rather than doing so programmatically here:
        group.update_cached_members()
        self.assertEqual(group.count, Device.objects.filter(status__name="Active").count())

        # Verify dynamic group shows up on device detail tab
        self.browser.visit(
            f"{self.live_server_url}{reverse('dcim:device_dynamicgroups', kwargs={'pk': devices[0].pk})}"
        )
        self.assertTrue(self.browser.is_text_present(name))
