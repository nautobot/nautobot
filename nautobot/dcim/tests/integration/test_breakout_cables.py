from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Cable, CableType, Interface
from nautobot.extras.models import Status
from nautobot.extras.tests.integration import create_test_device


class BreakoutCablesTestCase(SeleniumTestCase):
    """Breakout cable integration tests."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def create_1x2_breakout_cable(self):
        spine_device = create_test_device("Breakout Cable Spine Device")
        leaf_device = create_test_device("Breakout Cable Leaf Device")

        status_active = Status.objects.get_for_model(Interface).get(name="Active")
        status_connected = Status.objects.get_for_model(Cable).get(name="Connected")

        spine_interface = Interface.objects.create(
            device=spine_device,
            name="Spine Interface 1",
            type=InterfaceTypeChoices.TYPE_10GE_FIXED,
            status=status_active,
        )

        leaf_interfaces = [
            Interface.objects.create(device=leaf_device, name="Leaf Interface 1", status=status_active),
            Interface.objects.create(device=leaf_device, name="Leaf Interface 2", status=status_active),
        ]

        breakout_type = CableType.objects.create(
            name="1x2 Breakout Cable", a_connectors=1, b_connectors=2, total_lanes=2
        )

        cable = Cable(
            termination_a=spine_interface,
            termination_b=leaf_interfaces[0],
            cable_type=breakout_type,
            status=status_connected,
        )
        cable.save()
        cable.add_termination(leaf_interfaces[1], "B", connector=2)

        spine_interface_children = [
            Interface.objects.create(
                device=spine_device,
                name="Spine Interface 1/1",
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=status_active,
                parent_interface=spine_interface,
                breakout_position=1,
            ),
            Interface.objects.create(
                device=spine_device,
                name="Spine Interface 1/2",
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=status_active,
                parent_interface=spine_interface,
                breakout_position=2,
            ),
        ]

        return cable, spine_device, spine_interface, spine_interface_children, leaf_device, leaf_interfaces

    def test_device_detail_view_interface_tab_colors_change_after_cable_toggled_from_connected_to_planned(self):
        _, spine_device, spine_interface, spine_interface_children, _, _ = self.create_1x2_breakout_cable()

        self.browser.visit(self.live_server_url + reverse("dcim:device_interfaces", kwargs={"pk": spine_device.pk}))

        self.assertTrue(
            self.browser.is_element_present_by_css(
                f'tr[data-name="{spine_interface.name}"].table-success', wait_time=10
            ),
            "Parent interface row did not start green",
        )
        for child in spine_interface_children:
            self.assertTrue(
                self.browser.is_element_present_by_css(f'tr[data-name="{child.name}"].table-success', wait_time=10),
                f"{child.name} row did not start green",
            )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr[data-name="{spine_interface.name}"] a.cable-toggle')
            )
        )
        self.browser.driver.execute_script("arguments[0].click();", toggle)

        self.assertTrue(
            self.browser.is_element_present_by_css(f'tr[data-name="{spine_interface.name}"].table-info', wait_time=10),
            "Parent interface row did not turn blue after toggling its cable to Planned",
        )
        for child in spine_interface_children:
            self.assertTrue(
                self.browser.is_element_present_by_css(f'tr[data-name="{child.name}"].table-info', wait_time=10),
                f"{child.name} row did not turn blue after toggling the parent cable",
            )
            self.assertFalse(
                self.browser.is_element_present_by_css(f'tr[data-name="{child.name}"].table-success', wait_time=1),
                f"{child.name} row is still green after toggling the parent cable",
            )

    def test_device_detail_view_interface_tab_icons_change_after_cable_toggled_from_connected_to_planned(self):
        _, _, _, _, leaf_device, leaf_interfaces = self.create_1x2_breakout_cable()

        self.browser.visit(self.live_server_url + reverse("dcim:device_interfaces", kwargs={"pk": leaf_device.pk}))

        for interface in leaf_interfaces:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr[data-name="{interface.name}"] a.cable-toggle span.mdi-lan-pending', wait_time=10
                ),
                f"{interface.name} did not start with the 'mark planned' icon",
            )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr[data-name="{leaf_interfaces[0].name}"] a.cable-toggle')
            )
        )
        self.browser.driver.execute_script("arguments[0].click();", toggle)

        for interface in leaf_interfaces:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr[data-name="{interface.name}"] a.cable-toggle span.mdi-lan-connect', wait_time=10
                ),
                f"{interface.name} icon did not change to the 'mark connected' icon after toggling the cable",
            )

    def test_list_interfaces_view_colors_change_after_cable_toggled_from_connected_to_planned(self):
        _, _, spine_interface, spine_interface_children, _, leaf_interfaces = self.create_1x2_breakout_cable()

        self.browser.visit(self.live_server_url + reverse("dcim:interface_list"))

        cable_colored_interfaces = [spine_interface, *spine_interface_children, *leaf_interfaces]
        for interface in cable_colored_interfaces:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr:has(input[name="pk"][value="{interface.pk}"]).table-success', wait_time=10
                ),
                f"{interface.name} row did not start green",
            )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr:has(input[name="pk"][value="{spine_interface.pk}"]) a.cable-toggle')
            )
        )
        self.browser.driver.execute_script("arguments[0].click();", toggle)

        for interface in cable_colored_interfaces:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr:has(input[name="pk"][value="{interface.pk}"]).table-info', wait_time=10
                ),
                f"{interface.name} row did not turn blue after toggling the cable",
            )
            self.assertFalse(
                self.browser.is_element_present_by_css(
                    f'tr:has(input[name="pk"][value="{interface.pk}"]).table-success', wait_time=1
                ),
                f"{interface.name} row is still green after toggling the cable",
            )

    def test_list_interfaces_view_unrelated_interface_color_unchanged_when_cable_toggled(self):
        _, spine_device, spine_interface, _, _, _ = self.create_1x2_breakout_cable()

        status_active = Status.objects.get_for_model(Interface).get(name="Active")
        unrelated_interface = Interface.objects.create(
            device=spine_device,
            name="Unrelated Interface",
            type=InterfaceTypeChoices.TYPE_10GE_FIXED,
            status=status_active,
        )

        self.browser.visit(self.live_server_url + reverse("dcim:interface_list"))

        unrelated_row = f'tr:has(input[name="pk"][value="{unrelated_interface.pk}"])'

        self.assertTrue(
            self.browser.is_element_present_by_css(unrelated_row, wait_time=10),
            "Unrelated interface row was not rendered",
        )
        self.assertFalse(
            self.browser.is_element_present_by_css(f"{unrelated_row}.table-success", wait_time=1),
            "Unrelated interface row should not start green",
        )
        self.assertFalse(
            self.browser.is_element_present_by_css(f"{unrelated_row}.table-info", wait_time=1),
            "Unrelated interface row should not start blue",
        )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr:has(input[name="pk"][value="{spine_interface.pk}"]) a.cable-toggle')
            )
        )
        self.browser.driver.execute_script("arguments[0].click();", toggle)

        self.assertTrue(
            self.browser.is_element_present_by_css(
                f'tr:has(input[name="pk"][value="{spine_interface.pk}"]).table-info', wait_time=10
            ),
            "Cable row did not turn blue after toggling (the JS update did not run)",
        )
        self.assertFalse(
            self.browser.is_element_present_by_css(f"{unrelated_row}.table-info", wait_time=1),
            "Unrelated interface row incorrectly turned blue after toggling the cable",
        )
        self.assertFalse(
            self.browser.is_element_present_by_css(f"{unrelated_row}.table-success", wait_time=1),
            "Unrelated interface row incorrectly turned green after toggling the cable",
        )

    def test_list_interfaces_view_icons_change_after_cable_toggled_from_connected_to_planned(self):
        _, _, spine_interface, _, _, leaf_interfaces = self.create_1x2_breakout_cable()

        self.browser.visit(self.live_server_url + reverse("dcim:interface_list"))

        cable_terminations = [spine_interface, *leaf_interfaces]
        for interface in cable_terminations:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr:has(input[name="pk"][value="{interface.pk}"]) a.cable-toggle span.mdi-lan-pending',
                    wait_time=10,
                ),
                f"{interface.name} did not start with the 'mark planned' icon",
            )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr:has(input[name="pk"][value="{spine_interface.pk}"]) a.cable-toggle')
            )
        )
        self.browser.driver.execute_script("arguments[0].click();", toggle)

        for interface in cable_terminations:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr:has(input[name="pk"][value="{interface.pk}"]) a.cable-toggle span.mdi-lan-connect',
                    wait_time=10,
                ),
                f"{interface.name} icon did not change to the 'mark connected' icon after toggling the cable",
            )
