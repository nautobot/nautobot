from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.dcim.models import Device
from nautobot.extras.models import DynamicGroup
from nautobot.utilities.testing.integration import SeleniumTestCase

from . import create_test_device


class DynamicGroupTestCase(SeleniumTestCase):
    """
    Integration test to check nautobot.extras.models.DynamicGroup add/edit functionality.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_create_and_update(self):
        """
        Test initial add and then update of a new DynamicGroup
        """
        devices = [create_test_device() for _ in range(5)]
        content_type = ContentType.objects.get_for_model(Device)
        ct_label = f"{content_type.app_label}.{content_type.model}"

        # Navigate to the DynamicGroups list view
        self.browser.links.find_by_partial_text("Organization").click()
        self.browser.links.find_by_partial_text("Dynamic Groups").click()

        # Click add button
        self.browser.find_by_id("add-button").click()

        # Fill out the form.
        name = "devices-active"
        self.browser.fill("name", name)
        # self.browser.fill("slug", name)  # slug should be auto-populated
        self.browser.select("content_type", ct_label)

        # Click that "Create" button
        self.browser.find_by_text("Create").click()

        # Verify form redirect and presence of content.
        self.assertTrue(self.browser.is_text_present(f"Created dynamic group {name}"))
        self.assertTrue(self.browser.is_text_present("Edit"))

        # Edit the newly created DynamicGroup (Click that "Edit" button)
        self.browser.find_by_id("edit-button").click()

        # Find the "Status" dynamic multi-select and type into it. Xpath is used
        # to find the next "input" after the "status" select field.
        status_field = self.browser.find_by_name("filter-status").first
        status_input = status_field.find_by_xpath("./following::input[1]").first
        status_input.click()  # Force focus on the input field to bring it on-screen

        # Fill in "Status: Active".
        for _ in status_input.type("act\n", slowly=True):
            pass

        # Click that "Update" button
        self.browser.find_by_text("Update").click()

        # Verify form redirect and presence of content.
        self.assertTrue(self.browser.is_text_present(f"Modified dynamic group {name}"))
        self.assertTrue(self.browser.is_text_present("Edit"))

        # And just a cursory check to make sure that the filter worked.
        group = DynamicGroup.objects.get(name=name)
        self.assertEqual(group.count, len(devices))
        self.assertEqual(group.filter, {"status": ["active"]})

        # Verify dynamic group shows up on device detail tab
        self.browser.visit(
            f'{self.live_server_url}{reverse("dcim:device_dynamicgroups", kwargs={"pk": devices[0].pk})}'
        )
        self.assertTrue(self.browser.is_text_present(name))
