"""Locations list-view filter flow.

Tests include: open the filter drawer, apply a parent filter, then remove it from the
Advanced tab via both badge remove buttons. The behavioral tests additionally verify
the filter's *output* (row counts against the REST API, cell values).
"""

import pytest

from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage


class ListViewFilterTestCase:
    """1:1 Playwright port of ``core/tests/selenium/test_filters.py::ListViewFilterTestCase.test_list_view_filter``.

    The single Selenium test is fanned out into three behavior-scoped tests below; the
    class keeps the Selenium name as the migration ledger. Interim structure, not the
    long-term pattern — retire this class when generic list-view filter tests land.
    """

    def test_filter_drawer_opens(self, auth_page, base_url):
        """The filter drawer starts hidden and opens from the Filter toolbar button."""
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        assert not locations.is_filter_drawer_open()
        locations.open_filter_drawer()
        assert locations.is_filter_drawer_open()

    @pytest.mark.behavioral
    def test_filter_by_parent_narrows_list(self, auth_page, base_url, api_count, created_location_tree):
        """Filtering by parent shows exactly that parent's children.

        Narrowing, UI-count-equals-API-count, and per-row inclusion/exclusion are all
        asserted against records the test owns (see `created_location_tree`), so the
        test is independent of whatever other data the instance holds.
        """
        parent = created_location_tree["parent"]
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        total = locations.get_data_row_count()

        locations.filter_by_parent(parent["name"])

        assert "parent=" in locations.current_url()
        filtered = locations.get_data_row_count()
        assert filtered < total, "Applying the parent filter should have narrowed the list"
        assert filtered == api_count("dcim/locations", parent=parent["id"]), "UI row count should match the API count"
        names = locations.get_column_values_by_header("Name")
        for child in created_location_tree["children"]:
            assert any(child["name"] in cell for cell in names), f"{child['name']} missing from filtered rows: {names}"
        decoy_child_name = created_location_tree["decoy_child"]["name"]
        assert not any(decoy_child_name in cell for cell in names), f"Decoy child leaked into filtered rows: {names}"

    @pytest.mark.behavioral
    def test_remove_filters_restores_list(self, auth_page, base_url, created_location_tree):
        """Removing an applied filter from the Advanced tab restores the unfiltered list.

        Exercises both removal gestures: the badge's
        remove-all button, then (after browser Back re-applies the filter) the badge's
        single-value button. The filter indicator is asserted symmetrically: lit while
        the filter is applied, restored to its pre-filter baseline after each removal
        path commits.

        The baseline is captured rather than assumed False so the test holds on instances
        with an admin-configured default filter (LOCATION_LIST_DEFAULT_MAX_DEPTH redirects
        the bare list URL to ?max_depth=<n>, which legitimately keeps the indicator lit).
        On the hermetic CI instance the baseline is False, so the assertions are exactly
        as strict as an absolute check there.
        """
        parent = created_location_tree["parent"]
        locations = LocationsPage(auth_page, base_url)
        locations.navigate()
        unfiltered_rows = locations.get_data_row_count()
        baseline_indicator = locations.has_active_filter_indicator()

        locations.filter_by_parent(parent["name"])
        assert "parent=" in locations.current_url()
        assert locations.has_active_filter_indicator()
        assert locations.get_data_row_count() < unfiltered_rows, "Filter must narrow the list before removal is tested"

        # Remove the whole parent filter with its badge's X button.
        locations.open_advanced_filter_tab()
        locations.remove_filter("parent")
        locations.apply_advanced_filters()
        assert "parent=" not in locations.current_url()
        assert locations.get_data_row_count() == unfiltered_rows
        assert locations.has_active_filter_indicator() == baseline_indicator

        # Back to the filtered view; remove the single filter value instead.
        locations.go_back()
        locations.open_advanced_filter_tab()
        locations.remove_filter_value("parent")
        locations.apply_advanced_filters()
        assert "parent=" not in locations.current_url()
        assert locations.get_data_row_count() == unfiltered_rows
        assert locations.has_active_filter_indicator() == baseline_indicator
