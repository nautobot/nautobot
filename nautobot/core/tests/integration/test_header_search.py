from django.urls import reverse
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.core.utils import lookup


class HomeTestCase(SeleniumTestCase):
    """Integration tests against the global search bar."""

    SEARCH_POPUP_XPATH = "//div[@id='search_popup']"

    def get_element(self, xpath):
        # Wait for given element to appear in the DOM, and then return it by given `xpath` argument.
        self.assertTrue(self.browser.is_element_present_by_xpath(xpath, wait_time=10))
        return self.browser.find_by_xpath(xpath)

    def get_search_popup_content_type_badge(self):
        return self.get_element(f"{self.SEARCH_POPUP_XPATH}//span[@class='badge border' and @data-nb-link]")

    def get_search_popup_input(self):
        return self.get_element(f"{self.SEARCH_POPUP_XPATH}//input[@name='q' and @type='search']")

    def get_search_popup_results(self):
        return self.get_element(f"{self.SEARCH_POPUP_XPATH}//form//following-sibling::div/ul/li")

    def open_search_popup(self):
        # Wait for header search input to load into DOM and trigger search popup by clicking on header search input
        header_search_input = self.get_element("//form[@id='header_search']//input[@name='q' and @type='search']")
        header_search_input.click()

        # Wait for search popup to initialize
        self.assertTrue(self.browser.is_element_present_by_xpath(self.SEARCH_POPUP_XPATH, wait_time=10))

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def test_header_global_search(self):
        self.browser.visit(self.live_server_url)
        self.open_search_popup()

        # Type "test" phrase in the search popup input
        phrase = "test"
        input_field = self.get_search_popup_input()
        input_field.fill(phrase)
        input_field.type(Keys.ENTER)

        # Expect page to have changed, URL to be that of global search page with search phrase as `q` query param
        self.assertTrue(
            self.browser.is_element_present_by_xpath("//div[@id='page-title']/h1[normalize-space()='Search']")
        )
        self.assertEqual(self.browser.url, f"{self.live_server_url}{reverse('search')}?q={phrase}")

    def test_header_search_model_exact_match(self):
        self.browser.visit(self.live_server_url)
        self.open_search_popup()

        # Type "in locations" phrase in the search popup input
        input_field = self.get_search_popup_input()
        input_field.fill("in locations ")

        # Assert that `Location` content type badge is rendered, and that its link and has text are valid
        url = reverse(lookup.get_route_for_model("dcim.location", "list"))
        badge = self.get_search_popup_content_type_badge()
        self.assertTrue(badge["data-nb-link"], url)
        self.assertEqual(badge.text, "in: Locations\nRemove")  # `\nRemove` is a badge "X" button text

        # Type "test" phrase and press Enter key
        phrase = "test"
        input_field.fill(phrase)
        input_field.type(Keys.ENTER)

        # Expect page to have changed, URL to be that of search content type badge with search phrase as `q` query param
        self.assertTrue(
            self.browser.is_element_present_by_xpath("//div[@id='page-title']/h1[normalize-space()='Locations']")
        )
        self.assertEqual(self.browser.url, f"{self.live_server_url}{url}?q={phrase}")

    def test_header_search_typeahead(self):
        """
        Render header search.
        """
        self.browser.visit(self.live_server_url)
        self.open_search_popup()

        # Type "in" phrase in the search popup input
        input_field = self.get_search_popup_input()
        input_field.fill("in")

        # Expect 3 typeahead suggestions to be rendered to confirm that "in" phrase in fact enables search results
        results = self.get_search_popup_results()
        self.assertEqual(len(results), 3)

        # Type "in de" phrase in the search popup input
        input_field.fill("in de")

        # Again, expect 3 typeahead suggestions to be rendered (likely different than previously but it doesn't matter)
        results = self.get_search_popup_results()
        self.assertEqual(len(results), 3)

        # Click on the first typeahead suggestion, it is expected to be "in: Devices"
        results.first.click()

        # Assert that `Device` content type badge is rendered, and that its link and has text are valid
        url = reverse(lookup.get_route_for_model("dcim.device", "list"))
        badge = self.get_search_popup_content_type_badge()
        self.assertTrue(badge["data-nb-link"], url)
        self.assertEqual(badge.text, "in: Devices\nRemove")  # `\nRemove` is a badge "X" button text

        # Type "test" phrase and press Enter key
        phrase = "test"
        input_field.fill(phrase)
        input_field.type(Keys.ENTER)

        # Expect page to have changed, URL to be that of search content type badge with search phrase as `q` query param
        self.assertTrue(
            self.browser.is_element_present_by_xpath("//div[@id='page-title']/h1[normalize-space()='Devices']")
        )
        self.assertEqual(self.browser.url, f"{self.live_server_url}{url}?q={phrase}")
