from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase


class RadioProfileTestCase(SeleniumTestCase):
    """
    Perform set of Radio Profile tests using Selenium.
    """

    def test_radio_profile_bulk_edit(self):
        """
        This test goes through the process of creating a radio profile and performing bulk edit.
        """
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        # Create a radio profile
        self.click_navbar_entry("Wireless", "Radio Profiles")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("wireless:radioprofile_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("wireless:radioprofile_add"))
        self.browser.fill("name", "Test Radio Profile 1")
        self.browser.find_by_xpath("//select[@id='id_regulatory_domain']/option[@value='PL']").click()
        self.click_edit_form_create_button()

        # Test bulk edit
        self.click_navbar_entry("Wireless", "Radio Profiles")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("wireless:radioprofile_list"))
        self.browser.find_by_xpath("//input[@name='pk']").click()
        bulk_edit_url = reverse("wireless:radioprofile_bulk_edit")
        self.browser.find_by_xpath(f"//button[@formaction='{bulk_edit_url}']").click()

        # Submit bulk edit form without any changes
        self.browser.find_by_xpath("//button[@name='_apply']", wait_time=5).click()

        self.assertEqual(self.browser.url, self.live_server_url + reverse("wireless:radioprofile_list"))
        self.assertTrue(self.browser.is_text_present("Updated 1 radio profiles", wait_time=5))
