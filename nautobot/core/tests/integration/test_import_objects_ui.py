from nautobot.core.testing.integration import SeleniumTestCase


class ImportObjectsUITestCase(SeleniumTestCase):
    """Integration tests for the 'Import Objects' system Job's UI."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_import_objects_ui_population(self):
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("Organization").click()
        self.browser.links.find_by_partial_text("Locations").click()
        self.browser.find_by_id("actions-dropdown").click()
        self.browser.find_by_id("import-button").click()

        # Make sure the table of fields for a Location import is populated via a few spot checks
        self.assertTrue(self.browser.is_text_present("shipping_address", wait_time=10))
        self.assertTrue(self.browser.is_text_present("Local facility ID or description"))

        # Clear the content-type selection
        clear_button = self.browser.find_by_xpath(
            "//span[@id='select2-id_content_type-container']//span[@class='select2-selection__clear']"
        )
        clear_button.click()

        # Table of fields should be cleared
        self.assertFalse(self.browser.is_text_present("shipping_address", wait_time=1))
        self.assertFalse(self.browser.is_text_present("Local facility ID or description", wait_time=1))

        # Select a different valid content-type
        self.browser.find_by_xpath("//li[contains(text(), 'circuits | circuit termination')]", wait_time=10).click()

        self.assertTrue(self.browser.is_text_present("upstream_speed", wait_time=10))
        self.assertTrue(self.browser.is_text_present("Upstream speed, if different from port speed"))
