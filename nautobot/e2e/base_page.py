"""Base page object for Playwright E2E tests.

Every page object extends `BasePage`. Selectors live in page objects, never in
test files, so a markup change is a one-file fix; test bodies read as user intent
(`locations.filter_by_parent(name)`) rather than selector plumbing.
"""

from playwright.sync_api import Page


def select2_filter_pick(page, field_name, search="", pick_text=None, exact=True):
    """Type-and-pick in an API-backed Select2 filter field, addressed by field *name*.

    Filter fields use the `nautobot-select2-api` pattern: the widget renders an
    anonymous `<span class="select2-container">` adjacent to the hidden `<select>`
    (there is no `#select2-<id>-container` element to click, unlike create/edit
    forms). Options load via AJAX from the REST API, so `select_option()` cannot see
    them; the reliable gesture is click the container, type into the open dropdown's
    search field, then click the matching result.

    Args:
        page (Page): The Playwright page.
        field_name (str): The `name` attribute of the underlying `<select>`.
        search (str): Text typed into the dropdown's search box to narrow the options.
        pick_text (str): Visible text of the option to click; first option if None.
        exact (bool): Exact text match for *pick_text*. Pass False for fields whose
            options render an ancestry path (e.g. locations: "Parent → Child"), where
            an exact match on the bare name would never hit.
    """
    page.locator(f"select[name='{field_name}'] + span.select2-container").first.click()
    # Scope to the open dropdown: list views keep every filter field's Select2 search
    # input in the DOM simultaneously, so an unscoped .first picks the wrong field.
    search_input = page.locator(".select2-container--open .select2-search__field").first
    search_input.wait_for(state="visible", timeout=8_000)
    search_input.fill(search)
    if pick_text is not None:
        # Wait for the target text itself, not just any option: AJAX-backed results
        # flicker (Searching → empty → populated) and a generic wait can resolve
        # during the empty window.
        option = page.locator(".select2-dropdown").get_by_text(pick_text, exact=exact).first
    else:
        option = page.locator(".select2-results__option:not(:has-text('Searching'))").first
    option.wait_for(state="visible", timeout=10_000)
    option.click()


class BasePage:
    """Shared low-level behavior for all page objects."""

    # htmx adds the htmx-request class to the requesting element (or its
    # hx-indicator target) while a fragment request is in flight; it is the only
    # in-page loading indicator core renders.
    _LOADING_INDICATOR = ".htmx-request"

    def __init__(self, page: Page, base_url: str):
        """Bind the page object to a Playwright *page* and the instance *base_url*."""
        self.page = page
        self.base_url = base_url.rstrip("/")

    def _goto(self, path):
        """Navigate to `base_url + path` and wait for the page to settle."""
        self.page.goto(f"{self.base_url}{path}")
        self.wait_for_load()

    def wait_for_load(self, timeout=30_000):
        """Wait for the load event and for any loading overlay to disappear.

        Uses "load" rather than "networkidle": Nautobot is server-rendered, so the DOM
        is complete at load, and pages with polling or open Select2 AJAX connections
        never reach networkidle at all.
        """
        self.page.wait_for_load_state("load", timeout=timeout)
        # state="hidden" is satisfied by an indicator that finishes and detaches (or
        # never existed), so no exception handling is needed for the happy paths. An
        # indicator still visible at the timeout is a genuinely stuck page and the
        # TimeoutError should propagate rather than surface later as a confusing
        # assertion failure.
        indicator = self.page.locator(self._LOADING_INDICATOR)
        if indicator.count() > 0:
            indicator.first.wait_for(state="hidden", timeout=timeout)

    def current_url(self) -> str:
        """Return the browser's current URL."""
        return self.page.url

    def go_back(self):
        """Navigate browser history back one step and wait for the page to settle."""
        self.page.go_back()
        self.wait_for_load()
