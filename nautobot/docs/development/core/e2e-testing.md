# End-to-End Testing with Playwright

Playwright end-to-end (E2E) tests drive a real browser against a running Nautobot
instance. They are the forward standard for browser-based test coverage, replacing the
Selenium integration tests over time. This page dissects one real test end to end,
maps the fixture chain that makes it work, and states where each kind of new code
belongs, so you can write the next test without asking anyone anything.

E2E tests run under pytest, in an isolated job, and never touch the unittest suites:
`nautobot-server test` and the unit/integration workflow described in
[Testing](testing.md) are completely unchanged. pytest collects only the
`nautobot/*/tests/e2e/` directories, and a guard in each E2E package keeps unittest
discovery out of them.

## The layers

```no-highlight
nautobot/<app>/tests/e2e/test_*.py     what to verify (assertions, markers)
nautobot/<app>/tests/e2e/conftest.py   test data: named fixtures over the shared factory
nautobot/<app>/tests/e2e/pages/        how to drive that app's pages (selectors live here)
nautobot/e2e/                          shared infrastructure: page-object bases, fixtures
```

`nautobot/e2e/` holds `BasePage` (navigation, waits), `ListPage` (tables, the filter
drawer), and `fixtures.py` (the login chain, the REST client, and the data factory).
It deliberately lives outside `nautobot.core` so it imports without Django settings:
the E2E suite is black-box and needs a URL and a token, not a database connection.

!!! warning "Do not move this package under `nautobot.core`"
    Importing anything under `nautobot.core` executes `nautobot/core/__init__.py`,
    which initializes the Celery app from Django settings, and
    `nautobot/core/testing/__init__.py`, which imports Django models; either one makes
    the import require a full Nautobot configuration. The Selenium integration tests
    can live in `nautobot/core/testing/` because they run inside `nautobot-server
    test`, where Django is already booted, and they use it (ORM data setup, an
    in-process live server). The E2E suite runs in a plain pytest process pointed at
    a URL. Moving this package would silently make every E2E run require a local
    `nautobot_config.py`, even when the instance under test is remote.

## Why page objects

If you are coming from Django, a page object is to a page what a model is to a
database table: the schema (selectors) is defined once and consumed everywhere.
Inline selectors in test bodies are raw SQL in every view, the exact thing Django
exists to prevent.

- It is what Playwright is, not a styling choice. The official Playwright
  documentation and the pytest plugin assume the page-object model; tutorials, new
  contributors, and code-generation tools all speak it.
- The maintenance math favors it. When UI markup changes, a selector defined once in a
  page object is a one-method fix. The same selector inlined across tests breaks every
  test that touches the page, which is a large part of why the Selenium suite is being
  replaced.
- The file jump is one directory deep. `pages/` sits inside the same app directory as
  the test, and methods are named after user actions (`filter_by_parent`,
  `open_filter_drawer`), so a test body reads as intent and is reviewable by someone
  who does not know the selectors.

## A test, dissected

From `nautobot/dcim/tests/e2e/test_location_filters.py`:

```python
def test_location_filter_drawer_opens(auth_page, base_url):
    """The filter drawer starts hidden and opens from the Filter toolbar button."""
    locations = LocationsPage(auth_page, base_url)
    locations.navigate()
    assert not locations.is_filter_drawer_open()
    locations.open_filter_drawer()
    assert locations.is_filter_drawer_open()
```

- **`auth_page`** and **`base_url`** are pytest fixtures, injected by parameter name
  from `nautobot/e2e/fixtures.py`. Run `pytest --fixtures nautobot/dcim/tests/e2e` to
  list every available fixture with its location and docstring.
- **`LocationsPage`** subclasses `ListPage` and sets `_LIST_PATH`; `navigate()`,
  row counts, column reads, and all filter-drawer methods are inherited.
- There are no selectors here, and there must never be: selectors belong in page
  objects, and a page-object method lands in the same pull request as its first
  calling test.

## The fixture chain (how auth works)

```no-highlight
auth_page                    # the fixture your test requests
  └── page                   # pytest-playwright's page fixture
        └── browser_context_args   # our override injects the login state
              └── auth_state_path  # logs in ONCE per session, saves storage state
                    └── browser    # pytest-playwright's browser (honors --headed etc.)
```

One real UI login happens per session; every test's page starts authenticated. Because
the chain extends pytest-playwright's own fixtures rather than replacing them, the
standard CLI flags (`--headed`, `--slowmo`, `--screenshot`, `--tracing`,
`--browser`) all keep working. Never launch a browser directly with
`sync_playwright().start()`; it bypasses all of those.

## Test data: owned, created over REST

Tests create the records they assert on, through the REST API, and delete them on
teardown. The single parameterized factory is the `create_object` fixture; per-app
conftests wrap it in named fixtures:

```python
@pytest.fixture
def created_location_tree(create_object, status_id_for):
    status = status_id_for("dcim.location")
    location_type = create_object("dcim/location-types", name=f"{unique}-type", nestable=True)
    parent = create_object("dcim/locations", name=f"{unique}-parent", ...)
    ...
```

Owned data makes assertions exact on any instance: a filter test that creates a parent
with two children plus a decoy family can assert inclusion, exclusion, and exact
counts without knowing anything else about the database. Prefer creating decoy or
owned records over guarding assertions with if-statements. Use a unique prefix
(`ZZZ-e2e-<hex>`) for every created name.

## Structural and behavioral tests

Structural tests prove the page rendered (a table has rows, a drawer opens).
Behavioral tests prove the application produced the right output, and they are the
main value over the old Selenium coverage. A filter test is behavioral and asserts
three things:

1. Narrowing: the filtered row count is smaller than the unfiltered one.
2. Ground truth: the visible row count equals the REST API count for the same filter
   (`api_count("dcim/locations", parent=...)`). Row-level checks alone miss records
   leaking onto later pages.
3. Row values: the expected records are present and the decoys are absent.

Mark behavioral tests with `@pytest.mark.behavioral`. App scoping needs no marker:
the directory is the selector (`invoke e2e --app dcim`).

## Where new code goes

| You need to... | It goes in... |
|---|---|
| Verify a behavior | `nautobot/<app>/tests/e2e/test_<feature>.py` |
| Create or tear down a record | `nautobot/<app>/tests/e2e/conftest.py`, named `created_<thing>`, over the shared factory |
| Interact with a page element | A page-object method. Never a selector in a test file. |
| A method useful on every page | `nautobot/e2e/base_page.py` |
| A method useful on every list view | `nautobot/e2e/list_page.py` |
| A method specific to one model's page | That app's page object, e.g. `nautobot/dcim/tests/e2e/pages/locations_page.py` |
| A new shared fixture | `nautobot/e2e/fixtures.py` (keep this surface small) |

## Running the suite

The suite targets any running Nautobot instance, configured by environment variables
(`NAUTOBOT_E2E_URL`, `NAUTOBOT_E2E_USERNAME`, `NAUTOBOT_E2E_PASSWORD`,
`NAUTOBOT_E2E_API_TOKEN`). The defaults match a local development instance at
`http://localhost:8080` with the `admin`/`admin` superuser and the development API
token.

```no-highlight
poetry install --with e2e
poetry run playwright install chromium

invoke e2e                       # the whole E2E suite
invoke e2e --app dcim            # one app's suite
invoke e2e --headed              # watch the browser
invoke e2e --pattern filter      # subset by test name
```

`invoke e2e` runs pytest with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and enables only the
intended plugins explicitly (`-p playwright -p base_url`). Plugin loading is an
allowlist: nothing runs in the test process unless it was named. CI runs the same
command against a hermetic instance seeded with `TEST_FACTORY_SEED`.

Run every new test against a live instance before committing it. If a behavioral
assertion reveals the application doing something unexpected, do not bend the
assertion to match: note it in the test, and raise it for triage.
