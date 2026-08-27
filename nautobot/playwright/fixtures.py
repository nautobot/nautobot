"""Shared pytest fixture surface for the Playwright test suite.

Registered once, via `pytest_plugins` in the repository-root `conftest.py`. Per-app
`tests/integration/conftest.py` files build thin named fixtures on top of
`create_object`; run `pytest --fixtures nautobot/<app>/tests/integration` to list every
available fixture with its location.

The target instance is configured entirely by environment variables, so the same suite
runs against any Nautobot it can reach over HTTP. The defaults match the
development-style bootstrap that both local runs and the CI job use: an instance at
`http://localhost:8080` with the `admin`/`admin` superuser and the well-known
development API token.

- `NAUTOBOT_PLAYWRIGHT_URL`
- `NAUTOBOT_PLAYWRIGHT_USERNAME` / `NAUTOBOT_PLAYWRIGHT_PASSWORD`
- `NAUTOBOT_PLAYWRIGHT_API_TOKEN`

Black-box refers to the instance under test, not the test host: collection imports the
`nautobot` package (this module registers as a pytest plugin), so the host still
needs the repo installed (`poetry install --with playwright`).
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import os
from uuid import uuid4

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pytest

PLAYWRIGHT_DEFAULT_URL = "http://localhost:8080"
# The defaults below match the documented development-instance bootstrap
# (createsuperuser admin/admin plus the well-known dev API token); they are
# never valid against a real deployment.
PLAYWRIGHT_DEFAULT_USERNAME = "admin"
PLAYWRIGHT_DEFAULT_PASSWORD = "admin"  # noqa: S105
PLAYWRIGHT_DEFAULT_API_TOKEN = "0123456789abcdef0123456789abcdef01234567"  # noqa: S105


def unique_name(prefix="ZZZ-test"):
    """Return a unique, sortable name for a test-owned record.

    The prefix sorts owned records last, so they never perturb first-page row counts
    taken before a test filters for them; the hex suffix keeps parallel runs and
    repeated runs against a shared instance from colliding.
    """
    return f"{prefix}-{uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """Root URL of the Nautobot instance under test.

    Deliberately shadows pytest-base-url's fixture of the same name so pytest-playwright
    picks up our resolution order: `--base-url` (pytest-base-url, bundled with
    pytest-playwright) wins if given; otherwise `NAUTOBOT_PLAYWRIGHT_URL`, defaulting to the
    local development-style instance.
    """
    from_cli = pytestconfig.getoption("base_url", default=None)
    return (from_cli or os.getenv("NAUTOBOT_PLAYWRIGHT_URL") or PLAYWRIGHT_DEFAULT_URL).rstrip("/")


@pytest.fixture(scope="session")
def auth_state_path(browser, base_url, tmp_path_factory):
    """Log in through the UI once per session and return the saved storage-state file.

    Every browser context created afterwards (see `browser_context_args`) starts
    from this state, so tests never repeat the login flow.
    """
    username = os.getenv("NAUTOBOT_PLAYWRIGHT_USERNAME", PLAYWRIGHT_DEFAULT_USERNAME)
    password = os.getenv("NAUTOBOT_PLAYWRIGHT_PASSWORD", PLAYWRIGHT_DEFAULT_PASSWORD)
    state_file = tmp_path_factory.mktemp("auth") / "session.json"
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    page.goto(f"{base_url}/login/")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    try:
        # The logout link is the auth-positive signal: it is always in the DOM once a
        # session exists, but hidden inside a collapsed dropdown (hence "attached").
        # Generic chrome like <nav> also renders on the login page, so it can't be
        # trusted to mean "logged in".
        page.wait_for_selector("a[href='/logout/']", state="attached", timeout=15_000)
    except PlaywrightTimeoutError:
        pytest.fail(
            f"Playwright login failed as {username!r} against {base_url} (still on {page.url}). "
            "Check NAUTOBOT_PLAYWRIGHT_USERNAME/NAUTOBOT_PLAYWRIGHT_PASSWORD and that the instance is up."
        )
    context.storage_state(path=str(state_file))
    context.close()
    return state_file


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url, auth_state_path):
    """Inject the session login state and base URL into every browser context.

    pytest-playwright's standard `page` fixture then starts authenticated, and CLI
    flags such as `--headed`, `--slowmo`, `--screenshot`, and `--tracing` keep
    working with no extra wiring.
    """
    return {**browser_context_args, "base_url": base_url, "storage_state": str(auth_state_path)}


@pytest.fixture
def auth_page(page):
    """pytest-playwright's standard `page` fixture, under a name that marks intent.

    Authentication comes from `browser_context_args`, which starts every context
    from the session login state; this alias adds no check of its own. It exists so
    a test signature signals "this test assumes a logged-in session" to the reader.
    """
    return page


@pytest.fixture(scope="session")
def api(playwright, base_url):
    """Token-authenticated `APIRequestContext` against the instance under test.

    The REST ground truth for behavioral assertions and the transport for test-data
    setup. Keeping data setup on the REST API (rather than the ORM) keeps the suite
    black-box: it needs a URL and a token, not a database connection.
    """
    token = os.getenv("NAUTOBOT_PLAYWRIGHT_API_TOKEN", PLAYWRIGHT_DEFAULT_API_TOKEN)
    context = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    )
    yield context
    context.dispose()


@pytest.fixture(scope="session")
def status_id_for(api):
    """Callable returning the id of a valid Status for a content type (e.g. `dcim.location`).

    Nearly every `created_*` fixture needs a status; results are cached per content
    type for the session.
    """
    cache = {}

    def _lookup(content_type):
        if content_type not in cache:
            response = api.get("/api/extras/statuses/", params={"content_types": content_type, "limit": 1})
            if not response.ok:
                pytest.fail(f"Status lookup for {content_type} returned {response.status}: {response.text()}")
            results = response.json()["results"]
            if not results:
                pytest.fail(f"No status exists for content type {content_type}")
            cache[content_type] = results[0]["id"]
        return cache[content_type]

    return _lookup


@pytest.fixture
def create_object(api):
    """Parameterized factory: create a REST object owned by this test, deleted on teardown.

    The single factory behind every per-app `created_*` fixture:

        parent = create_object("dcim/locations", name=name, location_type=lt["id"], status=status_id)

    Objects are deleted in reverse creation order at teardown. A 404 is expected and
    ignored, since a child may already have been removed by a parent's cascade delete.
    Any other failing status is collected and reported once every delete has been
    attempted, so a server error during cleanup is visible without leaking the records
    that had not been deleted yet.
    """
    created = []

    def _create(endpoint, **fields):
        response = api.post(f"/api/{endpoint}/", data=fields)
        if not response.ok:
            pytest.fail(f"POST /api/{endpoint}/ returned {response.status}: {response.text()}")
        record = response.json()
        created.append((endpoint, record["id"]))
        return record

    yield _create

    failures = []
    for endpoint, pk in reversed(created):
        response = api.delete(f"/api/{endpoint}/{pk}/")
        if not response.ok and response.status != 404:
            failures.append(f"DELETE /api/{endpoint}/{pk}/ returned {response.status}: {response.text()[:200]}")
    if failures:
        pytest.fail("Test data teardown failed:\n" + "\n".join(failures))


@pytest.fixture(scope="session")
def api_count(api):
    """Callable returning the API object count for an endpoint and filter params.

    Gives filter tests an expected count from outside the UI: checking visible rows
    proves the rows shown match the filter, not that every matching record was shown.
    Valid only while the expected results fit on one page — keep owned test data
    small enough to guarantee that.
    """

    def _count(endpoint, **params):
        response = api.get(f"/api/{endpoint}/", params={**params, "limit": 1})
        if not response.ok:
            pytest.fail(f"GET /api/{endpoint}/ returned {response.status}: {response.text()}")
        return response.json()["count"]

    return _count
