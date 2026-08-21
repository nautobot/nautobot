"""Shared page object for Nautobot object list views.

Every list view (locations, devices, prefixes, ...) renders the same table structure
and the same filter drawer, so their shared behavior lives here and a markup change is
a single edit. Subclasses set `_LIST_PATH` and add only what is specific to their
model:

    class LocationsPage(ListPage):
        _LIST_PATH = "/dcim/locations/"
"""

from nautobot.e2e.base_page import BasePage, select2_filter_pick


class ListPage(BasePage):
    """Shared list-view behavior: navigation, table reads, and the filter drawer."""

    _LIST_PATH = ""  # REQUIRED in subclass, e.g. "/dcim/locations/"

    # A data row is a body row with a pk checkbox, which excludes the empty-state row
    # rendered when a list has no results. Reference this constant, never inline it.
    _DATA_ROWS = "table tbody tr:has(input[name='pk'])"

    # The filter drawer and its dynamic-filter UI render identically on every list view.
    _FILTER_TOGGLE = "button#id__filterbtn"
    _FILTER_DRAWER = "#FilterForm_drawer"
    _FILTER_APPLY_BASIC = "#FilterForm_drawer #default-filter button[type='submit']"
    _ADVANCED_FILTER_TAB = "#FilterForm_drawer a[href='#advanced-filter']"
    _FILTER_APPLY_ADVANCED = "#FilterForm_drawer #advanced-filter button[type='submit']"
    # Each active filter field renders one outer badge (data-nb-field names the field);
    # its direct remove button clears the whole field, while each value inside carries
    # its own nested remove button.
    _FILTER_BADGE = ".nb-dynamic-filter-items span.nb-multi-badge"
    _FILTER_BADGE_REMOVE = "button.nb-dynamic-filter-remove"
    _FILTER_BADGE_VALUE_ITEM = ".nb-multi-badge-items span.badge"
    # Scoped to the filter button: other toolbar controls (e.g. saved-view state)
    # reuse the nb-btn-indicator class for their own dots.
    _FILTER_INDICATOR = "button#id__filterbtn span.nb-btn-indicator"

    def __init__(self, page, base_url):
        """Fail fast on a subclass that forgot to set `_LIST_PATH`."""
        if not self._LIST_PATH:
            raise ValueError(f"{type(self).__name__} must set _LIST_PATH (e.g. '/dcim/locations/').")
        super().__init__(page, base_url)

    # -------------------------------------------------------------------------
    # Navigation and table reads
    # -------------------------------------------------------------------------

    def navigate(self):
        """Go to the list view."""
        self._goto(self._LIST_PATH)

    def get_data_row_count(self) -> int:
        """Return the number of data rows (rows with a pk checkbox) in the table."""
        return self.page.locator(self._DATA_ROWS).count()

    def get_table_column_headers(self) -> list:
        """Text of all non-empty column headers (the checkbox column has none).

        Sortable headers embed a visually-hidden sort instruction ("activate to sort
        ascending") that innerText renders on its own line, so only the first line of
        each header is kept.
        """
        headers = [text.split("\n")[0].strip() for text in self.page.locator("table thead th").all_inner_texts()]
        return [header for header in headers if header]

    def get_column_values_by_header(self, header_name) -> list:
        """Cell values for the column whose header text is *header_name*.

        The checkbox column has no header text and is filtered out of
        `get_table_column_headers()`, so header index 0 maps to td position 2.
        Raises if the header is not present, rather than silently returning nothing.
        """
        headers = self.get_table_column_headers()
        if header_name not in headers:
            raise ValueError(f"No column headed {header_name!r} on this list view; got {headers}.")
        # The +2 assumes exactly one unheaded column (the pk checkbox) precedes the
        # headed ones; if a list view ever breaks that assumption, fix it here and in
        # get_table_column_headers/_DATA_ROWS together.
        column_position = headers.index(header_name) + 2
        cells = self.page.locator(f"{self._DATA_ROWS} td:nth-child({column_position})")
        return [text.strip() for text in cells.all_inner_texts()]

    # -------------------------------------------------------------------------
    # Filter drawer
    # -------------------------------------------------------------------------

    def is_filter_drawer_open(self) -> bool:
        """Return True if the filter drawer is currently open.

        Open state is the `nb-drawer-open` class on the drawer element. Playwright's
        `is_visible()` cannot be used here: the closed drawer sits off-canvas but
        still has a layout box, so it reads as "visible" even when closed.
        """
        return self.page.locator(f"{self._FILTER_DRAWER}.nb-drawer-open").count() > 0

    def open_filter_drawer(self):
        """Click the Filter toolbar button and wait for the drawer to open."""
        self.page.locator(self._FILTER_TOGGLE).click()
        self.page.locator(f"{self._FILTER_DRAWER}.nb-drawer-open").wait_for(state="attached", timeout=8_000)

    def pick_filter_value(self, field_name, value, exact=True):
        """Pick *value* in the drawer's Select2 filter field named *field_name*.

        Pass `exact=False` for fields whose options render an ancestry path
        (e.g. location fields: "Parent → Child").
        """
        select2_filter_pick(self.page, field_name, search=value, pick_text=value, exact=exact)

    def apply_filters(self):
        """Submit the drawer's basic-tab filter form and wait for the filtered reload."""
        self._click_and_wait_for_navigation(self._FILTER_APPLY_BASIC)

    def open_advanced_filter_tab(self):
        """Switch the filter drawer to its Advanced tab, opening the drawer if needed."""
        if not self.is_filter_drawer_open():
            self.open_filter_drawer()
        self.page.locator(self._ADVANCED_FILTER_TAB).first.click()
        self.page.locator(self._FILTER_APPLY_ADVANCED).first.wait_for(state="visible", timeout=8_000)

    def _filter_badge(self, field_name):
        """Selector for the active-filter badge of the filter field named *field_name*.

        Always field-scoped: an instance-level default (e.g.
        LOCATION_LIST_DEFAULT_MAX_DEPTH) can add badges the test did not create, and
        an unscoped .first would then act on the wrong one.
        """
        return f"{self._FILTER_BADGE}[data-nb-field='{field_name}']"

    def remove_filter(self, field_name):
        """Click the X on *field_name*'s filter badge (Advanced tab).

        Removes that one filter field, with all its values, from the *pending* filter
        set; the list does not change until `apply_advanced_filters` commits it.
        Not to be confused with the Clear All button, which wipes every filter and
        commits immediately (navigating to `?all_filters_removed=true`).
        """
        self.page.locator(f"{self._filter_badge(field_name)} > {self._FILTER_BADGE_REMOVE}").first.click()

    def remove_filter_value(self, field_name):
        """Click the X on a single value inside *field_name*'s filter badge (Advanced tab).

        Removes one value from the *pending* filter set; the list does not change
        until `apply_advanced_filters` commits it.
        """
        self.page.locator(
            f"{self._filter_badge(field_name)} {self._FILTER_BADGE_VALUE_ITEM} {self._FILTER_BADGE_REMOVE}"
        ).first.click()

    def apply_advanced_filters(self):
        """Submit the drawer's advanced-tab filter form and wait for the reload."""
        self._click_and_wait_for_navigation(self._FILTER_APPLY_ADVANCED)

    def has_active_filter_indicator(self) -> bool:
        """Return True if the Filter button shows its active-filters indicator dot."""
        indicator = self.page.locator(self._FILTER_INDICATOR)
        return indicator.count() > 0 and indicator.first.is_visible()
