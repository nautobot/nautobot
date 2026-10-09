"""Dynamic group create and filter-edit flows.

Tests include: create a filter-defined device group through the UI, then edit its filter
and refresh its members. Member counts are asserted against devices the test owns.
"""

import pytest

from nautobot.extras.tests.integration.pages.dynamic_groups_page import DynamicGroupPage
from nautobot.playwright.helpers import unique_name


class DynamicGroupTestCase:
    """Playwright port of ``extras/tests/selenium/test_dynamicgroups.py::DynamicGroupTestCase.test_create_and_update``.

    The Selenium test is split into a create test and an edit test. Saving a group in the
    UI does not recalculate its membership, so both tests click "Refresh Members" and wait
    for its job before asserting the new count.
    """

    @pytest.mark.behavioral
    def test_create_with_filter(self, auth_page, base_url, created_device_set, dynamic_group_cleanup):
        """A group created with a location filter has exactly that location's devices as members.

        As in the edit test below, `wait_for_member_count` polls the members REST endpoint
        once a second for up to 60 seconds while the refresh job runs.
        """
        group = DynamicGroupPage(auth_page, base_url)
        name = unique_name()
        group.navigate_add()
        pk = group.create(name, content_type="dcim.device")
        dynamic_group_cleanup.append(pk)
        group.expect_heading(name)

        group.navigate_edit(pk)
        group.add_filter_value("location", created_device_set["first_location"]["name"])
        group.save()
        group.expect_member_count(0)

        group.refresh_members()
        expected = len(created_device_set["first_devices"])
        group.wait_for_member_count(pk, expected)
        group.navigate(pk)
        group.expect_member_count(expected)

    @pytest.mark.behavioral
    def test_edit_filter_and_refresh_members(self, auth_page, base_url, created_device_set, created_dynamic_group):
        """Adding a second location to the filter grows the membership once the members are refreshed.

        The new count only reaches the page after the refresh job finishes, which the
        detail view does not signal, so `wait_for_member_count` polls the members REST
        endpoint once a second for up to 60 seconds before the page is reloaded and checked.
        """
        pk = created_dynamic_group["id"]
        group = DynamicGroupPage(auth_page, base_url)
        group.navigate(pk)
        group.expect_member_count(len(created_device_set["first_devices"]))

        group.navigate_edit(pk)
        group.add_filter_value("location", created_device_set["second_location"]["name"])
        group.save()
        # The edit alone leaves the cached membership as it was.
        group.expect_member_count(len(created_device_set["first_devices"]))

        group.refresh_members()
        expected = len(created_device_set["first_devices"]) + len(created_device_set["second_devices"])
        group.wait_for_member_count(pk, expected)
        group.navigate(pk)
        group.expect_member_count(expected)
