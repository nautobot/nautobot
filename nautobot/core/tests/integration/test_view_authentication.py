"""Authentication enforcement on the UI and the REST API.

Playwright port of ``nautobot/core/tests/selenium/test_view_authentication.py::AuthenticationEnforcedTestCase.test_all_views_require_authentication``.

The Selenium original walked every registered URL pattern with the Django test
client. That sweep is URL-pattern coverage: it belongs in the unittest suite, needs
the ORM to enumerate the patterns, and is far too slow to drive through a browser.
The browser port checks the same guarantee against a fixed representative sample
instead, one protected surface of each kind.
"""

from playwright.sync_api import expect
import pytest

from nautobot.playwright.fixtures import DISABLE_DEBUG_TOOLBAR_HEADERS

# One representative of each kind of protected UI surface. Each redirects an
# anonymous request to the login page, carrying the requested path in `next`.
PROTECTED_UI_VIEWS = (
    "/",  # home
    "/dcim/devices/",  # a list view
    # A detail view. The UUID deliberately matches no object: authentication is
    # enforced before the object is looked up, so the redirect is the same either
    # way and the test needs no data of its own.
    "/dcim/devices/00000000-0000-0000-0000-000000000000/",
)

# The REST API root. DRF rejects an unauthenticated request outright rather than
# redirecting a browser to the login page, so it is asserted separately below.
API_ROOT = "/api/"


class AuthenticationEnforcedTestCase:
    """Protected views are not served to an anonymous browser.

    The representative sample: ``/`` (home), ``/dcim/devices/`` (a list view),
    ``/dcim/devices/<uuid>/`` (a detail view), and ``/api/`` (the REST API root).

    Each test opens a context of its own with no stored session, rather than using
    the shared `auth_page`, so the requests really do arrive unauthenticated.
    """

    @pytest.mark.behavioral
    @pytest.mark.parametrize("path", PROTECTED_UI_VIEWS)
    def test_ui_view_redirects_anonymous_request_to_login(self, browser, base_url, path):
        """An anonymous request to a protected UI view lands on ``/login/?next=<path>``."""
        with browser.new_context(extra_http_headers=DISABLE_DEBUG_TOOLBAR_HEADERS) as context:
            page = context.new_page()
            page.goto(f"{base_url}{path}")
            expect(page).to_have_url(f"{base_url}/login/?next={path}")

    @pytest.mark.behavioral
    def test_api_root_refuses_anonymous_request(self, browser, base_url):
        """The REST API root refuses an anonymous request instead of serving it."""
        with browser.new_context(extra_http_headers=DISABLE_DEBUG_TOOLBAR_HEADERS) as context:
            page = context.new_page()
            response = page.goto(f"{base_url}{API_ROOT}")
            assert response.status == 403, f"Expected 403 from an anonymous {API_ROOT} request, got {response.status}"
            expect(page).to_have_url(f"{base_url}{API_ROOT}")
