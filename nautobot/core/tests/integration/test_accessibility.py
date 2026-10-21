"""Accessibility regression tests. axe-core runs against the shared page templates and against every core list view.

`base_django.html`, `generic/object_list.html`, `generic/object_retrieve.html` and `generic/object_create_base.html`
render most of the UI, so a regression in shared markup fails these tests whichever model introduced it. That is true
of the shared markup only. Overridden blocks, self-rendering columns and per-template `extra_styles` are invisible to a
scan of one model, which is why `test_core_list_views` scans every core list view.
"""

from playwright.sync_api import expect
import pytest

from nautobot.core.tests.integration.pages.home_page import HomePage
from nautobot.core.tests.integration.pages.login_page import LoginPage
from nautobot.core.tests.integration.pages.search_results_page import SearchResultsPage
from nautobot.dcim.tests.integration.pages.location_create_page import LocationCreatePage
from nautobot.dcim.tests.integration.pages.location_detail_page import LocationDetailPage
from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage
from nautobot.playwright.accessibility import AccessibilityViolations, assert_no_accessibility_violations

# App list views are under this prefix (their routes are named `plugins:...`). The sweep covers core views only.
APPS_API_PREFIX = "/api/plugins/"

# Entries of the API root that are not model endpoints and have no object list behind them.
NON_MODEL_API_ROOTS = ("apps", "graphql", "status")

# Models whose UI list view is not at the API path with `/api` removed.
UI_LIST_PATHS = {"/users/tokens/": "/users/api-tokens/"}

# API endpoints of models that have no UI list view: through tables, component templates, assignment records, and
# records that are managed from another object's page. The Selenium test skipped these with `NoReverseMatch`.
# A model added without a list view goes here, so that a view whose path changed cannot be skipped by mistake.
NO_UI_LIST_VIEW = (
    "/cloud/cloud-network-prefix-assignments/",
    "/cloud/cloud-service-network-assignments/",
    "/dcim/cables-to-cable-terminations/",
    "/dcim/connected-device/",
    "/dcim/console-port-templates/",
    "/dcim/console-server-port-templates/",
    "/dcim/device-bay-templates/",
    "/dcim/device-cluster-assignments/",
    "/dcim/device-types-to-software-image-files/",
    "/dcim/front-port-templates/",
    "/dcim/interface-redundancy-group-associations/",
    "/dcim/interface-templates/",
    "/dcim/interface-vdc-assignments/",
    "/dcim/module-bay-templates/",
    "/dcim/power-outlet-templates/",
    "/dcim/power-port-templates/",
    "/dcim/rear-port-templates/",
    "/extras/condition-presets/",
    "/extras/contact-associations/",
    "/extras/content-types/",
    "/extras/custom-field-choices/",
    "/extras/dynamic-group-memberships/",
    "/extras/file-proxies/",
    "/extras/image-attachments/",
    "/extras/job-logs/",
    "/extras/job-queue-assignments/",
    "/extras/metadata-choices/",
    "/extras/secrets-groups-associations/",
    "/extras/user-saved-view-associations/",
    "/ipam/prefix-location-assignments/",
    "/ipam/vlan-location-assignments/",
    "/ipam/vrf-device-assignments/",
    "/ipam/vrf-prefix-assignments/",
    "/load-balancers/load-balancer-pool-member-certificate-profile-assignments/",
    "/load-balancers/virtual-server-certificate-profile-assignments/",
    "/users/config/",
    "/users/groups/",
    "/users/permissions/",
    "/users/users/",
    "/vpn/vpn-profile-phase-1-policy-assignments/",
    "/vpn/vpn-profile-phase-2-policy-assignments/",
    "/wireless/controller-managed-device-group-radio-profile-assignments/",
    "/wireless/controller-managed-device-group-wireless-network-assignments/",
)

# A sweep that finds fewer paths than this is scanning the wrong thing, whatever it reports.
MIN_CORE_LIST_VIEWS = 100


def core_list_view_paths(api):
    """Return the UI list path of every core model the REST API root lists, sorted.

    The suite cannot call `apps.get_models()` (it does not import Django), so the REST API root is used
    instead. `GET /api/` lists the apps, `GET /api/<app>/` lists each model's endpoint, and the UI list
    path is the API path without its `/api` prefix, or its entry in `UI_LIST_PATHS`. Endpoints in
    `NO_UI_LIST_VIEW` are left out.
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
            if not api_path or f"/{api_path}" in NO_UI_LIST_VIEW:
                continue
            paths.add(UI_LIST_PATHS.get(f"/{api_path}", f"/{api_path}"))
    return sorted(paths)


class AccessibilityTestCase:
    """Nautobot's shared pages have no axe-core violations."""

    def test_home_page(self, auth_page, base_url):
        """The home page, with its panel grid rendered, has no violations."""
        home = HomePage(auth_page, base_url)
        home.navigate()
        home.expect_loaded()
        assert_no_accessibility_violations(auth_page)

    @pytest.mark.slow
    def test_core_list_views(self, auth_page, base_url, api, axe_core_on_load):
        """Scan the markup that each core view adds to the shared template. This test is not a substitute for an App scanning its own views."""
        scanned = []
        failures = []
        for path in core_list_view_paths(api):
            # The tree views redirect to `?max_depth=`. `goto` returns the response after the redirect, so their
            # status here is 200, not 302. The load event `goto` waits for is where the server-rendered table is.
            status = auth_page.goto(path).status
            if status != 200:
                failures.append(
                    f"{path} returned {status}. If the model has no list view, add its endpoint to NO_UI_LIST_VIEW; "
                    "if the list view is at another path, add it to UI_LIST_PATHS."
                )
                continue
            scanned.append(path)
            try:
                assert_no_accessibility_violations(auth_page)
            except AccessibilityViolations as error:
                failures.append(str(error))

        # If the enumeration above breaks, this test would pass over a handful of paths.
        assert len(scanned) > MIN_CORE_LIST_VIEWS, (
            f"Expected more than {MIN_CORE_LIST_VIEWS} core list views, scanned {len(scanned)}"
        )
        assert not failures, f"{len(failures)} problem(s) across {len(scanned)} scanned list views:\n" + "\n".join(
            failures
        )

    def test_object_list_view(self, auth_page, base_url, created_location_tree):
        """An object list, with a row that has the tree caret and the descendants link, has no violations."""
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        expect(locations.object_table_wrapper()).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    def test_object_detail_view(self, auth_page, base_url, created_location_tree):
        """An object detail page has no violations."""
        detail = LocationDetailPage(auth_page, base_url)
        detail.navigate(created_location_tree["parent"]["id"])
        detail.expect_heading(created_location_tree["parent"]["name"])
        assert_no_accessibility_violations(auth_page)

    def test_object_edit_view(self, auth_page, base_url):
        """An object add form, before anything is entered, has no violations."""
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

    def test_search_page(self, auth_page, base_url, created_location_tree):
        """The global search results page, with at least one model's results in, has no violations."""
        results = SearchResultsPage(auth_page, base_url)
        results.navigate(created_location_tree["parent"]["name"])
        # The fixture guarantees a match in the location results, so that table is the one to wait for.
        results.expect_results_for("dcim.location")
        assert_no_accessibility_violations(auth_page)

    # storage_state=None leaves out the saved session login, so `page` starts logged out.
    @pytest.mark.browser_context_args(storage_state=None)
    def test_login_page(self, page, base_url):
        """The login page, seen logged out, has no violations."""
        login = LoginPage(page, base_url)
        login.navigate()
        login.expect_loaded()
        assert_no_accessibility_violations(page)

    def test_known_violation_is_reported(self, auth_page, base_url):
        """The failure message includes the rule id, which is what proves a green run scanned the page and found nothing."""
        home = HomePage(auth_page, base_url)
        home.navigate()
        home.expect_loaded()
        # An image with no `alt` attribute fails axe's `image-alt` rule.
        auth_page.evaluate(
            "document.body.insertAdjacentHTML('beforeend', '<img src=\"/static/img/nautobot_logo.svg\">')"
        )
        with pytest.raises(AccessibilityViolations, match="image-alt"):
            assert_no_accessibility_violations(auth_page)
