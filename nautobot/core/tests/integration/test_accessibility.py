"""Accessibility regression tests: axe-core against representative pages rather than every view.

`base_django.html`, `generic/object_list.html`, `generic/object_retrieve.html` and `generic/object_create_base.html`
render most of the UI, so a regression in shared markup fails these tests whichever model introduced it. That is true
of the shared markup only. Overridden blocks, self-rendering columns and per-template `extra_styles` are invisible to a
scan of one model, which is why `test_core_list_views` scans every core list view.

Each test waits for an element that the view itself renders before scanning. Nautobot's error pages have the same `main`
as every other page, so a wait on `main` would let a failed view be scanned as its error page.
"""

from playwright.sync_api import expect
import pytest

from nautobot.core.tests.integration.pages.any_list_page import AnyListPage
from nautobot.core.tests.integration.pages.home_page import HomePage
from nautobot.core.tests.integration.pages.login_page import LoginPage
from nautobot.core.tests.integration.pages.search_results_page import SearchResultsPage
from nautobot.dcim.tests.integration.pages.location_create_page import LocationCreatePage
from nautobot.dcim.tests.integration.pages.location_detail_page import LocationDetailPage
from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage
from nautobot.playwright.axe import AccessibilityViolations, assert_no_accessibility_violations

# App list views are under this prefix (their routes are named `plugins:...`). The sweep covers core views only.
APPS_API_PREFIX = "/api/plugins/"

# Entries of the API root that are not model endpoints and have no object list behind them.
NON_MODEL_API_ROOTS = ("apps", "graphql", "status")

# A sweep that finds fewer paths than this is scanning the wrong thing, whatever it reports.
MIN_CORE_LIST_VIEWS = 100


def core_list_view_paths(api):
    """Return the UI list path of every core model the REST API root lists, sorted.

    The suite cannot call `apps.get_models()` (it does not import Django), so the REST API root is used
    instead. `GET /api/` lists the apps, `GET /api/<app>/` lists each model's endpoint, and the UI list
    path is the API path without its `/api` prefix. Models without a list view (through tables,
    component templates) return 404 in the UI, and the caller skips them.
    """
    paths = set()
    for app_name, app_url in api.get("/api/").json().items():
        if app_name in NON_MODEL_API_ROOTS or not isinstance(app_url, str) or APPS_API_PREFIX in app_url:
            continue
        app_response = api.get(app_url)
        if not app_response.ok:
            continue
        for endpoint_url in app_response.json().values():
            if not isinstance(endpoint_url, str):
                continue
            _, _, api_path = endpoint_url.partition("/api/")
            if api_path:
                paths.add(f"/{api_path}")
    return sorted(paths)


class AccessibilityTestCase:
    """Nautobot's shared pages have no axe-core violations."""

    def test_home_page(self, auth_page, base_url):
        home = HomePage(auth_page, base_url)
        home.navigate()
        home.expect_loaded()
        assert_no_accessibility_violations(auth_page)

    @pytest.mark.slow
    def test_core_list_views(self, auth_page, base_url, api, axe_core_on_load):
        """Scan the markup that each core view adds to the shared template. Not a substitute for an App scanning its own views."""
        lists = AnyListPage(auth_page, base_url)
        scanned = []
        not_list_views = []
        failures = []
        for path in core_list_view_paths(api):
            # The tree views redirect to `?max_depth=`. `navigate_to` returns the response after the redirect,
            # so their status here is 200, not 302.
            if lists.navigate_to(path).status != 200:
                continue
            # The list form is in the first response, so no wait is needed. A 200 page without it is not an
            # object list (an endpoint whose UI page is something else) and is not what this test covers.
            if lists.object_list_form().count() == 0:
                not_list_views.append(path)
                continue
            scanned.append(path)
            try:
                assert_no_accessibility_violations(auth_page)
            except AccessibilityViolations as error:
                failures.append(str(error))

        # If the enumeration above breaks, this test would pass over a handful of paths.
        assert len(scanned) > MIN_CORE_LIST_VIEWS, (
            f"Expected more than {MIN_CORE_LIST_VIEWS} core list views, scanned {len(scanned)}. "
            f"Pages without an object list form: {not_list_views}"
        )
        assert not failures, f"{len(failures)} of {len(scanned)} list views have violations:\n" + "\n".join(failures)

    def test_object_list_view(self, auth_page, base_url, created_location_with_child):
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        expect(locations.object_list_form()).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    def test_object_detail_view(self, auth_page, base_url, created_location_with_child):
        detail = LocationDetailPage(auth_page, base_url)
        detail.navigate(created_location_with_child["id"])
        detail.expect_heading(created_location_with_child["name"])
        assert_no_accessibility_violations(auth_page)

    def test_object_edit_view(self, auth_page, base_url):
        LocationCreatePage(auth_page, base_url).navigate()
        assert_no_accessibility_violations(auth_page)

    def test_object_edit_view_with_validation_errors(self, auth_page, base_url):
        """Scan the error state, where each invalid field needs `aria-invalid` and an `aria-describedby` for its error list."""
        form = LocationCreatePage(auth_page, base_url)
        form.navigate()
        form.remove_required_attributes()
        form.submit()
        form.expect_validation_errors()
        assert_no_accessibility_violations(auth_page)

    def test_search_page(self, auth_page, base_url, created_location_with_child):
        results = SearchResultsPage(auth_page, base_url)
        results.navigate(created_location_with_child["name"])
        # The fixture guarantees a match in the location results, so that table is the one to wait for.
        results.expect_results_for("dcim.location")
        assert_no_accessibility_violations(auth_page)

    # storage_state=None leaves out the saved session login, so `page` starts logged out.
    @pytest.mark.browser_context_args(storage_state=None)
    def test_login_page(self, page, base_url):
        login = LoginPage(page, base_url)
        login.navigate()
        login.expect_loaded()
        assert_no_accessibility_violations(page)

    def test_known_violation_is_reported(self, auth_page, base_url):
        """The failure message includes the rule id, which is what proves a green run scanned the page and found nothing."""
        home = HomePage(auth_page, base_url)
        home.navigate()
        home.expect_loaded()
        auth_page.evaluate(
            "document.body.insertAdjacentHTML('beforeend', '<img src=\"/static/img/nautobot_logo.svg\">')"
        )
        with pytest.raises(AccessibilityViolations, match="image-alt"):
            assert_no_accessibility_violations(auth_page)
