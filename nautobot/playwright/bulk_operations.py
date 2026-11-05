"""Shared bulk edit and bulk delete tests for any model's list view.

The Playwright port of the Selenium `BulkOperationsTestCases.BulkOperationsTestCase` in
`nautobot.core.testing.integration`, with the same 14 tests in the same order. A subclass
names the model through the same class attributes and creates its records in
`setup_items`:

    class DeviceBulkOperationsTestCase(bulk_operations.BulkOperationsTestCase):
        model_base_viewname = "dcim:device"
        model_edit_data = {"serial": "Test serial"}
        model_filter_by = {"location": "{prefix}-location-2"}

        def setup_items(self, create_object, status_for, prefix):
            ...

Import the module rather than the class. pytest collects every `*TestCase` class in a
test module's namespace, and this one has no records to work on.

The Selenium tests empty the model's table before creating their records. These run
against a shared instance, so every list view they open is scoped to this test's records
by searching for a unique prefix (`?q=<prefix>`) that every record's name carries.
"""

import pytest

from nautobot.playwright.helpers import unique_name
from nautobot.playwright.job_result_page import JobResultPage
from nautobot.playwright.list_page import ListPage


class BulkOperationsTestCase:
    """Bulk edit and bulk delete of one, all, filtered, and cross-page selections."""

    # The model's base view name, e.g. "dcim:device". The list view and the REST endpoint
    # are derived from it: /dcim/devices/ and /api/dcim/devices/.
    model_base_viewname: str
    # Text fields to set on the bulk edit form, and the REST filter that finds the edited records.
    model_edit_data: dict
    # Filter drawer fields and the option to pick in each, which select the "filtered" records.
    # "{prefix}" in a value is replaced with the prefix setup_items was given.
    model_filter_by: dict
    # How many records setup_items creates in all, and how many of them model_filter_by selects.
    # Any record that already matched the prefix is added to "all". There should be none.
    model_expected_counts = {
        "all": 5,
        "filtered": 2,
    }
    # The plural when it is not the model name plus "s", e.g. "ip addresses".
    override_model_plural = None

    def setup_items(self, create_object, status_for, prefix):
        """Create the records under test, each with *prefix* in a name the list view's search matches."""
        raise NotImplementedError

    @property
    def model_plural(self) -> str:
        """The model's verbose plural, as the list view's messages print it."""
        if self.override_model_plural is None:
            return f"{self.model_base_viewname.split(':')[1].replace('_', ' ')}s"
        return self.override_model_plural

    @property
    def list_path(self) -> str:
        """The list view's path, e.g. /dcim/devices/."""
        app_label = self.model_base_viewname.split(":")[0]
        return f"/{app_label}/{self.model_plural.replace(' ', '-')}/"

    @pytest.fixture(autouse=True)
    def _setup(self, auth_page, base_url, create_object, status_for, api_count, restore_page_size):  # pylint: disable=unused-argument
        """Create this test's records, compute the expected counts, and open the list view on them.

        restore_page_size is requested for every test because the cross-page tests save a
        page size of 1 to the user's config.
        """
        self.prefix = unique_name()
        self.endpoint = self.list_path.lstrip("/")
        self.filter_by = {field: value.format(prefix=self.prefix) for field, value in self.model_filter_by.items()}
        self.api_count = api_count

        existing = api_count(self.endpoint, q=self.prefix)
        self.setup_items(create_object, status_for, self.prefix)
        # The filter cannot be counted before setup_items creates the records it names. Those
        # names carry the prefix, so no record that existed before can match the filter.
        self.expected_counts = {
            "all": existing + self.model_expected_counts["all"],
            "filtered": self.model_expected_counts["filtered"],
        }
        for scope, filters in (("all", {}), ("filtered", self.filter_by)):
            actual = api_count(self.endpoint, q=self.prefix, **filters)
            assert actual == self.expected_counts[scope], (
                f"setup_items left {actual} {scope} records matching {self.prefix!r}, "
                f"expected {self.expected_counts[scope]}. Check model_expected_counts."
            )

        self.list_page = ListPage(auth_page, base_url, list_path=self.list_path)
        self.job_result_page = JobResultPage(auth_page, base_url)
        self.go_to_model_list_page()

    def go_to_model_list_page(self, **params):
        """Open the list view on this test's records."""
        self.list_page.navigate(q=self.prefix, **params)

    def apply_filter(self):
        """Pick each model_filter_by option in the filter drawer and apply them."""
        self.list_page.open_filter_drawer()
        for field, value in self.filter_by.items():
            self.list_page.pick_filter_value(field, value, exact=False)
        self.list_page.apply_filters()

    def edit_and_apply(self):
        """Fill in model_edit_data on the bulk edit form, submit it, and wait for the job to complete."""
        for field_name, field_value in self.model_edit_data.items():
            self.list_page.fill_bulk_edit_field(field_name, field_value)
        self.list_page.apply_bulk_edit()
        self.job_result_page.expect_job_description("Bulk edit objects.")
        self.job_result_page.expect_status("Completed")

    def confirm_delete(self):
        """Confirm the bulk delete and wait for the job to complete."""
        self.list_page.confirm_bulk_delete()
        self.job_result_page.expect_job_description("Bulk delete objects.")
        self.job_result_page.expect_status("Completed")

    def assert_edited_count(self, expected):
        """Assert that *expected* of this test's records now hold model_edit_data."""
        actual = self.api_count(self.endpoint, q=self.prefix, **self.model_edit_data)
        assert actual == expected, f"{actual} {self.model_plural} hold {self.model_edit_data}, expected {expected}"

    # -------------------------------------------------------------------------
    # Bulk edit
    # -------------------------------------------------------------------------

    def test_bulk_edit_require_selection(self):
        """Edit Selected with nothing selected stays on the list view and says nothing was selected."""
        self.list_page.click_edit_selected()

        self.list_page.expect_on_list()
        self.list_page.expect_flash_message(f"No {self.model_plural} were selected")

    def test_bulk_edit_all_items(self):
        """Editing every row on the page edits every record."""
        self.list_page.select_all_rows()
        self.list_page.click_edit_selected()
        self.list_page.expect_url_contains(f"{self.list_path}edit/")
        self.list_page.expect_bulk_edit_count(self.expected_counts["all"])

        self.edit_and_apply()

        self.assert_edited_count(self.expected_counts["all"])

    def test_bulk_edit_one_item(self):
        """Editing one selected row edits only that record."""
        self.list_page.select_first_row()
        self.list_page.click_edit_selected()
        self.list_page.expect_url_contains(f"{self.list_path}edit/")
        self.list_page.expect_bulk_edit_count(1)

        self.edit_and_apply()

        self.assert_edited_count(1)

    def test_bulk_edit_all_items_from_all_pages(self):
        """Edit All, with one record per page, edits the records on every page."""
        self.go_to_model_list_page(per_page=1)
        self.list_page.select_all_matching(self.expected_counts["all"])
        self.list_page.click_edit_all()
        self.list_page.expect_url_contains(f"{self.list_path}edit/")
        self.list_page.expect_bulk_edit_count(self.expected_counts["all"])

        self.edit_and_apply()

        self.assert_edited_count(self.expected_counts["all"])

    def test_bulk_edit_all_filtered_items(self):
        """Editing every row of a filtered list edits every record the filter selects, and no other."""
        self.apply_filter()
        self.list_page.expect_row_count(self.expected_counts["filtered"])

        self.list_page.select_all_rows()
        self.list_page.click_edit_selected()
        self.list_page.expect_url_contains(f"{self.list_path}edit/")
        self.list_page.expect_bulk_edit_count(self.expected_counts["filtered"])

        self.edit_and_apply()

        self.assert_edited_count(self.expected_counts["filtered"])

    def test_bulk_edit_one_filtered_item(self):
        """Editing one row of a filtered list edits only that record."""
        self.apply_filter()
        self.list_page.expect_row_count(self.expected_counts["filtered"])

        self.list_page.select_first_row()
        self.list_page.click_edit_selected()
        self.list_page.expect_url_contains(f"{self.list_path}edit/")
        self.list_page.expect_bulk_edit_count(1)

        self.edit_and_apply()

        self.assert_edited_count(1)

    def test_bulk_edit_all_filtered_items_from_all_pages(self):
        """Edit All on a filtered list, with one record per page, edits every record the filter selects, and no other."""
        self.go_to_model_list_page(per_page=1)
        self.apply_filter()

        self.list_page.select_all_matching(self.expected_counts["filtered"])
        self.list_page.click_edit_all()
        self.list_page.expect_url_contains(f"{self.list_path}edit/")
        self.list_page.expect_bulk_edit_count(self.expected_counts["filtered"])

        self.edit_and_apply()

        self.assert_edited_count(self.expected_counts["filtered"])

    # -------------------------------------------------------------------------
    # Bulk delete
    # -------------------------------------------------------------------------
    # Each test checks the count on the confirmation page before it confirms, so a
    # selection that reached past this test's records stops there.

    def test_bulk_delete_require_selection(self):
        """Delete Selected with nothing selected stays on the list view and says nothing was selected."""
        self.list_page.click_delete_selected()

        self.list_page.expect_on_list()
        self.list_page.expect_flash_message(f"No {self.model_plural} were selected for deletion.")

    def test_bulk_delete_all_items(self):
        """Deleting every row on the page deletes every record."""
        self.list_page.select_all_rows()
        self.list_page.click_delete_selected()
        self.list_page.expect_url_contains(f"{self.list_path}delete/")
        self.list_page.expect_bulk_delete_count(self.expected_counts["all"])

        self.confirm_delete()

        self.go_to_model_list_page()
        self.list_page.expect_row_count(0)

    def test_bulk_delete_one_item(self):
        """Deleting one selected row deletes only that record."""
        self.list_page.select_first_row()
        self.list_page.click_delete_selected()
        self.list_page.expect_url_contains(f"{self.list_path}delete/")
        self.list_page.expect_bulk_delete_count(1)

        self.confirm_delete()

        self.go_to_model_list_page()
        self.list_page.expect_row_count(self.expected_counts["all"] - 1)

    def test_bulk_delete_all_items_from_all_pages(self):
        """Delete All, with one record per page, deletes the records on every page."""
        self.go_to_model_list_page(per_page=1)
        self.list_page.select_all_matching(self.expected_counts["all"])
        self.list_page.click_delete_all()
        self.list_page.expect_url_contains(f"{self.list_path}delete/")
        self.list_page.expect_bulk_delete_count(self.expected_counts["all"])

        self.confirm_delete()

        self.go_to_model_list_page()
        self.list_page.expect_row_count(0)

    def test_bulk_delete_all_filtered_items(self):
        """Deleting every row of a filtered list deletes every record the filter selects, and no other."""
        self.apply_filter()
        self.list_page.expect_row_count(self.expected_counts["filtered"])

        self.list_page.select_all_rows()
        self.list_page.click_delete_selected()
        self.list_page.expect_url_contains(f"{self.list_path}delete/")
        self.list_page.expect_bulk_delete_count(self.expected_counts["filtered"])

        self.confirm_delete()

        self.go_to_model_list_page()
        self.list_page.expect_row_count(self.expected_counts["all"] - self.expected_counts["filtered"])

    def test_bulk_delete_one_filtered_items(self):
        """Deleting one row of a filtered list deletes only that record."""
        self.apply_filter()
        self.list_page.expect_row_count(self.expected_counts["filtered"])

        self.list_page.select_first_row()
        self.list_page.click_delete_selected()
        self.list_page.expect_url_contains(f"{self.list_path}delete/")
        self.list_page.expect_bulk_delete_count(1)

        self.confirm_delete()

        self.go_to_model_list_page()
        self.list_page.expect_row_count(self.expected_counts["all"] - 1)

    def test_bulk_delete_all_filtered_items_from_all_pages(self):
        """Delete All on a filtered list, with one record per page, deletes every record the filter selects, and no other."""
        self.go_to_model_list_page(per_page=1)
        self.apply_filter()

        self.list_page.select_all_matching(self.expected_counts["filtered"])
        self.list_page.click_delete_all()
        self.list_page.expect_url_contains(f"{self.list_path}delete/")
        self.list_page.expect_bulk_delete_count(self.expected_counts["filtered"])

        self.confirm_delete()

        self.go_to_model_list_page(per_page=50)
        self.list_page.expect_row_count(self.expected_counts["all"] - self.expected_counts["filtered"])

        # Filter again and assert that all the filtered records were deleted.
        self.apply_filter()
        self.list_page.expect_row_count(0)
