"""Tags filter on list views: the dropdown offers only the tags that apply to the listed model (#4216)."""

import pytest

from nautobot.circuits.tests.integration.pages.providers_page import ProvidersPage
from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage


class TagFilterTestCase:
    """The Tags field of the list-view filter drawer."""

    @pytest.mark.behavioral
    def test_tag_matching_content_type(self, auth_page, base_url, created_provider_tags):
        """The Providers Tags filter lists provider tags, the first 50 only until more are loaded."""
        prefix = created_provider_tags["prefix"]
        providers = ProvidersPage(auth_page, base_url)
        providers.navigate()
        providers.open_filter_drawer()

        providers.search_filter_options("tags", prefix)

        providers.expect_filter_option_count(prefix, 50)
        providers.expect_filter_option_count(f"{prefix} 51", 0)

    @pytest.mark.behavioral
    def test_tag_not_matching_content_type(self, auth_page, base_url, created_provider_tags):
        """The Locations Tags filter does not list tags that apply only to providers."""
        prefix = created_provider_tags["prefix"]
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        locations.open_filter_drawer()

        locations.search_filter_options("tags", prefix)

        locations.expect_no_filter_options()
        locations.expect_filter_option_count(prefix, 0)
