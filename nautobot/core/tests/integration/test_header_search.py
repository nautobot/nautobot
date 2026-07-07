from django.urls import reverse
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.core.utils import lookup
from nautobot.dcim.factory import LocationTypeFactory
from nautobot.dcim.models.locations import Location, LocationType
from nautobot.extras.models import Status


class HeaderSearchTestCase(SeleniumTestCase):
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
        return self.get_element(f"{self.SEARCH_POPUP_XPATH}//form//following-sibling::div//*[parent::ul|parent::tbody]")

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
        Render search typeahead results.
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

        # Assert that the first typeahead suggestion is "in: Devices", and click it
        self.assertTrue(results.first.text, "in: Devices")
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

    def test_header_search_live_search(self):
        """
        Render live search results.
        """
        if not LocationType.objects.exists():
            LocationTypeFactory.create()
        location_type = LocationType.objects.first()
        status = Status.objects.get_for_model(Location).first()
        location = Location.objects.create(name="My Test Location", location_type=location_type, status=status)

        self.browser.visit(self.live_server_url)
        self.open_search_popup()

        # Type "in: locations " phrase in the search popup input to narrow down the search scope only to Locations model.
        input_field = self.get_search_popup_input()
        input_field.fill("in: locations ")

        # Type a single character phrase in the search popup input, and expect nothing to happen just yet.
        spinner = self.get_element(
            f"{self.SEARCH_POPUP_XPATH}//form//following-sibling::div/div[contains(@class, 'htmx-indicator')]"
        )
        self.assertTrue(spinner.is_not_visible())
        input_field.fill(location.name[:1])
        self.assertTrue(spinner.is_not_visible())

        # Type a location name phrase in the search popup input, and expect live search to be triggered.
        self.assertTrue(spinner.is_not_visible())
        input_field.fill(location.name)
        self.assertTrue(spinner.is_visible())

        # There should be exactly one live search result in this case.
        results = self.get_search_popup_results()
        self.assertEqual(len(results), 1)

        # Assert that the first live search result name is the location name, and click it.
        self.assertEqual(results.first.find_by_tag("td").first.text, location.name)
        self.browser.execute_script(
            "arguments[0].click();", results.first._element
        )  # Standard `.click()` does not work here

        # Expect page to have changed to the location detail view.
        page_title_xpath = f"//div[@id='page-title']/h1//span[normalize-space()='{location.name}']"
        self.assertTrue(self.browser.is_element_present_by_xpath(page_title_xpath, wait_time=10))
        self.assertEqual(
            self.browser.url, f"{self.live_server_url}{reverse('dcim:location', kwargs={'pk': location.pk})}"
        )

    def test_header_search_keyboard_selection(self):
        """
        Confirm that selecting result items is possible with up and down arrow keys.
        """
        if not LocationType.objects.exists():
            LocationTypeFactory.create()
        location_type = LocationType.objects.first()
        status = Status.objects.get_for_model(Location).first()
        for i in range(0, 20):
            Location.objects.create(name=f"Location #{i}", location_type=location_type, status=status)

        self.browser.visit(self.live_server_url)
        self.open_search_popup()

        # Type "in: locations " phrase in the search popup input to narrow down the search scope only to Locations model.
        input_field = self.get_search_popup_input()
        input_field.fill("in: locations ")

        # Type a "lo" phrase in the search popup input.
        input_field.fill("lo")

        # There should always be no more than ten live results displayed at a time (+1 for the "More..." button).
        results = self.get_search_popup_results()
        self.assertLessEqual(len(results), 11)

        # Assert that none of the live search results is currently selected.
        for result in results:
            self.assertFalse(result.has_class("active"))

        # Press arrow down key and assert that the first result is now selected.
        input_field.type(Keys.ARROW_DOWN)
        for index, result in enumerate(results):
            self.assertIs(result.has_class("active"), index == 0)

        # Press arrow down key twice and assert that the third result is now selected.
        input_field.type(Keys.ARROW_DOWN)
        input_field.type(Keys.ARROW_DOWN)
        for index, result in enumerate(results):
            self.assertIs(result.has_class("active"), index == 2)

        # Press arrow up key thrice and assert that the "More..." button is now selected.
        input_field.type(Keys.ARROW_UP)
        input_field.type(Keys.ARROW_UP)
        input_field.type(Keys.ARROW_UP)
        for index, result in enumerate(results):
            if result.has_class("active"):
                anchor_link = result.find_by_tag("a").first
                self.assertEqual(index, 10)
                self.assertEqual(anchor_link.href, "/dcim/locations/?q=lo")
                self.assertEqual(anchor_link.text, "More... (10)")

        # Press arrow up key once and assert that the last (tenth) result is now selected.
        input_field.type(Keys.ARROW_UP)
        for index, result in enumerate(results):
            self.assertIs(result.has_class("active"), index == 9)

        # Get the selected result attributes relevant for the next assertion.
        selected_result = next(result for result in results if result.has_class("active"))
        selected_result_name = selected_result.find_by_tag("td").first.text
        selected_result_url = selected_result["onclick"][
            selected_result["onclick"].find("/") : selected_result["onclick"].rfind("/") + 1
        ]

        # Press Enter key.
        input_field.type(Keys.ENTER)

        # Assert that user was navigated to the selected result page.
        page_title_xpath = f"//div[@id='page-title']/h1//span[normalize-space()='{selected_result_name}']"
        self.assertTrue(self.browser.is_element_present_by_xpath(page_title_xpath, wait_time=10))
        self.assertEqual(self.browser.url, self.live_server_url + selected_result_url)
