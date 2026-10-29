"""Page object for the Dynamic Group edit form (/extras/dynamic-groups/<pk>/edit/)."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage, select2_filter_pick


class DynamicGroupEditPage(BasePage):
    """The Dynamic Group edit form's filter fields."""

    EDIT_PATH = "/extras/dynamic-groups/{pk}/edit/"

    _UPDATE_BUTTON = "button[name='_update']"

    def navigate(self, pk):
        """Go to the edit form of the group *pk*."""
        self._goto(self.EDIT_PATH.format(pk=pk))

    def add_filter_value(self, field_name, value):
        """Add *value* to the edit form's multi-value filter field *field_name* (e.g. "location").

        The option text is matched as a substring, because location options show their full ancestry path.
        """
        select2_filter_pick(self.page, f"filter-{field_name}", search=value, pick_text=value, exact=False)
        expect(self.page.locator(f"select[name='filter-{field_name}'] option:checked", has_text=value)).to_have_count(1)

    def save(self):
        """Submit the edit form and assert that it redirected away from the form."""
        self._click_and_wait_for_navigation(self._UPDATE_BUTTON)
        self.expect_url_lacks("/edit/")
