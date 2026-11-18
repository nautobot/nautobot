"""Shared component object for the sidenav (`nav#sidenav`), which has one `li[data-section-name]` per tab.

A tab, group or item that the user may not view is missing from the DOM, not hidden. Every flyout is in
the DOM from page load, so read labels with `text_content()`, because `inner_text()` returns '' in a closed
flyout. Expand a tab before clicking one of its links. Lookups are scoped to `li[data-section-name]`,
because the Favorites flyout uses the same group and link classes without that attribute.
"""

from playwright.sync_api import expect, Page

from nautobot.playwright.helpers import exact_text


class NavMenu:
    """The sidenav on the current page: its tabs, their groups and items, and expanding a tab.

    It is a component, not a page, so it never navigates. Create it on a page that a page object has
    already loaded:

        HomePage(page, base_url).navigate()
        nav = NavMenu(page)
    """

    _TAB = "nav#sidenav li[data-section-name]"
    _TAB_BUTTON = ":scope > button.nb-sidenav-list-item"
    _FLYOUT = ":scope > div.nb-sidenav-flyout"
    _GROUP = ":scope > div.nb-sidenav-flyout > ul"
    _GROUP_LABEL = "li.nb-sidenav-link-group"
    _ITEM_LINK = "a.nb-sidenav-link"

    def __init__(self, page: Page):
        """Bind the component to a Playwright *page*."""
        self.page = page

    # -------------------------------------------------------------------------
    # Tabs
    # -------------------------------------------------------------------------

    def tab(self, tab_name):
        """Locator for the tab named *tab_name*."""
        return self.page.locator(f'{self._TAB}[data-section-name="{tab_name}"]')

    def expect_tab(self, tab_name):
        """Assert (auto-retrying) that the sidenav has exactly one tab named *tab_name*."""
        expect(self.tab(tab_name)).to_have_count(1)

    def expect_no_tab(self, tab_name):
        """Assert (auto-retrying) that the sidenav has no tab named *tab_name*."""
        expect(self.tab(tab_name)).to_have_count(0)

    def expand_tab(self, tab_name):
        """Open the flyout of tab *tab_name*, unless it is already open, and wait until it is displayed.

        The button toggles, so clicking an open tab would close it.
        """
        if not self._is_tab_expanded(tab_name):
            self.tab(tab_name).locator(self._TAB_BUTTON).click()
        self.expect_tab_expanded(tab_name)

    def collapse_tab(self, tab_name):
        """Close the flyout of tab *tab_name*, unless it is already closed, and wait until it is hidden."""
        if self._is_tab_expanded(tab_name):
            self.tab(tab_name).locator(self._TAB_BUTTON).click()
        self.expect_tab_collapsed(tab_name)

    def _is_tab_expanded(self, tab_name):
        """Return True if the flyout of tab *tab_name* is open, read once from its button's `aria-expanded`.

        Only `expand_tab()` and `collapse_tab()` call it, to decide whether to click. Tests assert the state
        with `expect_tab_expanded()` or `expect_tab_collapsed()`, which retry.
        """
        return self.tab(tab_name).locator(self._TAB_BUTTON).get_attribute("aria-expanded") == "true"

    def expect_tab_expanded(self, tab_name):
        """Assert (auto-retrying) that the flyout of tab *tab_name* is open and displayed."""
        tab = self.tab(tab_name)
        expect(tab.locator(self._TAB_BUTTON)).to_have_attribute("aria-expanded", "true")
        expect(tab.locator(self._FLYOUT)).to_be_visible()

    def expect_tab_collapsed(self, tab_name):
        """Assert (auto-retrying) that the flyout of tab *tab_name* is closed and not displayed."""
        tab = self.tab(tab_name)
        expect(tab.locator(self._TAB_BUTTON)).to_have_attribute("aria-expanded", "false")
        expect(tab.locator(self._FLYOUT)).to_be_hidden()

    # -------------------------------------------------------------------------
    # Groups and items
    # -------------------------------------------------------------------------

    def group(self, tab_name, group_name):
        """Locator for the group labeled exactly *group_name* in tab *tab_name*: its label and its item links.

        Group names are not unique across tabs ("Metadata" is in both Organization and Extensibility),
        so a group is always looked up within its tab.
        """
        label = self.page.locator(self._GROUP_LABEL).filter(has_text=exact_text(group_name))
        return self.tab(tab_name).locator(self._GROUP).filter(has=label)

    def expect_group(self, tab_name, group_name):
        """Assert (auto-retrying) that tab *tab_name* has exactly one group labeled *group_name*."""
        expect(self.group(tab_name, group_name)).to_have_count(1)

    def item_link(self, tab_name, group_name, item_name):
        """Locator for the item link labeled exactly *item_name* in group *group_name* of tab *tab_name*."""
        return self.group(tab_name, group_name).locator(self._ITEM_LINK).filter(has_text=exact_text(item_name))

    def expect_item(self, tab_name, group_name, item_name):
        """Assert (auto-retrying) that group *group_name* of tab *tab_name* has exactly one *item_name* link."""
        expect(self.item_link(tab_name, group_name, item_name)).to_have_count(1)
