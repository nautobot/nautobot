"""Tests that a list view's Tags filter only lists tags that apply to that list's model (#4216)."""

import pytest

from nautobot.circuits.tests.integration.pages.providers_page import ProvidersPage
from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage

# Number of options select2.js loads per page in a filter dropdown.
SELECT2_PAGE_SIZE = 50


class TagFilterTestCase:
    """Tags filter dropdown on the Providers and Locations list views."""

    @pytest.mark.behavioral
    def test_tag_matching_content_type(self, auth_page, base_url, created_provider_tags):
        """Searching the Tags filter on Providers shows the first 50 provider tags, and the 51st is not on that page."""
        prefix = created_provider_tags["prefix"]
        tags = created_provider_tags["tags"]
        providers = ProvidersPage(auth_page, base_url)
        providers.navigate()
        providers.open_filter_drawer()

        providers.search_filter_options("tags", prefix)

        providers.expect_filter_option_count(prefix, SELECT2_PAGE_SIZE)
        providers.expect_filter_option_count(tags[-1]["name"], 0)

    @pytest.mark.behavioral
    def test_tag_not_matching_content_type(self, auth_page, base_url, created_provider_tags):
        """Searching the Tags filter on Locations finds none of the provider-only tags."""
        prefix = created_provider_tags["prefix"]
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        locations.open_filter_drawer()

        locations.search_filter_options("tags", prefix)

        locations.expect_no_filter_options()
        locations.expect_filter_option_count(prefix, 0)
