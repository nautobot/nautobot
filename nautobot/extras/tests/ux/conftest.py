# pylint: skip-file
# The development container does not install Playwright and pytest, so pylint cannot import these modules.
"""Shared fixtures for the Playwright UX tests.

These tests run against a live development instance. All settings come from environment variables:

- APP_URL: the base URL of the application, for example http://localhost:8080
- APP_USER, APP_PASSWORD: the credentials of a superuser in the development environment
- AXE_SCRIPT: the path of axe.min.js; if it is not set, the accessibility check is skipped
- ARTIFACTS_DIR: the folder for the screenshots and the accessibility results
- APP_HOST_RESOLVER_RULES: optional Chromium host resolver rules, for example
  "MAP localhost host.docker.internal", when the application only accepts the host name "localhost"
"""

import json
import os
from pathlib import Path
import secrets

from playwright.sync_api import expect, Page, sync_playwright
import pytest

APP_URL = os.environ.get("APP_URL", "http://localhost:8080").rstrip("/")
APP_USER = os.environ.get("APP_USER", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
AXE_SCRIPT = os.environ.get("AXE_SCRIPT", "")
ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", "ux-artifacts"))
HOST_RESOLVER_RULES = os.environ.get("APP_HOST_RESOLVER_RULES", "")

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]


@pytest.fixture(scope="session")
def browser():
    args = [f"--host-resolver-rules={HOST_RESOLVER_RULES}"] if HOST_RESOLVER_RULES else []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=args)
        yield browser
        browser.close()


class PageErrors:
    """Collect browser console errors and server errors (HTTP 5xx) of a page."""

    def __init__(self, page: Page):
        self.messages = []
        page.on("console", self._on_console)
        page.on("pageerror", lambda exc: self.messages.append(f"page error: {exc}"))
        page.on("response", self._on_response)

    def _on_console(self, message):
        if message.type == "error":
            self.messages.append(f"console error: {message.text}")

    def _on_response(self, response):
        if response.status >= 500:
            self.messages.append(f"server error: HTTP {response.status} {response.url}")

    def check(self):
        if self.messages:
            pytest.fail("Errors on the page:\n" + "\n".join(self.messages))


@pytest.fixture
def new_page(browser):
    """Return a factory that opens a new browser context and page, and records its errors."""
    contexts = []

    def _new_page():
        context = browser.new_context(bypass_csp=True, viewport={"width": 1440, "height": 900})
        contexts.append(context)
        # Keep the Django Debug Toolbar of the development environment closed, so that it does not hide the page.
        context.add_init_script(
            "document.addEventListener('DOMContentLoaded', () => {"
            " const style = document.createElement('style');"
            " style.textContent = '#djDebugRoot, #djDebug { display: none !important; }';"
            " document.head.appendChild(style); });"
        )
        page = context.new_page()
        page.errors = PageErrors(page)
        return page

    yield _new_page
    for context in contexts:
        context.close()


def login(page: Page, username: str, password: str):
    page.goto(f"{APP_URL}/login/")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    expect(page).not_to_have_url(f"{APP_URL}/login/")


def open_nav_item(page: Page, section: str, item: str):
    """Open a page through the side navigation menu, as a user does."""
    page.locator(f"li[data-section-name='{section}'] > button.nb-sidenav-list-item").click()
    page.locator(f"li[data-section-name='{section}'] a.nb-sidenav-link", has_text=item).first.click()
    page.wait_for_load_state("networkidle")


FOCUS_INDICATOR_JS = """(el) => {
    const style = getComputedStyle(el);
    return style.outlineStyle !== "none" || /rgb\\(/.test(style.boxShadow);
}"""


def wait_for_focus_indicator(page: Page, locator):
    """Wait until the focused element shows an outline or a box shadow. The theme animates the focus ring."""
    page.wait_for_function(FOCUS_INDICATOR_JS, arg=locator.element_handle(), timeout=5000)


def screenshot(page: Page, name: str, locator=None, full_page=True):
    path = ARTIFACTS_DIR / "screenshots" / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if locator is not None:
        locator.screenshot(path=str(path))
    else:
        page.screenshot(path=str(path), full_page=full_page)
    return path


def check_accessibility(page: Page, name: str):
    """Run axe-core on the page and save the violations. Return the violations."""
    if not AXE_SCRIPT:
        return []
    page.add_script_tag(path=AXE_SCRIPT)
    result = page.evaluate(f"axe.run(document, {{runOnly: {json.dumps(AXE_TAGS)}}})")
    path = ARTIFACTS_DIR / "a11y" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result["violations"], indent=2))
    return result["violations"]


def api_request(page: Page, method: str, path: str, data=None):
    """Send a REST API request from the browser, with the session of the logged-in user."""
    return page.evaluate(
        """async ([method, url, data]) => {
            const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
            const response = await fetch(url, {
                method: method,
                headers: {"Content-Type": "application/json", "Accept": "application/json", "X-CSRFToken": csrf},
                body: data === null ? undefined : JSON.stringify(data),
            });
            const text = await response.text();
            return {status: response.status, body: text ? JSON.parse(text) : null};
        }""",
        [method, f"{APP_URL}{path}", data],
    )


@pytest.fixture
def view_only_user(new_page):
    """Create a user that can only view Jobs. Delete the user and its permission after the test."""
    admin_page = new_page()
    login(admin_page, APP_USER, APP_PASSWORD)
    username = "ux-job-viewer"
    password = secrets.token_urlsafe(24)

    existing = api_request(admin_page, "GET", f"/api/users/users/?username={username}")
    for user in existing["body"]["results"]:
        api_request(admin_page, "DELETE", f"/api/users/users/{user['id']}/")
    existing = api_request(admin_page, "GET", f"/api/users/permissions/?name={username}")
    for permission in existing["body"]["results"]:
        api_request(admin_page, "DELETE", f"/api/users/permissions/{permission['id']}/")

    user = api_request(admin_page, "POST", "/api/users/users/", {"username": username, "password": password})
    if user["status"] != 201:
        pytest.fail(f"Cannot create the view-only user: {user}")
    permission = api_request(
        admin_page,
        "POST",
        "/api/users/permissions/",
        {
            "name": username,
            "enabled": True,
            "object_types": ["extras.job"],
            "actions": ["view"],
            "users": [user["body"]["id"]],
        },
    )
    if permission["status"] != 201:
        pytest.fail(f"Cannot create the view permission: {permission}")

    yield username, password

    api_request(admin_page, "DELETE", f"/api/users/permissions/{permission['body']['id']}/")
    api_request(admin_page, "DELETE", f"/api/users/users/{user['body']['id']}/")
