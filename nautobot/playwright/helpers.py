"""Plain helper functions for the Playwright test suite.

Ordinary functions, imported normally. Fixtures (anything pytest constructs
per test, with dependencies or teardown) live in `fixtures.py`.
"""

from uuid import uuid4

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def unique_name(prefix="ZZZ-test"):
    """Return a unique, sortable name for a test-owned record.

    The prefix sorts owned records last; the hex suffix keeps parallel runs and
    repeated runs against a shared instance from colliding.
    """
    return f"{prefix}-{uuid4().hex[:8]}"


def log_in(page, username, password):
    """Log in through the UI and wait for the logged-in state.

    A plain function so scripts outside pytest can call it. Navigates to the relative
    path `/login/`, so the page's context must be created with `base_url`.
    """
    page.goto("/login/")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    try:
        # The logout link only exists once a session does. It sits in a collapsed
        # dropdown, so wait for "attached" rather than visible.
        page.wait_for_selector("a[href='/logout/']", state="attached", timeout=15_000)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(f"Login as {username!r} did not reach a logged-in session (still on {page.url}).") from exc
