from urllib.parse import parse_qs, urlparse

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from nautobot.core.constants import PAGINATE_COUNT_DEFAULT
from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status


class PaginatorTestCase(SeleniumTestCase):
    """Integration tests for the paginator."""

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

        location_type, _ = LocationType.objects.get_or_create(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        Location.objects.bulk_create(
            [
                Location(name=f"Paginator Test Location {i}", location_type=location_type, status=location_status)
                for i in range(PAGINATE_COUNT_DEFAULT + 1)
            ]
        )

    def _assert_input_visible(self):
        """Ensure page input field is visible."""
        page_input_field = self.browser.find_by_id("paginator-go-to", wait_time=5)
        self.scroll_element_into_view(element=page_input_field)
        self.assertTrue(page_input_field.is_visible())
        return page_input_field

    # Test input paginator
    def test_pagination_input_field(self):
        """Ensure the presence of input field for pages with pagination vs no pagination."""
        # The input is present on a page with enough objects to paginate.
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        self._assert_input_visible()
        # The input is not present on a page with a single page of objects.
        self.browser.visit(f"{self.live_server_url}/dcim/controllers/")
        self.assertFalse(self.browser.is_element_present_by_id("paginator-go-to"))

    def _assert_page_loads(self, page_num: str):
        """Assert the page loads correctly on page input submission."""
        WebDriverWait(self.browser.driver, 5).until(ec.url_contains(f"page={page_num}"))
        query_params = parse_qs(urlparse(self.browser.url).query)
        self.assertEqual(query_params.get("page"), [page_num])

    def test_pagination_routing(self):
        """Check that the pate loads correct pages both on Enter/return and button click."""
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        page_input_field = self._assert_input_visible()
        field = page_input_field.first
        field.fill("2")
        field.type(Keys.RETURN)

        self._assert_page_loads("2")

        page_input_field = self._assert_input_visible()
        field = page_input_field.first
        field.fill("1")
        go_button = self.browser.find_by_id("paginator-go-to-link", wait_time=5)
        go_button.click()
        self._assert_page_loads("1")

    # Test button paginator
    def test_page_links_pagination(self):
        """Check that the main paginator's behavior."""
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        # The numbered "2" page link navigates to page 2.
        page_2_link = self.browser.find_by_xpath(
            "//nav//a[contains(@class, 'page-link') and normalize-space(text())='2']", wait_time=5
        ).first
        self.scroll_element_into_view(element=page_2_link)
        page_2_link.click()
        WebDriverWait(self.browser.driver, 5).until(ec.url_contains("page=2"))
        self.assertEqual(parse_qs(urlparse(self.browser.url).query).get("page"), ["2"])

        # The "Previous" («) button returns to page 1.
        previous_button = self.browser.find_by_xpath("//nav//a[@aria-label='Previous']", wait_time=5).first
        self.scroll_element_into_view(element=previous_button)
        previous_button.click()
        WebDriverWait(self.browser.driver, 5).until(lambda driver: "page=2" not in driver.current_url)
        self.assertNotEqual(parse_qs(urlparse(self.browser.url).query).get("page"), ["2"])

        # The "Next" (») button advances to page 2 again.
        next_button = self.browser.find_by_xpath("//nav//a[@aria-label='Next']", wait_time=5).first
        self.scroll_element_into_view(element=next_button)
        next_button.click()
        WebDriverWait(self.browser.driver, 5).until(ec.url_contains("page=2"))
        self.assertEqual(parse_qs(urlparse(self.browser.url).query).get("page"), ["2"])
