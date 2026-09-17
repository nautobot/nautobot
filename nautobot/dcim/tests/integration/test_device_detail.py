from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.core.testing.integration import CollapseAllButtonTestCase, SeleniumTestCase
from nautobot.core.ui.object_detail import Button, Panel
from nautobot.dcim.models import Device
from nautobot.extras.models import ComputedField, CustomField
from nautobot.extras.tests.integration import create_test_device


class DeviceDetailTestCase(SeleniumTestCase):
    """Integration tests for Device detail view rendering."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.device = create_test_device("Device 1")

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_device_detail_renders_fully(self):
        """Test that the Device detail page contains all expected panels and other content."""
        self.browser.visit(self.live_server_url + reverse("dcim:device", kwargs={"pk": self.device.pk}))

        # Page title
        self.assertTrue(self.browser.is_text_present(self.device.name))
        # Tab titles? TODO
        # Created date? TODO
        # Last updated date - as this is relative time, skip it
        # Buttons
        self.assertTrue(self.browser.is_text_present("Add Components", wait_time=5))
        self.assertTrue(self.browser.is_text_present("Edit Device", wait_time=5))
        # Device panel contents
        self.assertTrue(self.browser.is_text_present(self.device.location.name, wait_time=5))
        self.assertTrue(self.browser.is_text_present(self.device.device_type.model, wait_time=5))
        # Management panel contents
        self.assertTrue(self.browser.is_text_present(self.device.role.name, wait_time=5))
        self.assertTrue(self.browser.is_text_present(self.device.status.name, wait_time=5))
        # Comments panel contents
        # Tags panel contents
        self.assertTrue(self.browser.is_text_present("No tags assigned", wait_time=5))
        # Assigned VRFs panel contents
        self.assertTrue(self.browser.is_text_present("No VRF-device assignments found", wait_time=5))
        # Clusters panel contents
        self.assertTrue(self.browser.is_text_present("No clusters found", wait_time=5))
        # Services panel contents
        self.assertTrue(self.browser.is_text_present("No services found", wait_time=5))
        # Images panel contents
        self.assertTrue(self.browser.is_text_present("No image attachments found", wait_time=5))
        # Virtual Device Contexts panel contents
        self.assertTrue(self.browser.is_text_present("No virtual device contexts found", wait_time=5))
        # Panel titles
        panel_titles = [elem.text.lower() for elem in self.browser.find_by_css(".card-header strong")]
        self.assertIn("device", panel_titles)
        # self.assertIn("virtual chassis", panel_titles)  # not applicable to self.device
        self.assertIn("management", panel_titles)
        self.assertIn("comments", panel_titles)
        self.assertIn("tags", panel_titles)
        # self.assertIn("power utilization", panel_titles)  # not applicable to self.device
        self.assertIn("assigned vrfs", panel_titles)
        self.assertIn("clusters", panel_titles)
        self.assertIn("services", panel_titles)
        self.assertIn("images", panel_titles)
        self.assertIn("virtual device contexts", panel_titles)

    def test_device_detail_renders_fully_with_deferred_rendering(self):
        """Repeat test_device_detil_renders_fully() with deferred rendering of components enabled."""
        with mock.patch.object(Button, "deferred_render", True), mock.patch.object(Panel, "deferred_render", True):
            self.test_device_detail_renders_fully()


class DeviceDetailCustomFieldsCollapseAndExpandButton(CollapseAllButtonTestCase):
    """Integration tests for the Custom Fields panel's Collapse/Expand button on the Device detail page."""

    TOGGLE_ALL_BUTTON_SELECTOR = '[data-nb-toggle="collapse-all"][data-nb-target*="custom_fields_False"]'
    GROUP_ROW_SELECTOR = '[class*="collapseme-custom_fields_False-"]'
    GROUP_TOGGLE_SELECTOR = '[data-bs-toggle="collapse"][data-bs-target*="collapseme-custom_fields_False-"]'

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.device = create_test_device("Device 1")

        device_content_type = ContentType.objects.get_for_model(Device)
        CustomField.objects.filter(content_types=device_content_type).delete()

        for index, grouping in enumerate(("Group A", "Group B")):
            custom_field = CustomField.objects.create(
                type="text",
                label=f"Owner {grouping}",
                key=f"collapse_test_owner_{index}",
                grouping=grouping,
            )
            custom_field.content_types.set([device_content_type])
            self.device.cf[custom_field.key] = f"{grouping} owner"
        self.device.validated_save()

    def tearDown(self):
        self.logout()
        super().tearDown()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _visit_device_detail(self):
        self.browser.visit(self.live_server_url + reverse("dcim:device", kwargs={"pk": self.device.pk}))
        self.browser.is_element_present_by_css(self.GROUP_ROW_SELECTOR, wait_time=5)

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_default_custom_fields_panel_is_fully_expanded(self):
        """Default Custom Fields panel should show all groups expanded"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_default_collapse_all_button_text_is_collapse_all_groups(self):
        """Default state is fully expanded custom fields, so collapse all button should say 'Collapse All Groups'"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

    def test_collapse_all_button_collapses_all(self):
        """Collapse All Button must collapse every custom field group"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_expand_all_button_expands_all(self):
        """Expand All Button must expand every custom field group"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())
        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_button_changes_text_to_expand_all_groups_string_after_all_groups_are_collapsed(self):
        """Collapse All Button text must say 'Expand All Groups' when all custom field groups are collapsed"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        # Collapse 'em all down
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        # Check button
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

    def test_collapse_state_persists_after_revisit_to_page(self):
        """Collapse State must persist after page reload"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

        self.browser.reload()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_from_mixed_state_collapses_every_group(self):
        """Collapse All must collapse every group even when a reload restores a mixed state"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreaterEqual(self._get_group_count(), 2)

        self._click_collapse_all_button()
        self._expand_first_group()

        # Wait for the reopened group to render and persist before reloading, so the reload restores the intended mixed state rather than a uniform one.
        self.browser.is_element_present_by_css(f"{self.GROUP_ROW_SELECTOR}.show", wait_time=2)
        self.assertGreater(self._get_collapsed_row_count(), 0)

        self.browser.reload()
        self.assertGreater(self._get_expanded_row_count(), 0)

        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())


class DeviceDetailComputedFieldsCollapseAndExpandButton(CollapseAllButtonTestCase):
    """Integration tests for the Computed Fields panel's Collapse/Expand All button on the Device detail page."""

    # New-component (GroupedKeyValueTablePanel) selectors for the main-tab computed fields panel (body_id "computed_fields_False").
    TOGGLE_ALL_BUTTON_SELECTOR = '[data-nb-toggle="collapse-all"][data-nb-target*="computed_fields_False"]'
    GROUP_ROW_SELECTOR = '[class*="collapseme-computed_fields_False-"]'
    GROUP_TOGGLE_SELECTOR = '[data-bs-toggle="collapse"][data-bs-target*="collapseme-computed_fields_False-"]'

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.device = create_test_device("Device 1")

        # Start from a clean slate so only the two computed field groups created below render on the page.
        device_content_type = ContentType.objects.get_for_model(Device)
        CustomField.objects.filter(content_types=device_content_type).delete()
        ComputedField.objects.filter(content_type=device_content_type).delete()

        for index, grouping in enumerate(("Group A", "Group B")):
            ComputedField.objects.create(
                content_type=device_content_type,
                key=f"collapse_test_computed_{index}",
                label=f"Computed {grouping}",
                template="{{ obj.name }}",
                grouping=grouping,
            )

    def tearDown(self):
        self.logout()
        super().tearDown()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _visit_device_detail(self):
        self.browser.visit(self.live_server_url + reverse("dcim:device", kwargs={"pk": self.device.pk}))
        self.browser.is_element_present_by_css(self.GROUP_ROW_SELECTOR, wait_time=5)

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_default_computed_fields_panel_is_fully_expanded(self):
        """Default Computed Fields panel should show all groups expanded"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_default_collapse_all_button_text_is_collapse_all_groups(self):
        """Default state is fully expanded computed fields, so collapse all button should say 'Collapse All Groups'"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

    def test_collapse_all_button_collapses_all(self):
        """Collapse All Button must collapse every computed field group"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_expand_all_button_expands_all(self):
        """Expand All Button must expand every computed field group"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())
        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_button_changes_text_to_expand_all_groups_string_after_all_groups_are_collapsed(self):
        """Collapse All Button text must say 'Expand All Groups' when all computed field groups are collapsed"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        # Collapse 'em all down
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        # Check button
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

    def test_collapse_state_persists_after_revisit_to_page(self):
        """Collapse State must persist after page reload"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

        self.browser.reload()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_from_mixed_state_collapses_every_group(self):
        """Collapse All must collapse every group even when a reload restores a mixed state"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreaterEqual(self._get_group_count(), 2)

        self._click_collapse_all_button()
        self._expand_first_group()

        # Wait for the reopened group to render and persist before reloading, so the reload restores the intended mixed state rather than a uniform one.
        self.browser.is_element_present_by_css(f"{self.GROUP_ROW_SELECTOR}.show", wait_time=2)
        self.assertGreater(self._get_collapsed_row_count(), 0)

        self.browser.reload()
        self.assertGreater(self._get_expanded_row_count(), 0)

        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())


class DeviceDetailComputedFieldsAndCustomFieldsCollapseAndExpandButton(CollapseAllButtonTestCase):
    """Integration tests ensuring the Custom Fields and Computed Fields panels collapse independently of each other."""

    CUSTOM_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR = '[data-nb-toggle="collapse-all"][data-nb-target*="custom_fields_False"]'
    CUSTOM_FIELDS_GROUP_ROW_SELECTOR = '[class*="collapseme-custom_fields_False-"]'
    COMPUTED_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR = (
        '[data-nb-toggle="collapse-all"][data-nb-target*="computed_fields_False"]'
    )
    COMPUTED_FIELDS_GROUP_ROW_SELECTOR = '[class*="collapseme-computed_fields_False-"]'

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.device = create_test_device("Device 1")

        # Start from a clean slate so the page renders exactly the two custom field groups and two computed field groups created below.
        device_content_type = ContentType.objects.get_for_model(Device)
        CustomField.objects.filter(content_types=device_content_type).delete()
        ComputedField.objects.filter(content_type=device_content_type).delete()

        for index, grouping in enumerate(("Group A", "Group B")):
            custom_field = CustomField.objects.create(
                type="text",
                label=f"Owner {grouping}",
                key=f"collapse_test_owner_{index}",
                grouping=grouping,
            )
            custom_field.content_types.set([device_content_type])
            self.device.cf[custom_field.key] = f"{grouping} owner"
        self.device.validated_save()

        for index, grouping in enumerate(("Group A", "Group B")):
            ComputedField.objects.create(
                content_type=device_content_type,
                key=f"collapse_test_computed_{index}",
                label=f"Computed {grouping}",
                template="{{ obj.name }}",
                grouping=grouping,
            )

    def tearDown(self):
        self.logout()
        super().tearDown()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _visit_device_detail(self):
        self.browser.visit(self.live_server_url + reverse("dcim:device", kwargs={"pk": self.device.pk}))
        self.browser.is_element_present_by_css(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR, wait_time=5)
        self.browser.is_element_present_by_css(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR, wait_time=5)

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_collapsing_or_expanding_computed_fields_does_not_affect_custom_fields(self):
        """Toggling the Computed Fields panel must never collapse or expand the Custom Fields panel"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        # Collapse
        self._click_collapse_all_button(self.COMPUTED_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR)
        self.assertEqual(
            self._get_collapsed_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
        )
        self.assertEqual(
            self._get_expanded_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
        )

        # Expand
        self._click_collapse_all_button(self.COMPUTED_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR)
        self.assertEqual(
            self._get_expanded_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
        )
        self.assertEqual(
            self._get_expanded_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
        )

        # Collapse
        self._click_collapse_all_button(self.COMPUTED_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR)
        self.assertEqual(
            self._get_collapsed_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
        )
        self.assertEqual(
            self._get_expanded_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
        )

    def test_collapsing_or_expanding_custom_fields_does_not_affect_computed_fields(self):
        """Toggling the Custom Fields panel must never collapse or expand the Computed Fields panel"""
        self._visit_device_detail()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        # Collapse
        self._click_collapse_all_button(self.CUSTOM_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR)
        self.assertEqual(
            self._get_collapsed_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
        )
        self.assertEqual(
            self._get_expanded_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
        )

        # Expand
        self._click_collapse_all_button(self.CUSTOM_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR)
        self.assertEqual(
            self._get_expanded_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
        )
        self.assertEqual(
            self._get_expanded_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
        )

        # Collapse
        self._click_collapse_all_button(self.CUSTOM_FIELDS_TOGGLE_ALL_BUTTON_SELECTOR)
        self.assertEqual(
            self._get_collapsed_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.CUSTOM_FIELDS_GROUP_ROW_SELECTOR),
        )
        self.assertEqual(
            self._get_expanded_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
            self._get_total_row_count(self.COMPUTED_FIELDS_GROUP_ROW_SELECTOR),
        )
