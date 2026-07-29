from nautobot.circuits.models import Circuit, Provider
from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, PowerFeed, PowerPanel
from nautobot.tenancy.models import Tenant


class HomeTestCase(SeleniumTestCase):
    """Integration tests against the home page."""

    layout = {
        "Organization": {
            "Locations": {"model": Location, "permission": "dcim.view_location"},
            "Tenant": {"model": Tenant, "permission": "tenancy.view_tenant"},
        },
        "Power": {
            "Power Feeds": {"model": PowerFeed, "permission": "dcim.view_powerfeed"},
            "Power Panel": {"model": PowerPanel, "permission": "dcim.view_powerpanel"},
        },
        "Circuits": {
            "Providers": {"model": Provider, "permission": "circuits.view_provider"},
            "Circuits": {"model": Circuit, "permission": "circuits.view_circuit"},
        },
    }

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)
        self.logged_in = True

    def get_panel_permissions(self, panel_details):
        permissions = []
        for panel in panel_details.values():
            permissions.append(panel["permission"])
        return permissions

    def test_homepage_render(self):
        """
        Render homepage with app defined objects.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        self.browser.visit(self.live_server_url)

        columns_html = self.browser.find_by_xpath("//div[@id='draggable-homepage-panels']")
        for panel_name, panel_details in self.layout.items():
            columns_html.first.find_by_xpath(f".//strong[text()='{panel_name}']")
            for item_name, _ in panel_details.items():
                columns_html.first.find_by_xpath(f".//a[contains(text(), '{item_name}')]")

    def test_homepage_render_counters(self):
        """
        Ensure object counters are correct.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        self.browser.visit(self.live_server_url)

        columns_html = self.browser.find_by_xpath("//div[@id='draggable-homepage-panels']")
        for panel_name, panel_details in self.layout.items():
            columns_html.first.find_by_xpath(f".//strong[text()='{panel_name}']")
            for item_name, item_details in panel_details.items():
                item_html = columns_html.first.find_by_xpath(f".//a[contains(text(), '{item_name}')]")
                if item_details.get("model"):
                    counter = item_details["model"].objects.count()
                    counter_html = int(item_html.find_by_xpath("./../../span").first.html)
                    self.assertEqual(counter, counter_html)

    def test_homepage_render_with_limit_permissions(self):
        """
        Render homepage with limited permissions and restricted UI.
        This restricts the user to be able to view ONLY locations and circuits.
        It then checks the UI for these restrictions.
        """
        self.add_permissions("dcim.view_location")
        self.add_permissions("circuits.view_circuit")
        user_permissions = self.user.get_all_permissions()

        self.browser.visit(self.live_server_url)

        for panel_index, (panel_name, panel_details) in enumerate(self.layout.items()):
            if any(perm in self.get_panel_permissions(panel_details) for perm in user_permissions):
                for item_name, item_details in panel_details.items():
                    panel_element_to_search = self.browser.find_by_xpath(
                        f"//div[@id='draggable-homepage-panels']"
                        f"/div[@class='col-xxl-3 col-xl-4 col-md-6 ms-auto nb-panel-group order-xl-0 order-md-{panel_index // 2}']"
                        f"/div[@class='card nb-draggable']"
                        f"/div[@class='card-header nb-draggable-handle']"
                        f"/strong[contains(text(), '{panel_name}')]"
                        f"/../.."
                        f"/ul[@class='list-group collapse overflow-y-auto show']"
                    )
                    links = panel_element_to_search.links.find_by_text(item_name)
                    if item_details["permission"] in user_permissions:
                        self.assertEqual(len(links), 1)
                    else:
                        self.assertEqual(len(links), 0)
            else:
                panel = self.browser.find_by_xpath(
                    f"//div[@class='card-header nb-draggable-handle']/strong[text()='{panel_name}']"
                )
                self.assertEqual(len(panel), 0)

    def test_homepage_layout_panels_collapse(self):
        """
        Confirm that homepage layout panels are collapsible and that their collapsed state is saved in user preferences.
        """
        self.add_permissions("dcim.view_location")
        self.add_permissions("circuits.view_circuit")

        self.browser.visit(self.live_server_url)

        organization_panel_xpath = "//div[contains(@class, 'nb-panel-group')][1]/div[@id='organization']"
        circuits_panel_xpath = "//div[contains(@class, 'nb-panel-group')][2]/div[@id='circuits']"
        collapsed_xpath = "/ul[not(contains(@class, 'show'))]"
        expanded_xpath = "/ul[contains(@class, 'show')]"

        # Assert that all panels are expanded by default.
        self.assertTrue(
            self.browser.is_element_present_by_xpath(organization_panel_xpath + expanded_xpath, wait_time=10)
        )
        self.assertTrue(self.browser.is_element_present_by_xpath(circuits_panel_xpath + expanded_xpath, wait_time=10))

        # Collapse the Circuits panel.
        circuits_panel_button = self.browser.find_by_xpath(f"{circuits_panel_xpath}//span[@data-bs-toggle='collapse']")
        circuits_panel_button.click()
        # Assert that the Circuits panel is now collapsed.
        self.assertTrue(self.browser.is_element_present_by_xpath(circuits_panel_xpath + collapsed_xpath, wait_time=10))

        # Reload the page to make sure that user preferences with panels collapsed state were correctly saved.
        self.browser.reload()

        # Assert that the Circuits panel stays collapsed.
        self.assertTrue(
            self.browser.is_element_present_by_xpath(organization_panel_xpath + expanded_xpath, wait_time=10)
        )
        self.assertTrue(self.browser.is_element_present_by_xpath(circuits_panel_xpath + collapsed_xpath, wait_time=10))
