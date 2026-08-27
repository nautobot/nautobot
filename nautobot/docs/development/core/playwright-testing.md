# Playwright Testing

Playwright tests drive a real browser against a running Nautobot instance. They run
under pytest, in their own CI job, and never touch the unittest-based suites.
`nautobot-server test` and the workflow described in [Testing](testing.md) are
unchanged.

!!! warning "Interim structure"
    The Playwright tests in this release are one-to-one ports of existing Selenium
    tests, keeping the Selenium file and class names so the migration is traceable.
    Do not treat their structure, naming, or layout as the standard. The long-term
    pattern (including generic, per-model test classes) will be defined in a separate
    proposal before the next release. In the meantime, browser tests for new features
    should be written as Playwright one-offs following the existing tests' structure,
    never as new Selenium tests, with the expectation that the long-term pattern may
    restructure them.

    This page covers how to **run** the suite.

## Layout

```no-highlight
nautobot/<app>/tests/integration/     Playwright tests for that app (pytest-only)
nautobot/<app>/tests/selenium/        the existing Selenium tests (unchanged)
nautobot/playwright/                  shared infrastructure the Playwright tests import
```

!!! warning "Do not move `nautobot/playwright/` under `nautobot.core`"
    Importing anything under `nautobot.core` executes `nautobot/core/__init__.py`,
    which initializes the Celery app from Django settings. That would make every
    Playwright run require a local `nautobot_config.py`, even when the instance under
    test is remote. The suite is black-box, requiring only a URL and a token, not a
    database connection.

## Running the suite

The suite targets any running Nautobot instance it can reach over HTTP, configured by
environment variables (`NAUTOBOT_PLAYWRIGHT_URL`, `NAUTOBOT_PLAYWRIGHT_USERNAME`,
`NAUTOBOT_PLAYWRIGHT_PASSWORD`, `NAUTOBOT_PLAYWRIGHT_API_TOKEN`). The defaults match
a local development instance at `http://localhost:8080` with the `admin`/`admin`
superuser and the development API token. The machine running pytest still needs this
repository installed, because pytest imports the `nautobot.playwright` package at
collection time.

```no-highlight
poetry install --with playwright
poetry run playwright install chromium

invoke playwright                       # run all playwright tests
invoke playwright --app dcim            # one app's tests
invoke playwright --headed              # watch the browser while tests are running
invoke playwright --pattern filter      # subset by test name
invoke playwright --url https://...     # a remote instance
invoke playwright --marker behavioral        # output-correctness tests only
invoke playwright --marker "not behavioral"  # fast structural pass
```

`invoke playwright` runs pytest with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and enables
only the intended plugins explicitly (`-p playwright -p base_url`). Nothing runs in
the test process unless it was named. Traces and screenshots are captured for failed
tests only, under `test-results/`.

### Selecting tests

Tests that verify application output (row counts, values, side effects)
carry `@pytest.mark.behavioral`. Unmarked tests check page structure only.
The mark is simply a filter. Without `--marker`, every test runs, marked or
not, and an unmarked test counts as "not behavioral" when filtering. Marks
are registered in pyproject.toml, and a misspelled mark on a test fails
collection with `--strict-markers` in the repo's pytest config. App scoping
is by directory (`--app dcim`), not by mark.

## CI

The CI job (`playwright-test`) starts an isolated instance, seeds it with
`nautobot-server generate_test_data` (`TEST_FACTORY_SEED`), and runs the same
`invoke playwright` command. Tests create the specific records they assert on over
the REST API and delete them on teardown. The seed is run to provide a realistically
populated instance *around* those records, so narrowing and exclusion assertions are
meaningful rather than trivially true. On failure the job uploads the Playwright
traces and screenshots as a build artifact and prints the server log.

## Adding a test package

If a new `nautobot/<app>/tests/integration/` package is created, its `__init__.py`
MUST re-export the discovery guard (`from nautobot.playwright import load_tests`)
copied from any existing app's `__init__.py`. Without it, `nautobot-server test`
discovery imports pytest-only modules and fails in environments without the
`playwright` dependency group.

If a behavioral assertion reveals the application doing something unexpected, do not
just change the assertion to match. Note it in the test and raise it for triage.

When writing tests, `poetry run pytest --fixtures nautobot/<app>/tests/integration`
lists the available fixtures with their docstrings (the path scopes the listing to
fixtures that suite can use).
