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

    def create1x2BreakoutCable(self):
        local_device = create_test_device("Breakout Cable Local Device")
        remote_device = create_test_device("Breakout Cable Remote Device")

        interface_status = Status.objects.get_for_model(Interface).first()
        cable_connected = Status.objects.get_for_model(Cable).get(name="Connected")

        local_interface = Interface.objects.create(
            device=local_device,
            name="Local Interface 1",
            type=InterfaceTypeChoices.TYPE_10GE_FIXED,
            status=interface_status,
        )

        remote_interfaces = [
            Interface.objects.create(device=remote_device, name="Remote Interface 1", status=interface_status),
            Interface.objects.create(device=remote_device, name="Remote Interface 2", status=interface_status),
        ]

        breakout_type = CableType.objects.create(
            name="1x2 Breakout Cable", a_connectors=1, b_connectors=2, total_lanes=2
        )

        cable = Cable(
            termination_a=local_interface,
            termination_b=remote_interfaces[0],
            cable_type=breakout_type,
            status=cable_connected,
        )
        cable.save()
        cable.add_termination(remote_interfaces[1], "B", connector=2)

        local_interface_children = [
            Interface.objects.create(
                device=local_device,
                name="Local Interface 1/1",
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=interface_status,
                parent_interface=local_interface,
                breakout_position=1,
            ),
            Interface.objects.create(
                device=local_device,
                name="Local Interface 1/2",
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=interface_status,
                parent_interface=local_interface,
                breakout_position=2,
            ),
        ]

        return cable, local_device, local_interface, local_interface_children, remote_device, remote_interfaces

    def test_device_detail_view_interface_tab_colors_change_after_cable_toggled_from_connected_to_planned(self):
        _, local_device, local_interface, local_interface_children, _, _ = self.create1x2BreakoutCable()

        self.browser.visit(
            self.live_server_url + reverse("dcim:device_interfaces", kwargs={"pk": local_device.pk})
        )

        self.assertTrue(
            self.browser.is_element_present_by_css(
                f'tr[data-name="{local_interface.name}"].table-success', wait_time=10
            ),
            "Parent interface row did not start green",
        )
        for child in local_interface_children:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr[data-name="{child.name}"].table-success', wait_time=10
                ),
                f"{child.name} row did not start green",
            )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr[data-name="{local_interface.name}"] a.cable-toggle')
            )
        )
        self.browser.driver.execute_script("arguments[0].click();", toggle)

        self.assertTrue(
            self.browser.is_element_present_by_css(
                f'tr[data-name="{local_interface.name}"].table-info', wait_time=10
            ),
            "Parent interface row did not turn blue after toggling its cable to Planned",
        )
        for child in local_interface_children:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr[data-name="{child.name}"].table-info', wait_time=10
                ),
                f"{child.name} row did not turn blue after toggling the parent cable",
            )
            self.assertFalse(
                self.browser.is_element_present_by_css(
                    f'tr[data-name="{child.name}"].table-success', wait_time=1
                ),
                f"{child.name} row is still green after toggling the parent cable",
            )

    def test_list_interfaces_view_colors_change_after_cable_toggled_from_connected_to_planned(self):
        _, _, local_interface, local_interface_children, _, remote_interfaces = self.create1x2BreakoutCable()

        self.browser.visit(self.live_server_url + reverse("dcim:interface_list"))

        cable_colored_interfaces = [local_interface, *local_interface_children, *remote_interfaces]
        for interface in cable_colored_interfaces:
            self.assertTrue(
                self.browser.is_element_present_by_css(
                    f'tr:has(input[name="pk"][value="{interface.pk}"]).table-success', wait_time=10
                ),
                f"{interface.name} row did not start green",
            )

        toggle = WebDriverWait(self.browser.driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f'tr:has(input[name="pk"][value="{local_interface.pk}"]) a.cable-toggle')
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