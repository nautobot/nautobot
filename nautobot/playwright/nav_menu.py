"""Shared component object for the navigation menu, the sidenav (`nav#sidenav`) on every logged-in page.

The sidenav lists one tab per `li[data-section-name]`. Each tab is a button and a flyout. The flyout holds
one `<ul>` per group: the group's label (`li.nb-sidenav-link-group`) followed by its item links. The server
leaves out every item the user has no permission for, then every group left with no items, then every tab
left with no groups, so a tab or group the user cannot use is missing from the DOM rather than hidden.

Every tab's flyout is in the DOM from page load but is not displayed until its tab is clicked. Read labels
with `text_content()`: `inner_text()` returns '' for anything not displayed, so it reads every label of a
closed flyout as blank. A link must be displayed before it can be clicked, so expand its tab first.

The Favorites flyout reuses the group and link classes, but its `<li>` has no `data-section-name`, so
scoping everything to the tabs keeps favorites out of the results.
"""

import re

from playwright.sync_api import expect, Page


def _exact(text):
    """Regex that matches *text* as the whole of an element's text, ignoring surrounding whitespace."""
    return re.compile(rf"^\s*{re.escape(text)}\s*$")


class NavMenu:
    """The sidenav on the current page: its tabs, their groups and items, and expanding a tab.

    A component, not a page: it does no navigation of its own. Build it on a page that a page object
    has already loaded:

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

    def tab_names(self):
        """Return the name of every rendered tab, in order."""
        return [tab.get_attribute("data-section-name") for tab in self.page.locator(self._TAB).all()]

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
        if not self.is_tab_expanded(tab_name):
            self.tab(tab_name).locator(self._TAB_BUTTON).click()
        self.expect_tab_expanded(tab_name)

    def collapse_tab(self, tab_name):
        """Close the flyout of tab *tab_name*, unless it is already closed, and wait until it is hidden."""
        if self.is_tab_expanded(tab_name):
            self.tab(tab_name).locator(self._TAB_BUTTON).click()
        self.expect_tab_collapsed(tab_name)

    def is_tab_expanded(self, tab_name):
        """Return True if the flyout of tab *tab_name* is open, read from its button's `aria-expanded`."""
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
        label = self.page.locator(self._GROUP_LABEL).filter(has_text=_exact(group_name))
        return self.tab(tab_name).locator(self._GROUP).filter(has=label)

    def group_labels(self, tab_name):
        """Return the label of every group in tab *tab_name*, read with `text_content()` so a closed flyout reads too."""
        labels = self.tab(tab_name).locator(f"{self._GROUP} > {self._GROUP_LABEL}")
        return [(label.text_content() or "").strip() for label in labels.all()]

    def item_labels(self, tab_name, group_name):
        """Return the label of every item in group *group_name* of tab *tab_name*, read with `text_content()`."""
        links = self.group(tab_name, group_name).locator(self._ITEM_LINK)
        return [(link.text_content() or "").strip() for link in links.all()]

    def item_link(self, tab_name, group_name, item_name):
        """Locator for the item link labeled exactly *item_name* in group *group_name* of tab *tab_name*."""
        return self.group(tab_name, group_name).locator(self._ITEM_LINK).filter(has_text=_exact(item_name))
