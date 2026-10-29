"""Dynamic group create, filter-edit and static assignment flows."""

import pytest

from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage
from nautobot.extras.tests.integration.pages.device_group_assignment_page import DeviceGroupAssignmentPage
from nautobot.extras.tests.integration.pages.dynamic_group_create_page import DynamicGroupCreatePage
from nautobot.extras.tests.integration.pages.dynamic_group_detail_page import DynamicGroupDetailPage
from nautobot.extras.tests.integration.pages.dynamic_group_edit_page import DynamicGroupEditPage


class DynamicGroupTestCase:
    """Dynamic group create and edit: the saved filter, the member count after Refresh Members, and the member's tab."""

    @pytest.mark.behavioral
    @pytest.mark.usefixtures("require_celery_worker")
    def test_create_with_filter(self, auth_page, base_url, created_device_set, dynamic_group_name):
        """A group created with a location filter has exactly that location's devices as members."""
        create = DynamicGroupCreatePage(auth_page, base_url)
        create.navigate()
        pk = create.create(dynamic_group_name, content_type="dcim.device")
        group = DynamicGroupDetailPage(auth_page, base_url)
        group.expect_heading(dynamic_group_name)

        edit = DynamicGroupEditPage(auth_page, base_url)
        edit.navigate(pk)
        edit.add_filter_value("location", created_device_set["first_location"]["name"])
        edit.save()
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
        device.open_tab("dynamic_groups")
        device.expect_tab_to_contain("dynamic_groups", created_dynamic_group["name"])

    @pytest.mark.behavioral
    @pytest.mark.usefixtures("require_celery_worker")
    def test_edit_filter_and_refresh_members(self, auth_page, base_url, created_device_set, created_dynamic_group):
        """Adding a second location to the filter grows the membership once the members are refreshed."""
        pk = created_dynamic_group["id"]
        group = DynamicGroupDetailPage(auth_page, base_url)
        group.navigate(pk)
        group.expect_member_count(len(created_device_set["first_devices"]))

        edit = DynamicGroupEditPage(auth_page, base_url)
        edit.navigate(pk)
        edit.add_filter_value("location", created_device_set["second_location"]["name"])
        edit.save()
        group.expect_panel_to_contain("Filter", created_device_set["second_location"]["name"])
        # The edit alone leaves the cached membership as it was.
        group.expect_member_count(len(created_device_set["first_devices"]))

        group.refresh_members()
        expected = len(created_device_set["first_devices"]) + len(created_device_set["second_devices"])
        group.wait_for_member_count(pk, expected)
        group.navigate(pk)
        group.expect_member_count(expected)

    @pytest.mark.behavioral
    @pytest.mark.usefixtures("restore_page_size")
    def test_bulk_assign_all_filtered_items_from_all_pages(
        self, auth_page, base_url, created_device_set, created_static_group
    ):
        """Update Group Assignment for All, on a filtered device list, assigns only the filtered devices."""
        first_devices = created_device_set["first_devices"]
        devices = DeviceGroupAssignmentPage(auth_page, base_url)
        # One device per page, so the select-all box renders and the selection spans every page.
        devices.navigate(location=created_device_set["first_location"]["name"], per_page=1)
        devices.select_all_matching(len(first_devices))
        devices.assign_all_matching_to_group(created_static_group["name"])
        devices.expect_flash_message(f"Added {len(first_devices)} devices to 1 dynamic group(s).")

        group = DynamicGroupDetailPage(auth_page, base_url)
        group.navigate(created_static_group["id"])
        group.expect_member_count(len(first_devices))
        # The list above saved a page size of 1 to the user's config, so ask for a page that fits every member.
        group.navigate_members(created_static_group["id"], per_page=50)
        for device in first_devices:
            group.expect_member_listed(device["name"])
        group.expect_member_listed(created_device_set["second_devices"][0]["name"], listed=False)
