"""Dynamic group create and filter-edit flows."""

import pytest

from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage
from nautobot.extras.tests.integration.pages.dynamic_groups_page import DynamicGroupPage


class DynamicGroupTestCase:
    """Dynamic group create and edit: the saved filter, the member count after Refresh Members, and the member's tab."""

    @pytest.mark.behavioral
    @pytest.mark.usefixtures("require_celery_worker", "refresh_members_job_on_default_queue")
    def test_create_with_filter(self, auth_page, base_url, created_device_set, dynamic_group_name):
        """A group created with a location filter has exactly that location's devices as members."""
        group = DynamicGroupPage(auth_page, base_url)
        group.navigate_add()
        pk = group.create(dynamic_group_name, content_type="dcim.device")
        group.expect_heading(dynamic_group_name)

        group.navigate_edit(pk)
        group.add_filter_value("location", created_device_set["first_location"]["name"])
        group.save()
        group.expect_panel_to_contain("Filter", created_device_set["first_location"]["name"])
        group.expect_member_count(0)

        group.refresh_members()
        expected = len(created_device_set["first_devices"])
        group.wait_for_member_count(pk, expected)
        group.navigate(pk)
        group.expect_member_count(expected)

    @pytest.mark.behavioral
    def test_member_device_lists_group(self, auth_page, base_url, created_device_set, created_dynamic_group):
        """A member device's Dynamic Groups tab lists the group."""
        device = DeviceDetailPage(auth_page, base_url)
        device.navigate(created_device_set["first_devices"][0]["id"])
        device.expect_dynamic_groups_tab_to_list(created_dynamic_group["name"])

    @pytest.mark.behavioral
    @pytest.mark.usefixtures("require_celery_worker", "refresh_members_job_on_default_queue")
    def test_edit_filter_and_refresh_members(self, auth_page, base_url, created_device_set, created_dynamic_group):
        """Adding a second location to the filter grows the membership once the members are refreshed."""
        pk = created_dynamic_group["id"]
        group = DynamicGroupPage(auth_page, base_url)
        group.navigate(pk)
        group.expect_member_count(len(created_device_set["first_devices"]))

        group.navigate_edit(pk)
        group.add_filter_value("location", created_device_set["second_location"]["name"])
        group.save()
        group.expect_panel_to_contain("Filter", created_device_set["second_location"]["name"])
        # The edit alone leaves the cached membership as it was.
        group.expect_member_count(len(created_device_set["first_devices"]))

        group.refresh_members()
        expected = len(created_device_set["first_devices"]) + len(created_device_set["second_devices"])
        group.wait_for_member_count(pk, expected)
        group.navigate(pk)
        group.expect_member_count(expected)
