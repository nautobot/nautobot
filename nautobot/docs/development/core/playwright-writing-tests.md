# Writing Playwright Tests

This page covers how to write Playwright tests for Nautobot core and for Nautobot apps. [Playwright Testing](playwright-testing.md) covers how to run them. Core and apps use the same base classes and fixtures from `nautobot.playwright`, so the same rules apply to both.

## Where the code goes

| What | Core | App |
|---|---|---|
| Tests | `nautobot/<app>/tests/integration/test_*.py` | `<app_name>/tests/integration/test_*.py` |
| Page objects | `nautobot/<app>/tests/integration/pages/` | `<app_name>/tests/integration/pages/` |
| Fixtures for one app | `nautobot/<app>/tests/integration/conftest.py` | `<app_name>/tests/integration/conftest.py` |
| Fixtures for every app | `nautobot/playwright/fixtures.py` | Add `pytest_plugins = ["nautobot.playwright.fixtures"]` to the app's root `conftest.py` to load the global Nautobot fixtures. |

If a fixture that you write for an app would also be useful to other apps, propose it for `nautobot.playwright.fixtures` in a core PR.

A new `tests/integration/` package needs the `load_tests` import in its `__init__.py`, as [Adding a test package](playwright-testing.md#adding-a-test-package) describes. Without it, `nautobot-server test` fails in an environment that does not have the `playwright` dependency group installed.

A test file contains test steps and assertions. It does not contain selectors. Every selector goes in a page object, so a markup change is fixed in one file instead of in every test that uses that element.

A page object extends one of the base classes in `nautobot.playwright`:

| Base class | Use it for | Set in the subclass |
|---|---|---|
| `ListPage` (`nautobot.playwright.list_page`) | a list view: rows, columns, the filter drawer, table configuration, bulk selection and bulk edit | `LIST_PATH` |
| `DetailPage` (`nautobot.playwright.detail_page`) | an object detail view: the heading, the Edit button, tabs and panels | `DETAIL_PATH`, `VERBOSE_NAME` |
| `ObjectFormPage` (`nautobot.playwright.object_form_page`) | an add or edit form: text fields, related-object pickers, submit and field errors | `ADD_PATH` |
| `BasePage` (`nautobot.playwright.base_page`) | any other page | nothing |

Before you write a page object method, check whether a base class already has it. Before you write a fixture, run `poetry run pytest --fixtures <path to tests/integration>` to list the fixtures that already exist.

A page object for a list view needs only its path. The methods for rows, columns and the filter drawer are inherited from `ListPage`:

```python
from nautobot.playwright.list_page import ListPage


class LocationsPage(ListPage):
    """The Locations list view."""

    LIST_PATH = "/dcim/locations/"

    def filter_by_parent(self, parent_name):
        """Open the filter drawer and filter the list by *parent_name*."""
        self.open_filter_drawer()
        self.pick_filter_value("parent", parent_name, exact=False)
        self.apply_filters()
```

The test then calls the page object methods in the order a user takes the steps:

```python
class ListViewFilterTestCase:
    """The Locations list-view filter drawer."""

    @pytest.mark.behavioral
    def test_filter_by_parent_narrows_list(self, auth_page, base_url, api_count, created_location_tree):
        """Filtering by parent shows exactly that parent's children."""
        parent = created_location_tree["parent"]
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        total = locations.get_data_row_count()

        locations.filter_by_parent(parent["name"])

        expected = api_count("dcim/locations/", parent=parent["id"])
        assert expected < total, "Applying the parent filter should narrow the list"
        locations.expect_row_count(expected)
        names = locations.get_column_values_by_header("Name")
        for child in created_location_tree["children"]:
            assert any(child["name"] in cell for cell in names), f"{child['name']} missing from filtered rows: {names}"
        decoy_child_name = created_location_tree["decoy_child"]["name"]
        assert not any(decoy_child_name in cell for cell in names), f"Decoy child leaked into filtered rows: {names}"
```

A selector written in a test file belongs in a page object method:

```python
# Wrong: a CSS selector in the test file.
row = auth_page.locator("table tbody tr:has(input[name='pk'])").first

# Right: the selector is in ListPage.data_row(), which LocationsPage inherits.
row = locations.data_row(0)
```

## Test data

- Use the `create_object` fixture to create the records that a test asserts on. The fixture creates them over the REST API, and when the test ends, it deletes every record that it created. Do not create test data through the UI unless the UI flow is what is being tested. For a record that the test creates through the UI, call `create_object.track(endpoint, name=name)` before the UI action, so that teardown deletes it.
- Give every record a name from `unique_name()` in `nautobot.playwright.helpers`. A fixed name collides when tests run in parallel and leaves records behind when a teardown fails.
- Use the `created_*` fixtures that already exist (`created_location`, `created_device`, `created_location_tree` and others) before you write a new one. A new fixture that creates records is named `created_<thing>`.
- Never assert a fixed count of records that the test did not create. The instance may contain any other data. Get the expected number from the API with `api_count`, or create the records yourself.
- When a test checks that a record is left out of the results, create the record that must be left out. `created_location_tree` creates a decoy parent with its own child for this reason. The test then checks the exclusion against a record that it created.
- A test that sets `?per_page=` uses the `restore_page_size` fixture. Nautobot saves the page size in the user's config, so without the fixture every later test runs with the changed page size.

## Assertions

After an action, the page can keep updating, because an htmx request, a script or a page load can finish after the test's next line runs. Check the page with `expect` on a locator because it re-reads the page until the check passes or the timeout ends, and a failure message shows what went wrong. Use `assert` for a value that does not come from the page, such as an API response.
- Check that something is absent with `expect(...).not_to_*`, never with `assert not`. An `assert not` reads the page once and passes if the change has not happened yet.
- Page objects provide locators and `expect_*` methods (`expect_row_count`, `expect_flash_message`, `expect_panel`). Do not add methods that return a `bool` from the page. A check on a `bool` cannot retry, and its failure message shows only `False`.
- Sometimes a test copies a value from the page into a Python variable, for example to compare it with a later value. Before the test reads the value, use `expect` to wait until the page is in the state needed by the test. Then read the value once. For example, `get_data_row_count()` reads the row count one time and does not retry. Use it to record a starting count, and use `expect_row_count()` to check the count.
- Every `assert` has a message that says what was expected, for example `assert expected < total, "Applying the parent filter should narrow the list"`.

## Waiting

- Do not use `page.wait_for_timeout()` or `time.sleep()`. A fixed wait is too short on a slow machine and wastes time on a fast one. The one exception is a loop that polls a job result over the API. The `wait_for_job_result` fixture contains that loop, so a test does not need to write one.
- Do not use `wait_for_load_state("networkidle")`. Pages with Select2 fields or polling keep requests open, so the network does not become idle.
- Wait for the element the next step uses. After you call a page object's `navigate()` or `go_back()`, do not add your own wait for the page to load, because those methods already wait for it. Most Nautobot pages then load parts of their content with htmx. For example, list rows load in a second request, so wait for them with `expect_row_count()` or `expect(page_object.data_row(0)).to_be_visible()`.
- Wait for a Bootstrap modal to finish opening before you click or type in it. Bootstrap ignores a request to close a modal while it is still opening, so a test that clicks Cancel straight away leaves the modal open. In the page object, open the modal with `open_modal(opener, modal)` from `BasePage`, which waits for the modal's `shown.bs.modal` event. For an example, see `BasePage.open_theme_modal()`.
- A UI action that starts a job, such as bulk edit, returns before the job finishes. `ListPage.apply_bulk_edit()` returns the job result ID. Pass that ID to the `wait_for_job_result` fixture, which polls the job result over the API until the job finishes and then returns the job result record. Check the job's effects after the call returns. The instance needs a running Celery worker, or the job will not finish. Do not wait for a job on the job result page. While the job runs, that page replaces parts of itself every 2 or 3 seconds, so the test would read text from elements that keep being replaced. The fixture reads the job's status field from the REST API instead, and stops when the status is one of Celery's finished states.
- Leave out the `timeout` argument on `expect` and other Playwright calls, so Playwright's default timeout applies. If a test or page object needs a different timeout, add a comment that explains why.

## Structural and behavioral tests

A structural test checks that the parts of a page rendered, such as the heading, the table, a column or a panel. A behavioral test checks that the values are right. Mark it with `@pytest.mark.behavioral`. For new features, write structural and behavioral tests.

- A filter test asserts four things. The filter narrows the list. The row count equals the API count for the same filter. The list shows every record that the test created to match the filter. The list does not show the decoy record, which the test created so that it does not match.
- A search test asserts that the list narrows and that every visible row contains the search term. Location and prefix search also return parents and children, so for those models assert that the searched record is in the results.
- A create test submits the form with known values, then checks the new record over the API and on its detail page.
- A detail test compares the values on the page with the values that the test used to create the record.

## Shared traps

These apply to more than one page. The base classes have a method for each one, so use that method instead of writing your own.

| Trap | Use |
|---|---|
| Select2 options for location and parent pickers show the full ancestry path, so an exact match on the name fails. On other pickers a loose match can pick a different option whose text contains the name. | `pick_filter_value(field, value, exact=False)` for location and parent fields, and the default `exact=True` for the others |
| Each list view has a Select2 search box in the page for every filter field, so an unscoped search box selector will pick the wrong one. | `select2_filter_search()` and `select2_filter_pick()` |
| Messages that appear after an action are displayed as an alert or as a toast, and a toast hides itself after a delay. | `expect_flash_message(text)`, called immediately after the action |
| Checkboxes you check on one page of a list are lost when you open another page, because htmx replaces the entire table. A bulk action then covers only the rows checked on the open page. | `select_all_matching(expected)`. It confirms that the list shows "Select all *expected* … matching query", then checks that checkbox to select every matching record on all pages. |
| The "Edit Selected" bulk edit button is hard to find with a selector. Its URL changes when a filter is active, so an exact match fails, and the "Edit All" button submits to the same URL, so a loose match finds both buttons. | `click_edit_selected()` |
| Sortable column headers contain hidden sort text, and column positions change when columns are reordered or hidden in the table configuration, or when the checkbox and overview columns are shown. | `get_table_column_headers()` and `get_column_values_by_header()`, never a fixed `td:nth-child()` |

## When the application does something unexpected

Do not change an assertion so that it matches what the application does. The assertion describes the correct behavior, and the application has a bug. Instead:

1. Add a comment to the test that describes how the application's behavior differs from the expected behavior.
2. Mark the test with `@pytest.mark.xfail(strict=True, reason="...")`. Put the bug's tracker ID in the reason if one exists.
3. Report the bug for triage.

`xfail` tells pytest that the test is expected to fail. While the bug exists, the test fails, pytest reports it as "xfailed", and the test run still passes. With `strict=True`, pytest also checks the opposite case: once someone fixes the bug and the test passes, pytest reports it as a failure. That failure tells the next person to remove the marker, so that the test goes back to checking the behavior normally.

## Checklist

Use this list before you ask for a review, and when you review a Playwright change.

- The test files contain no selectors (`locator(`, `get_by_*` and CSS strings). Every selector is in a page object.
- Every page object extends `ListPage`, `DetailPage`, `ObjectFormPage` or `BasePage`, and does not repeat a method the base class has.
- Test data comes from `create_object` or a `created_*` fixture, with names from `unique_name()`.
- No assertion compares against a fixed count of records the test did not create.
- Browser state is checked with `expect`, and absence with `expect(...).not_to_*`.
- There is no `wait_for_timeout`, `time.sleep` or `networkidle`.
- A new feature has a structural test and a behavioral test, and the behavioral test is marked `@pytest.mark.behavioral`.
- `restore_page_size` for tests that set `?per_page=`
- A message on every assert.
- A comment on every custom timeout.
- No page object methods that return a bool.
- `xfail(strict=True)` instead of an assertion changed to match a bug.
