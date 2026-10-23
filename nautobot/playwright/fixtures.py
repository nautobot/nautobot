"""Shared pytest fixture surface for the Playwright test suite.

Registered once, via `pytest_plugins` in the repository-root `conftest.py`. Per-app
`tests/integration/conftest.py` files build thin named fixtures on top of
`create_object`. The fixtures that more than one app needs (a location tree, a
manufacturer, a device, and the records a device needs) are defined here. Run
`pytest --fixtures nautobot/<app>/tests/integration` to list every available fixture
with its location.

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

from nautobot.playwright.accessibility import get_axe_core_source
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

    For an object the test creates through the UI, call `track` before the UI action.
    Teardown deletes every object matching the filters:

        create_object.track("dcim/devices/", name=name)

    Objects are deleted in the reverse of the order they were created or tracked. A 404 is expected and
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

    def _track(endpoint, **filters):
        if not filters:
            pytest.fail(
                f"create_object.track({endpoint!r}) needs at least one filter, or teardown deletes every record."
            )
        created.append((endpoint, filters))

    _create.track = _track
    yield _create

    failures = []
    # Each entry is a created object's id or a tracked object's filters.
    for endpoint, target in reversed(created):
        if isinstance(target, dict):
            response = api.get(f"/api/{endpoint}", params=target)
            if not response.ok:
                failures.append(f"GET /api/{endpoint} returned {response.status}: {response.text()[:200]}")
                continue
            pks = [record["id"] for record in response.json()["results"]]
        else:
            pks = [target]
        for pk in pks:
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
def created_location_tree(create_object, status_for):
    """A location family owned by this test, in a location type of its own.

    Creates a parent with two children, plus a decoy parent with its own child, so a
    parent-filter test can assert both inclusion (the children) and exclusion (the
    decoy's child) against records this test controls, regardless of other data in the
    instance. All records use a unique `ZZZ-test-` prefixed name and are deleted on teardown.
    """
    unique = unique_name()
    status = status_for("dcim.location")["id"]
    location_type = create_object("dcim/location-types/", name=f"{unique}-type", nestable=True)
    parent = create_object("dcim/locations/", name=f"{unique}-parent", location_type=location_type["id"], status=status)
    children = [
        create_object(
            "dcim/locations/",
            name=f"{unique}-child-{index}",
            location_type=location_type["id"],
            status=status,
            parent=parent["id"],
        )
        for index in (1, 2)
    ]
    decoy = create_object("dcim/locations/", name=f"{unique}-decoy", location_type=location_type["id"], status=status)
    decoy_child = create_object(
        "dcim/locations/",
        name=f"{unique}-decoy-child",
        location_type=location_type["id"],
        status=status,
        parent=decoy["id"],
    )
    return {"parent": parent, "children": children, "decoy": decoy, "decoy_child": decoy_child}


@pytest.fixture
def created_manufacturer(create_object):
    """A manufacturer owned by this test."""
    return create_object("dcim/manufacturers/", name=unique_name())


@pytest.fixture
def created_device_prerequisites(create_object, status_for, created_manufacturer):
    """A location, device type and role created for this test, and a device Status, as API records."""
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
    return {
        "location": location,
        "device_type": device_type,
        "role": role,
        "status": status_for("dcim.device"),
    }


@pytest.fixture
def created_device(create_object, created_device_prerequisites):
    """A device created for this test, plus its related records, since the device record has only their ids."""
    device = create_object(
        "dcim/devices/",
        name=unique_name(),
        location=created_device_prerequisites["location"]["id"],
        device_type=created_device_prerequisites["device_type"]["id"],
        role=created_device_prerequisites["role"]["id"],
        status=created_device_prerequisites["status"]["id"],
    )
    return {"device": device, **created_device_prerequisites}


@pytest.fixture
def axe_core_on_load(context):
    """Load axe-core into every page that this test's browser context opens from here on.

    Use it in a test that scans many pages. `run_axe` loads axe-core itself when a page lacks it, but the
    Playwright trace (`--tracing=retain-on-failure` in CI) records the 570 KB source with every call that
    passes it. An init script is recorded once.
    """
    context.add_init_script(get_axe_core_source())
