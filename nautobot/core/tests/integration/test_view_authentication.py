"""Anonymous requests to protected views are sent to the login page or refused."""

from playwright.sync_api import expect
import pytest

PROTECTED_UI_VIEWS = (
    "/",
    "/dcim/devices/",
    # The UUID deliberately matches no object: authentication is enforced before the
    # object is looked up, so the redirect is the same either way and the test needs
    # no data of its own.
    "/dcim/devices/00000000-0000-0000-0000-000000000000/",
)

# DRF refuses an unauthenticated request to the API root outright rather than
# redirecting a browser to the login page, so it is asserted separately below.
API_ROOT = "/api/"


# storage_state=None drops the session login, so page arrives logged out.
@pytest.mark.browser_context_args(storage_state=None)
class AuthenticationEnforcedTestCase:
    """A chosen sample of protected views (home, a list, a detail, the API root) is refused to an anonymous browser."""

    @pytest.mark.parametrize("path", PROTECTED_UI_VIEWS)
    def test_ui_view_redirects_anonymous_request_to_login(self, page, base_url, path):
        """An anonymous request to a protected UI view lands on `/login/?next=<path>`."""
        page.goto(path)
        expect(page).to_have_url(f"{base_url}/login/?next={path}")

    def test_api_root_refuses_anonymous_request(self, page, base_url):
        """The REST API root refuses an anonymous request instead of serving it."""
        response = page.goto(API_ROOT)
        assert response.status == 403, f"Expected 403 from an anonymous {API_ROOT} request, got {response.status}"
        expect(page).to_have_url(f"{base_url}{API_ROOT}")
