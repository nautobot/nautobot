"""Page object for the Devices list view's static group assignment modal (/dcim/devices/)."""

from playwright.sync_api import expect

from nautobot.dcim.tests.integration.pages.devices_page import DevicesPage


class DeviceGroupAssignmentPage(DevicesPage):
    """The Devices list view's "Update Group Assignment" modal, which assigns devices to static groups."""

    # In the select-all box, so it is enabled only once every matching record is selected.
    _UPDATE_GROUPS_FOR_ALL = "#update_dynamic_groups_for_all"
    _ASSIGNMENT_MODAL = "#dynamic_group_assignment_modal"
    _ADD_TO_GROUPS = "select[name='add_to_groups']"
    _ASSIGNMENT_APPLY = "#dynamic_group_assignment_form button[type='submit']"

    def assign_all_matching_to_group(self, group_name):
        """Click "Update Group Assignment for All", add the selection to the group *group_name*, and apply.

        Call `select_all_matching` first: the button is disabled until the select-all box is checked.
        """
        self.page.locator(self._UPDATE_GROUPS_FOR_ALL).click()
        expect(self.page.locator(self._ASSIGNMENT_MODAL)).to_be_visible()
        self.page.locator(f"{self._ADD_TO_GROUPS} + span.select2-container").click()
        # Select2 sizes this multi-select's search box while the modal is still hidden, so the box
        # has no width and Playwright will not fill it. The click focuses it, so type instead.
        self.page.keyboard.type(group_name)
        self.page.locator(".select2-dropdown").get_by_text(group_name, exact=True).click()
        expect(self.page.locator(f"{self._ADD_TO_GROUPS} option:checked", has_text=group_name)).to_have_count(1)
        self._click_and_wait_for_navigation(self._ASSIGNMENT_APPLY)
