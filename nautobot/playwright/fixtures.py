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
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import os

import pytest

from nautobot.playwright.helpers import log_in, LoginError, unique_name

PLAYWRIGHT_DEFAULT_URL = "http://localhost:8080"
# The defaults below match the documented development-instance bootstrap
# (createsuperuser admin/admin plus the well-known dev API token); they are
# never valid against a real deployment.
PLAYWRIGHT_DEFAULT_USERNAME = "admin"
PLAYWRIGHT_DEFAULT_PASSWORD = "admin"  # noqa: S105
PLAYWRIGHT_DEFAULT_API_TOKEN = "0123456789abcdef0123456789abcdef01234567"  # noqa: S105

# Sent on every browser context; the development config reads it and leaves the debug toolbar off.
DISABLE_DEBUG_TOOLBAR_HEADERS = {"X-Disable-Debug-Toolbar": "1"}


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
    context = browser.new_context(base_url=base_url, extra_http_headers=DISABLE_DEBUG_TOOLBAR_HEADERS)
    page = context.new_page()
    try:
        log_in(page, username, password)
    except LoginError as exc:
        pytest.fail(
            f"Playwright login failed against {base_url}: {exc} "
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
    headers = {**browser_context_args.get("extra_http_headers", {}), **DISABLE_DEBUG_TOOLBAR_HEADERS}
    return {
        **browser_context_args,
        "base_url": base_url,
        "storage_state": str(auth_state_path),
        "extra_http_headers": headers,
    }


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
def status_for(api):
    """Callable returning the API record of a Status valid for content_type.

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
            cache[content_type] = results[0]
        return cache[content_type]

    return _lookup


@pytest.fixture
def create_object(api):
    """Parameterized factory: create a REST object owned by this test, deleted on teardown.

    The single factory behind every per-app `created_*` fixture:

        parent = create_object("dcim/locations/", name=name, location_type=lt["id"], status=status_id)

    Objects are deleted in reverse creation order at teardown. A 404 is expected and
    ignored, since a child may already have been removed by a parent's cascade delete.
    Any other failing status is collected and reported once every delete has been
    attempted, so a server error during cleanup is visible without leaking the records
    that had not been deleted yet.
    """
    created = []

    def _create(endpoint, **fields):
        response = api.post(f"/api/{endpoint}", data=fields)
        if not response.ok:
            pytest.fail(f"POST /api/{endpoint} returned {response.status}: {response.text()}")
        record = response.json()
        created.append((endpoint, record["id"]))
        return record

    yield _create

    failures = []
    for endpoint, pk in reversed(created):
        response = api.delete(f"/api/{endpoint}{pk}/")
        if not response.ok and response.status != 404:
            failures.append(f"DELETE /api/{endpoint}{pk}/ returned {response.status}: {response.text()[:200]}")
    if failures:
        pytest.fail("Test data teardown failed:\n" + "\n".join(failures))


@pytest.fixture(scope="session")
def api_count(api):
    """Callable returning the API object count for an endpoint and filter params.

    Gives filter tests an expected count from outside the UI. Checking visible rows
    proves the rows shown match the filter, not that every matching record was shown.
    Valid only while the expected results fit on one page. Keep owned test data
    small enough to guarantee that.
    """

    def _count(endpoint, **params):
        response = api.get(f"/api/{endpoint}", params={**params, "limit": 1})
        if not response.ok:
            pytest.fail(f"GET /api/{endpoint} returned {response.status}: {response.text()}")
        return response.json()["count"]

    return _count


@pytest.fixture
def created_manufacturer(create_object):
    """A manufacturer owned by this test."""
    return create_object("dcim/manufacturers/", name=unique_name())


@pytest.fixture
def created_device(create_object, status_for, created_manufacturer):
    """A device owned by this test, with its own location type, location, device type and role.

    Also returns the related records. The device's API response gives only their id and
    URL, and the tests need their names.
    """
    unique = unique_name()
    # Nautobot rejects a device whose location type does not list dcim.device in its content types.
    location_type = create_object("dcim/location-types/", name=f"{unique}-location-type", content_types=["dcim.device"])
    location = create_object(
        "dcim/locations/",
        name=f"{unique}-location",
        location_type=location_type["id"],
        status=status_for("dcim.location")["id"],
    )
    device_type = create_object(
        "dcim/device-types/",
        model=f"{unique}-model",
        manufacturer=created_manufacturer["id"],
    )
    role = create_object("extras/roles/", name=f"{unique}-role", content_types=["dcim.device"])
    status = status_for("dcim.device")
    device = create_object(
        "dcim/devices/",
        name=unique,
        location=location["id"],
        device_type=device_type["id"],
        role=role["id"],
        status=status["id"],
    )
    return {
        "device": device,
        "location": location,
        "device_type": device_type,
        "role": role,
        "status": status,
    }
