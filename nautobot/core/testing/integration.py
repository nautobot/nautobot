import os

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.functional import classproperty
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from splinter.browser import Browser
from splinter.exceptions import ElementDoesNotExist

from nautobot.core import testing

# URL used to connect to the Selenium host
SELENIUM_URL = os.getenv("NAUTOBOT_SELENIUM_URL", "http://localhost:4444/wd/hub")

# Hostname used by Selenium client to talk to Nautobot
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "host.docker.internal")

# Default login URL
LOGIN_URL = reverse(settings.LOGIN_URL)


class ObjectsListMixin:
    """
    Helper class for easier testing and navigating on standard Nautobot objects list page.
    """

    def select_all_items(self):
        self.browser.find_by_xpath('//*[@id="object_list_form"]//input[@class="toggle"]').click()

    def select_one_item(self):
        self.browser.find_by_xpath('//*[@id="object_list_form"]//input[@name="pk"]').click()

    def click_bulk_delete(self):
        self.browser.find_by_xpath(
            '//*[@id="object_list_form"]//button[@type="submit"]/following-sibling::button[1]'
        ).click()
        self.browser.find_by_xpath('//*[@id="object_list_form"]//button[@name="_delete"]').click()

    def click_bulk_edit(self):
        self.browser.find_by_xpath('//*[@id="object_list_form"]//button[@type="submit"]').click()

    @property
    def objects_list_visible_items(self):
        objects_table_container = self.browser.find_by_xpath('//*[@id="object_list_form"]/div[1]/div')
        try:
            objects_table = objects_table_container.find_by_tag("tbody")
            return len(objects_table.find_by_tag("tr"))
        except ElementDoesNotExist:
            return 0

    def apply_filter(self, field, value):
        self.browser.find_by_xpath('//*[@id="id__filterbtn"]').click()
        self.fill_filters_select2_field(field, value)
        self.browser.find_by_xpath('//*[@id="default-filter"]//button[@type="submit"]').click()


class BulkOperationsMixin:
    def confirm_bulk_delete_operation(self):
        self.browser.find_by_xpath('//button[@name="_confirm" and @type="submit"]').click()

    def submit_bulk_edit_operation(self):
        self.browser.find_by_xpath("//button[@name='_apply']", wait_time=5).click()

    def wait_for_job_result(self):
        end_statuses = ["Completed", "Failed"]
        WebDriverWait(self.browser, 30).until(
            lambda driver: driver.find_by_id("pending-result-label").text in end_statuses
        )

        return self.browser.find_by_id("pending-result-label").text

    def verify_job_description(self, expected_job_description):
        job_description = self.browser.find_by_xpath('//td[text()="Job Description"]/following-sibling::td[1]').text
        self.assertEqual(job_description, expected_job_description)

    def assertIsBulkDeleteJob(self):
        self.verify_job_description("Bulk delete objects.")

    def assertIsBulkEditJob(self):
        self.verify_job_description("Bulk edit objects.")

    def assertJobStatusIsCompleted(self):
        job_status = self.wait_for_job_result()
        self.assertEqual(job_status, "Completed")


# In CI, sometimes the FQDN of SELENIUM_HOST gets used, other times it seems to be just the hostname?
@override_settings(ALLOWED_HOSTS=["nautobot.example.com", SELENIUM_HOST, SELENIUM_HOST.split(".")[0]])
@tag("integration")
class SeleniumTestCase(StaticLiveServerTestCase, testing.NautobotTestCaseMixin):
    """
    Base test case for Splinter Selenium integration testing with custom helper methods.

    This extends `django.contrib.staticfiles.testing.StaticLiveServerTestCase`
    so there is no need to run `collectstatic` prior to running tests.
    """

    host = "0.0.0.0"  # noqa: S104  # hardcoded-bind-all-interfaces -- false positive
    selenium_host = SELENIUM_HOST  # Docker: `nautobot`; else `host.docker.internal`

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Instantiate the browser object.
        cls.browser = Browser(
            "remote",
            command_executor=SELENIUM_URL,
            # See: https://developer.mozilla.org/en-US/docs/Web/WebDriver/Timeouts
            # desired_capabilities={"timeouts": {"implicit": 60 * 60 * 1000 }},  # 1 hour timeout
        )

    def setUp(self):
        super().setUpNautobot(populate_status=True)

        self.password = "testpassword"  # noqa: S105  # hardcoded-password-string
        self.user.set_password(self.password)
        self.user.save()

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def live_server_url(cls):  # pylint: disable=no-self-argument
        return f"http://{cls.selenium_host}:{cls.server_thread.port}"

    @classmethod
    def tearDownClass(cls):
        """Close down the browser after tests are ran."""
        cls.browser.quit()

    def login(self, username, password, login_url=LOGIN_URL, button_text="Log In"):
        """
        Navigate to `login_url` and perform a login w/ the provided `username` and `password`.
        """
        self.browser.visit(f"{self.live_server_url}{login_url}")
        self.browser.fill("username", username)
        self.browser.fill("password", password)
        self.browser.find_by_xpath(f"//button[text()='{button_text}']").first.click()

        if self.browser.is_text_present("Please enter a correct username and password."):
            self.fail(f"Unable to login in with username {username}")

    def logout(self):
        self.browser.visit(f"{self.live_server_url}/logout")

    def click_navbar_entry(self, parent_menu_name, child_menu_name):
        """
        Helper function to click on a parent menu and child menu in the navigation bar.
        """

        parent_menu_xpath = f"//*[@id='navbar']//a[@class='dropdown-toggle' and normalize-space()='{parent_menu_name}']"
        parent_menu = self.browser.find_by_xpath(parent_menu_xpath, wait_time=5)
        if not parent_menu["aria-expanded"] == "true":
            parent_menu.click()
        child_menu_xpath = f"{parent_menu_xpath}/following-sibling::ul//li[.//a[normalize-space()='{child_menu_name}']]"
        child_menu = self.browser.find_by_xpath(child_menu_xpath, wait_time=5)
        child_menu.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def click_list_view_add_button(self):
        """
        Helper function to click the "Add" button on a list view.
        """
        add_button = self.browser.find_by_xpath("//a[@id='add-button']", wait_time=5)
        add_button.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def click_edit_form_create_button(self):
        """
        Helper function to click the "Create" button on a form.
        """
        add_button = self.browser.find_by_xpath("//button[@name='_create']", wait_time=5)
        add_button.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def _fill_select2_field(self, field_name, value, search_box_class=None):
        """
        Helper function to fill a Select2 single selection field.
        """
        if search_box_class is None:
            search_box_class = "select2-search select2-search--dropdown"

        self.browser.find_by_xpath(f"//select[@id='id_{field_name}']//following-sibling::span").click()
        search_box = self.browser.find_by_xpath(f"//*[@class='{search_box_class}']//input", wait_time=5)
        for _ in search_box.first.type(value, slowly=True):
            pass

        # wait for "searching" to disappear
        self.browser.is_element_not_present_by_css(".loading-results", wait_time=5)
        return search_box

    def fill_select2_field(self, field_name, value):
        """
        Helper function to fill a Select2 single selection field on add/edit forms.
        """
        search_box = self._fill_select2_field(field_name, value)
        search_box.first.type(Keys.ENTER)

    def fill_filters_select2_field(self, field_name, value):
        """
        Helper function to fill a Select2 single selection field on filters modals.
        """
        self._fill_select2_field(field_name, value, search_box_class="select2-search select2-search--inline")
        self.browser.find_by_xpath(f"//li[@class='select2-results__option' and text()='{value}']").click()

    def fill_select2_multiselect_field(self, field_name, value):
        """
        Helper function to fill a Select2 multi-selection field.
        """
        search_box = self.browser.find_by_xpath(f"//select[@id='id_{field_name}']//following-sibling::span//input")
        for _ in search_box.first.type(value, slowly=True):
            pass

        # wait for "searching" to disappear
        self.browser.is_element_not_present_by_css(".loading-results", wait_time=5)
        search_box.first.type(Keys.ENTER)
