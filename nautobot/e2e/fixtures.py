"""Shared pytest fixture surface for Playwright E2E tests.

Registered once, via ``pytest_plugins`` in the repository-root ``conftest.py``. Per-app
``tests/e2e/conftest.py`` files build thin named fixtures on top of
:func:`create_object`; run ``pytest --fixtures nautobot/<app>/tests/e2e`` to list every
available fixture with its location.

The target instance is configured entirely by environment variables, so the same suite
runs against the hermetic CI instance or any deployed Nautobot:

- ``NAUTOBOT_E2E_URL`` (default ``http://localhost:8080``)
- ``NAUTOBOT_E2E_USERNAME`` / ``NAUTOBOT_E2E_PASSWORD`` (default ``admin`` / ``admin``)
- ``NAUTOBOT_E2E_API_TOKEN`` (default: the development-instance token)
"""

import os

import pytest

E2E_DEFAULT_URL = "http://localhost:8080"
# The defaults below match the documented development-instance bootstrap
# (createsuperuser admin/admin plus the well-known dev API token); they are
# never valid against a real deployment.
E2E_DEFAULT_USERNAME = "admin"
E2E_DEFAULT_PASSWORD = "admin"  # noqa: S105
E2E_DEFAULT_API_TOKEN = "0123456789abcdef0123456789abcdef01234567"  # noqa: S105


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """Root URL of the Nautobot instance under test.

    ``--base-url`` (pytest-base-url, bundled with pytest-playwright) wins if given;
    otherwise ``NAUTOBOT_E2E_URL``, defaulting to the local hermetic instance.
    """
    from_cli = pytestconfig.getoption("base_url", default=None)
    return (from_cli or os.getenv("NAUTOBOT_E2E_URL") or E2E_DEFAULT_URL).rstrip("/")


@pytest.fixture(scope="session")
def auth_state_path(browser, base_url, tmp_path_factory):
    """Log in through the UI once per session and return the saved storage-state file.

    Every browser context created afterwards (see :func:`browser_context_args`) starts
    from this state, so tests never repeat the login flow.
    """
    username = os.getenv("NAUTOBOT_E2E_USERNAME", E2E_DEFAULT_USERNAME)
    password = os.getenv("NAUTOBOT_E2E_PASSWORD", E2E_DEFAULT_PASSWORD)
    state_file = tmp_path_factory.mktemp("auth") / "session.json"
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    page.goto(f"{base_url}/login/")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_selector("nav", timeout=15_000)
    context.storage_state(path=str(state_file))
    context.close()
    return state_file


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url, auth_state_path):
    """Inject the session login state and base URL into every browser context.

    pytest-playwright's standard ``page`` fixture then starts authenticated, and CLI
    flags such as ``--headed``, ``--slowmo``, ``--screenshot``, and ``--tracing`` keep
    working with no extra wiring.
    """
    return {**browser_context_args, "base_url": base_url, "storage_state": str(auth_state_path)}


@pytest.fixture
def auth_page(page):
    """An authenticated Playwright page (the standard ``page`` fixture, logged in)."""
    return page


@pytest.fixture(scope="session")
def api(playwright, base_url):
    """Token-authenticated ``APIRequestContext`` against the instance under test.

    The REST ground truth for behavioral assertions and the transport for test-data
    setup. Keeping data setup on the REST API (rather than the ORM) keeps the suite
    black-box: it needs a URL and a token, not a database connection.
    """
    token = os.getenv("NAUTOBOT_E2E_API_TOKEN", E2E_DEFAULT_API_TOKEN)
    context = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    )
    yield context
    context.dispose()


@pytest.fixture(scope="session")
def status_id_for(api):
    """Callable returning the id of a valid Status for a content type (e.g. ``dcim.location``).

    Nearly every ``created_*`` fixture needs a status; results are cached per content
    type for the session.
    """
    cache = {}

    def _lookup(content_type):
        if content_type not in cache:
            response = api.get("/api/extras/statuses/", params={"content_types": content_type, "limit": 1})
            assert response.ok, f"Status lookup for {content_type} returned {response.status}: {response.text()}"
            results = response.json()["results"]
            assert results, f"No status exists for content type {content_type}"
            cache[content_type] = results[0]["id"]
        return cache[content_type]

    return _lookup


@pytest.fixture
def create_object(api):
    """Parameterized factory: create a REST object owned by this test, deleted on teardown.

    The single factory behind every per-app ``created_*`` fixture::

        parent = create_object("dcim/locations", name=name, location_type=lt["id"], status=status_id)

    Objects are deleted in reverse creation order at teardown; deletes that return an
    error (e.g. a child already removed by a parent cascade) are ignored.
    """
    created = []

    def _create(endpoint, **fields):
        response = api.post(f"/api/{endpoint}/", data=fields)
        assert response.ok, f"POST /api/{endpoint}/ returned {response.status}: {response.text()}"
        record = response.json()
        created.append((endpoint, record["id"]))
        return record

    yield _create

    for endpoint, pk in reversed(created):
        api.delete(f"/api/{endpoint}/{pk}/")


@pytest.fixture(scope="session")
def api_count(api):
    """Callable returning the API object count for an endpoint and filter params.

    The ground truth for list-view assertions: page-level row checks alone would miss
    records leaking onto later pages, so filter tests compare the visible row count
    against ``api_count("dcim/locations", parent=parent_id)``.
    """

    def _count(endpoint, **params):
        response = api.get(f"/api/{endpoint}/", params={**params, "limit": 1})
        assert response.ok, f"GET /api/{endpoint}/ returned {response.status}: {response.text()}"
        return response.json()["count"]

    return _count
