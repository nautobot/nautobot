"""Expandable overview rows on list views."""

import re

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

    def test_failed_request_leaves_toggle_collapsed(self, auth_page, base_url, created_manufacturer):
        """A failed overview request leaves the toggle collapsed rather than half-expanded."""
        auth_page.route(re.compile(r"/overview/"), lambda route: route.fulfill(status=500, body=""))
        manufacturers = ManufacturersPage(auth_page, base_url)
        manufacturers.navigate(name=created_manufacturer["name"])

        with auth_page.expect_response(re.compile(r"/overview/")):
            manufacturers.overview_toggle().click()

        manufacturers.expect_overview(expanded=False)

    def test_no_toggles_on_a_table_opting_out(self, auth_page, base_url, created_location_tree):
        """A list view whose table opts out of overview rows renders no toggles at all."""
        locations = LocationsPage(auth_page, base_url)
        locations.navigate(name=created_location_tree["parent"]["name"])
        assert locations.overview_toggle().count() == 0
