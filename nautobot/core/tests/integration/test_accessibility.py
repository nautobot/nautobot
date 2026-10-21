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

from nautobot.playwright.axe import AccessibilityViolations, assert_no_accessibility_violations

# Every list view that `generic/object_list.html` renders wraps its table in this form.
OBJECT_LIST_FORM = "#object_list_form"

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

    def test_home_page(self, auth_page):
        auth_page.goto("/")
        expect(auth_page.locator("#draggable-homepage-panels")).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    @pytest.mark.slow
    def test_core_list_views(self, auth_page, api, axe_core_on_load):
        """Scan the markup that each core view adds to the shared template. Not a substitute for an App scanning its own views."""
        scanned = []
        not_list_views = []
        failures = []
        for path in core_list_view_paths(api):
            # `goto` follows the redirect that the tree views add (`?max_depth=`), so the status checked here is the final one.
            response = auth_page.goto(path)
            if response.status != 200:
                continue
            # The list form is in the first response, so no wait is needed. A 200 page without it is not an
            # object list (an endpoint whose UI page is something else) and is not what this test covers.
            if auth_page.locator(OBJECT_LIST_FORM).count() == 0:
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
            f"Pages without {OBJECT_LIST_FORM}: {not_list_views}"
        )
        assert not failures, f"{len(failures)} of {len(scanned)} list views have violations:\n" + "\n".join(failures)

    def test_object_list_view(self, auth_page, created_location_with_child):
        auth_page.goto("/dcim/locations/")
        expect(auth_page.locator(OBJECT_LIST_FORM)).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    def test_object_detail_view(self, auth_page, created_location_with_child):
        auth_page.goto(f"/dcim/locations/{created_location_with_child['id']}/")
        expect(auth_page.locator("#page-title")).to_contain_text(created_location_with_child["name"])
        assert_no_accessibility_violations(auth_page)

    def test_object_edit_view(self, auth_page):
        auth_page.goto("/dcim/locations/add/")
        expect(auth_page.locator("button[name='_create']")).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    def test_object_edit_view_with_validation_errors(self, auth_page):
        """Scan the error state, where each invalid field needs `aria-invalid` and an `aria-describedby` for its error list.

        The `required` attributes are removed so that the browser submits the form and the server rejects it.
        """
        auth_page.goto("/dcim/locations/add/")
        expect(auth_page.locator("button[name='_create']")).to_be_attached()
        auth_page.evaluate(
            "document.querySelectorAll('[required]').forEach((element) => element.removeAttribute('required'))"
        )
        auth_page.click("button[name='_create']")
        expect(auth_page.locator("[aria-invalid='true']").first).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    def test_search_page(self, auth_page, created_location_with_child):
        auth_page.goto(f"/search/?q={created_location_with_child['name']}")
        # The results arrive one model at a time over HTMX. The fixture guarantees a match in the location table, so
        # that table is the one to wait for.
        expect(auth_page.locator("#dcimlocation-results-table table")).to_be_attached()
        assert_no_accessibility_violations(auth_page)

    # storage_state=None leaves out the saved session login, so `page` starts logged out.
    @pytest.mark.browser_context_args(storage_state=None)
    def test_login_page(self, page):
        page.goto("/login/")
        expect(page.locator("input[name='username']")).to_be_attached()
        assert_no_accessibility_violations(page)

    def test_known_violation_is_reported(self, auth_page):
        """The failure message includes the rule id, which is what proves a green run scanned the page and found nothing."""
        auth_page.goto("/")
        expect(auth_page.locator("#draggable-homepage-panels")).to_be_attached()
        auth_page.evaluate(
            "document.body.insertAdjacentHTML('beforeend', '<img src=\"/static/img/nautobot_logo.svg\">')"
        )
        with pytest.raises(AccessibilityViolations, match="image-alt"):
            assert_no_accessibility_violations(auth_page)
