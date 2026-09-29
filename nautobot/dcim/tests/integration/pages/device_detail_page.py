"""Page object for the Device detail view (/dcim/devices/<pk>/)."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class DeviceDetailPage(BasePage):
    """The Device detail view and its in-page tabs (e.g. "main" and "advanced")."""

    # Each tab's content is a pane with the tab's id. Every pane is in the DOM at once;
    # only the active one is visible.
    _TAB_PANE = "div.tab-pane#{tab_id}"
    # The header renders each tab link twice, one of them hidden (a responsive duplicate),
    # so only the visible one is clickable.
    _TAB_LINK = "ul[data-nb-tests-id='object-details-header-tabs-ul'] a[role='tab'][aria-controls='{tab_id}']:visible"

    def navigate(self, pk):
        """Go to the detail view of the device with primary key *pk*."""
        self._goto(f"/dcim/devices/{pk}/")

    def _tab_pane(self, tab_id):
        """Locator for the content pane of the tab *tab_id*."""
        return self.page.locator(self._TAB_PANE.format(tab_id=tab_id))

    def open_tab(self, tab_id):
        """Click the header link of the tab *tab_id* and wait for its pane to show."""
        self.page.locator(self._TAB_LINK.format(tab_id=tab_id)).click()
        expect(self._tab_pane(tab_id)).to_be_visible()

    def expect_tab_to_show(self, tab_id, text):
        """Assert (auto-retrying) that the tab *tab_id* visibly renders *text*."""
        expect(self._tab_pane(tab_id).get_by_text(text, exact=True)).to_be_visible()

    def expect_tab_not_to_contain(self, tab_id, text):
        """Assert (auto-retrying) that the tab *tab_id* does not contain *text*, shown or hidden."""
        expect(self._tab_pane(tab_id)).not_to_contain_text(text)
