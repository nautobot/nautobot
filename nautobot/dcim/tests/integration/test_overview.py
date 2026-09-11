"""Expandable overview rows on list views."""

import pytest

from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage
from nautobot.dcim.tests.integration.pages.manufacturers_page import ManufacturersPage


class OverviewRowTestCase:
    """Overview rows on list views: expansion where a table enables them, absence where it doesn't."""

    def test_expand_and_collapse(self, auth_page, base_url, created_manufacturer):
        """The toggle expands a full-width overview row beneath its own row, and collapses it away again."""
        manufacturers = ManufacturersPage(auth_page, base_url)
        manufacturers.navigate(name=created_manufacturer["name"])
        manufacturers.expect_overview(expanded=False)

        manufacturers.toggle_overview(expand=True)
        manufacturers.expect_overview(expanded=True)
        manufacturers.expect_overview_row_spans_entire_table()

        manufacturers.toggle_overview(expand=False)
        manufacturers.expect_overview(expanded=False)

    @pytest.mark.behavioral
    def test_overview_shows_object_fields(self, auth_page, base_url, created_manufacturer):
        """The expanded overview shows the object's own field values."""
        manufacturers = ManufacturersPage(auth_page, base_url)
        manufacturers.navigate(name=created_manufacturer["name"])
        manufacturers.toggle_overview(expand=True)
        manufacturers.expect_overview_to_contain(created_manufacturer["name"])

    def test_failed_request_leaves_toggle_collapsed(self, auth_page, base_url, created_manufacturer):
        """A failed overview request leaves the toggle collapsed rather than half-expanded."""
        manufacturers = ManufacturersPage(auth_page, base_url)
        manufacturers.fail_overview_requests()
        manufacturers.navigate(name=created_manufacturer["name"])
        manufacturers.click_overview_toggle()
        manufacturers.expect_overview(expanded=False)

    def test_no_toggles_on_a_table_opting_out(self, auth_page, base_url, created_location_tree):
        """A list view whose table opts out of overview rows renders no toggles at all."""
        locations = LocationsPage(auth_page, base_url)
        locations.navigate(name=created_location_tree["parent"]["name"])
        locations.expect_no_overview_toggles()
