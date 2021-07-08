from nautobot.utilities.testing.integration import SeleniumTestCase


class HomeTestCase(SeleniumTestCase):
    """Integration tests against the home page."""

    fixtures = ["user-data.json"]  # bob/bob
    homepage_layout = [
        {
                "Organization": [
                "Sites",
                "Tenants"
            ],
            "Power": [
                "Power Feeds",
                "Power Panels",
            ]
        },
        {
            "Circuits": [
                "Providers",
                "Circuits",
            ],
            "Virtualization": [
                "Clusters",
                "Virtual Machines",
            ]
        }
    ]

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_login(self):
        """
        Perform a UI login.
        """
        self.load_page(self.live_server_url)
        # Wait for the page to render and make sure we got a body.
        self.selenium.wait_for_html("body")

    def test_homepage_panels(self):
        """
        Render homepage panels.
        """
        self.load_page(self.live_server_url)
        for column in self.homepage_layout:
