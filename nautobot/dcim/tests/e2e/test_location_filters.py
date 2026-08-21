"""Locations list-view filter flow.

Playwright replacement for the Selenium test ``ListViewFilterTestCase.test_list_view_filter``
(formerly in nautobot/core/tests/integration/test_filters.py): open the filter drawer,
apply a parent filter, then remove it from the Advanced tab via both badge remove
buttons. The behavioral tests additionally verify the filter's *output* (row counts
against the REST API, cell values) — assertions the Selenium version did not make.
"""

import pytest

from nautobot.dcim.tests.e2e.pages.locations_page import LocationsPage


def test_location_filter_drawer_opens(auth_page, base_url):
    """The filter drawer starts hidden and opens from the Filter toolbar button."""
    locations = LocationsPage(auth_page, base_url)
    locations.navigate()
    assert not locations.is_filter_drawer_open()
    locations.open_filter_drawer()
    assert locations.is_filter_drawer_open()


@pytest.mark.behavioral
def test_location_filter_by_parent_narrows_list(auth_page, base_url, api_count, created_location_tree):
    """Filtering by parent shows exactly that parent's children.

    Narrowing, UI-count-equals-API-count, and per-row inclusion/exclusion are all
    asserted against records the test owns (see ``created_location_tree``), so the
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
def test_location_remove_filters_restores_list(auth_page, base_url, created_location_tree):
    """Removing an applied filter from the Advanced tab restores the unfiltered list.

    Exercises both removal gestures, mirroring the Selenium flow: the badge's
    remove-all button, then (after browser Back re-applies the filter) the badge's
    single-value button. The filter indicator is asserted symmetrically: present
    while the filter is applied, gone after each removal path commits.

    Indicator assertions assume no instance-level default filter: an instance with
    LOCATION_LIST_DEFAULT_MAX_DEPTH configured redirects the bare list URL to
    ?max_depth=<n>, which legitimately keeps the indicator lit. The hermetic CI
    instance leaves that setting unset.
    """
    parent = created_location_tree["parent"]
    locations = LocationsPage(auth_page, base_url)
    locations.navigate()
    unfiltered_rows = locations.get_data_row_count()
    assert not locations.has_active_filter_indicator()

    locations.filter_by_parent(parent["name"])
    assert "parent=" in locations.current_url()
    assert locations.has_active_filter_indicator()
    assert locations.get_data_row_count() < unfiltered_rows, "Filter must narrow the list before removal is tested"

    # Remove the whole parent filter with the badge's remove-all button.
    locations.open_advanced_filter_tab()
    locations.remove_all_filters("parent")
    locations.apply_advanced_filters()
    assert "parent=" not in locations.current_url()
    assert locations.get_data_row_count() == unfiltered_rows
    assert not locations.has_active_filter_indicator()

    # Back to the filtered view; remove the single filter value instead.
    locations.go_back()
    locations.open_advanced_filter_tab()
    locations.remove_filter_value("parent")
    locations.apply_advanced_filters()
    assert "parent=" not in locations.current_url()
    assert locations.get_data_row_count() == unfiltered_rows
    assert not locations.has_active_filter_indicator()
