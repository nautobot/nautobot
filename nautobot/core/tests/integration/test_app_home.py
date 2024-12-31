from nautobot.circuits.models import Circuit, Provider
from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, PowerFeed, PowerPanel
from nautobot.tenancy.models import Tenant

from example_app.models import ExampleModel


class AppHomeTestCase(SeleniumTestCase):
    """Integration test the Example App homepage extensions."""

    layout = {
        "Organization": {
            "Locations": {"model": Location, "permission": "dcim.view_location"},
            "Example Models": {"model": ExampleModel, "permission": "example_app.view_examplemodel"},
            "Tenants": {"model": Tenant, "permission": "tenancy.view_tenant"},
        },
        "Example App Standard Panel": {
            "Example App Custom Item": {"permission": "example_app.view_examplemodel"},
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

    custom_panel_examplemodel = {
        "name": "Example App Custom Panel",
        "items": [
            "Example 1",
            "Example 2",
            "Example 3",
        ],
    }

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_homepage_render(self):
        """
        Render homepage with app defined objects.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        self.browser.visit(self.live_server_url)

        columns_html = self.browser.find_by_css("div[class='homepage_column']")
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

        columns_html = self.browser.find_by_css("div[class='homepage_column']")
        for panel_name, panel_details in self.layout.items():
            columns_html.first.find_by_xpath(f".//strong[text()='{panel_name}']")
            for item_name, item_details in panel_details.items():
                item_html = columns_html.first.find_by_xpath(f".//a[contains(text(), '{item_name}')]")
                self.assertTrue(item_html)
                if item_details.get("model"):
                    counter = item_details["model"].objects.count()
                    counter_html = int(item_html.find_by_xpath("./../../span")["innerHTML"])
                    self.assertEqual(counter, counter_html)

    def test_homepage_render_no_permissions(self):
        """
        Render homepage with no permissions.
        """
        self.browser.visit(self.live_server_url)

        columns_html = self.browser.find_by_css("div[class='homepage_column']")
        for panel_name, panel_details in self.layout.items():
            columns_html.first.find_by_xpath(f".//strong[text()='{panel_name}']")
            for item_name, _ in panel_details.items():
                item_html = columns_html.first.find_by_xpath(f".//h4[contains(text(), '{item_name}')]")
                # Assert Panel items without permissions are not shown in DOM
                self.assertFalse(item_html)

    def test_examplemodel_custom_panel(self):
        """
        Render custom panel.
        """
        self.user.is_superuser = True
        self.user.save()

        self.browser.visit(self.live_server_url)

        columns_html = self.browser.find_by_css("div[class='homepage_column']")
        columns_html.first.find_by_xpath(f".//strong[text()='{self.custom_panel_examplemodel['name']}']")

        for item_name in self.custom_panel_examplemodel["items"]:
            columns_html.first.find_by_xpath(f".//a[contains(text(), '{item_name}')]")

    def test_homepage_render_limit_permissions(self):
        """
        Render homepage with limited permissions.
        """
        self.add_permissions("dcim.view_location")
        self.add_permissions("circuits.view_circuit")
        self.add_permissions("example_app.view_examplemodel")
        user_permissions = self.user.get_all_permissions()

        self.browser.visit(self.live_server_url)

        columns_html = self.browser.find_by_css("div[class='homepage_column']")
        for panel_name, panel_details in self.layout.items():
            columns_html.first.find_by_xpath(f".//*[contains(text(), '{panel_name}')]")
            for item_name, item_details in panel_details.items():
                if item_details["permission"] in user_permissions:
                    item_html = columns_html.first.find_by_xpath(f".//a[contains(text(), '{item_name}')]")
                    if item_details.get("model"):
                        counter = item_details["model"].objects.count()
                        counter_html = int(item_html.find_by_xpath("./../../span")["innerHTML"])
                        self.assertEqual(counter, counter_html)
                else:
                    item_html = columns_html.first.find_by_xpath(f".//h4[contains(text(), '{item_name}')]")
                    # Assert Layout items without permission is not visible in DOM
                    self.assertFalse(item_html)
