"""Dynamic group create, filter-edit and static assignment flows."""

import pytest

from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage
from nautobot.extras.tests.integration.pages.device_group_assignment_page import DeviceGroupAssignmentPage
from nautobot.extras.tests.integration.pages.dynamic_group_create_page import DynamicGroupFormPage
from nautobot.extras.tests.integration.pages.dynamic_group_detail_page import DynamicGroupDetailPage
from nautobot.playwright.helpers import unique_name


class DynamicGroupTestCase:
    """Dynamic group create and edit, the member's tab, and static assignment from a filtered device list."""

    @pytest.mark.behavioral
    @pytest.mark.usefixtures("require_celery_worker")
    def test_create_with_filter(self, auth_page, base_url, create_object, created_device_set):
        """A group created with a location filter has exactly that location's devices as members."""
        name = unique_name()
        create_object.track("extras/dynamic-groups/", name=name)
        form = DynamicGroupFormPage(auth_page, base_url)
        form.navigate()
        pk = form.create(name, content_type="dcim.device")
        group = DynamicGroupDetailPage(auth_page, base_url)
        group.expect_flash_message(f"Created dynamic group {name}")
        group.expect_heading(name)
        group.expect_edit_button()

        group.click_edit()
        form.add_filter_value("location", created_device_set["first_location"]["name"])
        form.save()
        group.expect_flash_message(f"Modified dynamic group {name}")
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

        group.click_edit()
        form = DynamicGroupFormPage(auth_page, base_url)
        form.add_filter_value("location", created_device_set["second_location"]["name"])
        form.save()
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
        devices.navigate(per_page=1)
        devices.open_filter_drawer()
        devices.pick_filter_value("location", created_device_set["first_location"]["name"], exact=False)
        devices.apply_filters()
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
        group.expect_no_member_listed(created_device_set["second_devices"][0]["name"])
