import os
from typing import Any, Optional

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Model
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
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "nautobot")

# Default login URL
LOGIN_URL = reverse(settings.LOGIN_URL)


class ObjectsListMixin:
    """
    Helper class for easier testing and navigating on standard Nautobot objects list page.
    """

    def select_all_items(self):
        """
        Click "toggle all" on top of the items table list to select all rows.
        """
        self.browser.find_by_css("#object_list_form input.toggle").click()

    def select_one_item(self):
        """
        Click first row checkbox on items table list to select one row.
        """
        self.browser.find_by_css('#object_list_form input[name="pk"]').click()

    def set_per_page(self, per_page=1):
        """
        Explicitly set the `per_page` parameter by navigating to the "current" page but with query param.
        TODO: check if there are other query params and merge them
        """
        self.browser.visit(f"{self.browser.url}?per_page={per_page}")

    def select_all_items_from_all_pages(self):
        """
        Selecting all the items from all pages by clicking "select all" on top of the items table list and then
        select all on prompt that will show up.
        """
        self.select_all_items()
        self.browser.find_by_css("#select_all").click()

    def click_bulk_delete(self):
        """
        Click bulk delete from dropdown menu on bottom of the items table list.
        """
        self.browser.execute_script(
            "document.querySelector('#object_list_form button[type=\"submit\"]').scrollIntoView()"
        )
        self.browser.find_by_xpath(
            '//*[@id="object_list_form"]//button[@type="submit"]/following-sibling::button[1]'
        ).click()
        self.browser.find_by_css('#object_list_form button[name="_delete"]').click()

    def click_bulk_delete_all(self):
        """
        Click bulk delete all on prompt when selecting all items from all pages.
        """
        self.click_button('#select_all_box button[name="_delete"]')

    def click_bulk_edit(self):
        """
        Click bulk edit button on bottom of the items table list.
        """
        self.click_button('#object_list_form button[type="submit"]')

    def click_bulk_edit_all(self):
        """
        Click bulk edit all on prompt when selecting all items from all pages.
        """
        self.click_button('#select_all_box button[name="_edit"]')

    @property
    def objects_list_visible_items(self):
        """
        Calculating the visible items. Return 0 if there is no visible items.
        """
        objects_table_container = self.browser.find_by_xpath('//*[@id="object_list_form"]')
        try:
            objects_table = objects_table_container.find_by_tag("tbody")
            return len(objects_table.find_by_tag("tr"))
        except ElementDoesNotExist:
            return 0

    def apply_filter(self, field, value):
        """
        Open filter dialog and apply select2 filters.
        You can apply more values to the same filter, by calling this function with same name but different value.
        """
        self.browser.find_by_xpath('//*[@id="id__filterbtn"]').click()
        self.fill_filters_select2_field(field, value)
        self.click_button('#default-filter button[type="submit"]')


class BulkOperationsMixin:
    def confirm_bulk_delete_operation(self):
        """
        Confirms bulk delete operation on the "warning" page after clicking bulk delete buttons.
        """
        self.click_button('button[name="_confirm"][type="submit"]')

    def submit_bulk_edit_operation(self):
        """
        Submits the bulk edit form.
        """
        self.click_button('button[name="_apply"]')

    def wait_for_job_result(self):
        """
        Waits 30s for job to be finished.
        """
        end_statuses = ["Completed", "Failed"]
        WebDriverWait(self.browser, 30).until(
            lambda driver: driver.find_by_id("pending-result-label").text in end_statuses
        )

        return self.browser.find_by_id("pending-result-label").text

    def verify_job_description(self, expected_job_description):
        """
        Verifies if the job description is correct.
        Waits 30s on page load in case of large payload being sent from bulk edit form.
        """
        WebDriverWait(self.browser, 30).until(lambda driver: driver.is_text_present("Job Description"))

        job_description = self.browser.find_by_xpath('//td[text()="Job Description"]/following-sibling::td[1]').text
        self.assertEqual(job_description, expected_job_description)

    def update_edit_form_value(self, field_name, value, is_select=False):
        """
        Updates bulk edit form value.
        """
        if is_select:
            self.fill_select2_field(field_name, value)
        else:
            self.browser.fill(field_name, value)

    def assertBulkDeleteConfirmMessageIsValid(self, expected_count):
        """
        Asserts that bulk delete confirmation message is valid and if we're deleting proper number of items.
        """
        self.browser.is_element_present_by_tag("body", wait_time=30)

        button_text = self.browser.find_by_xpath('//button[@name="_confirm" and @type="submit"]').text
        self.assertIn(f"Delete these {expected_count}", button_text)

        message_text = self.browser.find_by_id("confirm-bulk-deletion").find_by_xpath('//div[@class="panel-body"]').text
        self.assertIn(f"The following operation will delete {expected_count}", message_text)

    def assertIsBulkDeleteJob(self):
        """
        Asserts if currently visible job is bulk delete job.
        """
        self.verify_job_description("Bulk delete objects.")

    def assertIsBulkEditJob(self):
        """
        Asserts if currently visible job is bulk edit job.
        """
        self.verify_job_description("Bulk edit objects.")

    def assertJobStatusIsCompleted(self):
        """
        Asserts that job was successfully completed.
        """
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
        self.browser.find_by_xpath(f"//li[contains(@class, 'select2-results__option') and text()='{value}']").click()

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

    def click_button(self, query_selector):
        btn = self.browser.find_by_css(query_selector, wait_time=5)
        # Button might be visible but on the edge and then impossible to click due to vertical/horizontal scrolls
        self.browser.execute_script(f"document.querySelector('{query_selector}').scrollIntoView()")
        btn.click()

    def login_as_superuser(self):
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)


class BulkOperationsTestCases:
    """
    Helper classes that runs all the basic bulk-operations test cases like edit/delete with
    filtered / not filtered items along with select all option.

    To use this class create required items in setUp method:
    - at least four entities in two different groups,
    - provide field for filtering to distinguish between above two groups
    - provide expected counts (if different from default)
    - set edit field and value
    """

    class BaseTestCase(SeleniumTestCase):
        model_menu_path: tuple[str, str]
        model_base_viewname: str
        model_edit_data: dict[str, Any]
        model_filter_by: dict[str, Any]
        model_class: type[Model]
        override_model_plural: Optional[str] = None
        model_expected_counts: dict[str, int] = {
            "all": 5,
            "filtered": 2,
        }

        @property
        def model_plural(self) -> str:
            if self.override_model_plural is None:
                return self.model_class._meta.verbose_name_plural

            return self.override_model_plural

        def setUp(self):
            super().setUp()

            self.setup_items()
            self.login_as_superuser()
            self.go_to_model_list_page()

        def tearDown(self):
            self.logout()
            super().tearDown()

        def go_to_model_list_page(self):
            self.click_navbar_entry(*self.model_menu_path)
            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_list"))

        def setup_items(self):
            raise NotImplementedError

    class BulkEditTestCase(BaseTestCase, ObjectsListMixin, BulkOperationsMixin):
        def test_bulk_edit_require_selection(self):
            # Click "edit selected" without selecting anything
            self.click_bulk_edit()

            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_list"))
            self.assertTrue(self.browser.is_text_present(f"No {self.model_plural} were selected", wait_time=5))

        def test_bulk_edit_all_items(self):
            # Select all items and edit them
            self.select_all_items()
            self.click_bulk_edit()
            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"))

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["all"])

        def test_bulk_edit_one_item(self):
            # Select one filtered item
            self.select_one_item()
            self.click_bulk_edit()
            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"))

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, 1)

        def test_bulk_edit_all_items_from_all_pages(self):
            # Select all from all pages
            self.set_per_page()
            self.select_all_items_from_all_pages()
            self.click_bulk_edit_all()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"), self.browser.url)

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["all"])

        def test_bulk_edit_all_filtered_items(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all filtered items
            self.select_all_items()
            self.click_bulk_edit()
            self.assertIn(
                self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"),
                self.browser.url,
            )

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["filtered"])

        def test_bulk_edit_one_filtered_item(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select one item and edit it
            self.select_one_item()
            self.click_bulk_edit()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"), self.browser.url)

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, 1)

        def test_bulk_edit_all_filtered_items_from_all_pages(self):
            # Filter items
            self.set_per_page()
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all items and delete them
            self.select_all_items_from_all_pages()
            self.click_bulk_edit_all()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"), self.browser.url)

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["filtered"])

    class BulkDeleteTestCase(BaseTestCase, ObjectsListMixin, BulkOperationsMixin):
        def test_bulk_delete_require_selection(self):
            # Click "delete selected" without selecting anything
            self.click_bulk_delete()

            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_list"))
            self.assertTrue(
                self.browser.is_text_present(f"No {self.model_plural} were selected for deletion.", wait_time=5)
            )

        def test_bulk_delete_all_items(self):
            # Select all items and delete them
            self.select_all_items()
            self.click_bulk_delete()

            self.assertEqual(
                self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete")
            )
            self.assertBulkDeleteConfirmMessageIsValid(self.model_expected_counts["all"])
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, 0)

        def test_bulk_delete_one_item(self):
            # Select one item and delete it
            self.select_one_item()
            self.click_bulk_delete()

            self.assertEqual(
                self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete")
            )
            self.assertBulkDeleteConfirmMessageIsValid(1)
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, self.model_expected_counts["all"] - 1)

        def test_bulk_delete_all_items_from_all_pages(self):
            # Select all from all pages
            self.set_per_page()
            self.select_all_items_from_all_pages()
            self.click_bulk_delete_all()

            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.assertBulkDeleteConfirmMessageIsValid(self.model_expected_counts["all"])
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, 0)

        def test_bulk_delete_all_filtered_items(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all items and delete them
            self.select_all_items()
            self.click_bulk_delete()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            rest_items_count = self.model_expected_counts["all"] - self.model_expected_counts["filtered"]
            self.assertEqual(self.objects_list_visible_items, rest_items_count)

        def test_bulk_delete_one_filtered_items(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select one item and delete it
            self.select_one_item()
            self.click_bulk_delete()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, self.model_expected_counts["all"] - 1)

        def test_bulk_delete_all_filtered_items_from_all_pages(self):
            # Filter items
            self.set_per_page()
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all items and delete them
            self.select_all_items_from_all_pages()
            self.click_bulk_delete_all()

            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.assertBulkDeleteConfirmMessageIsValid(self.model_expected_counts["filtered"])
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.set_per_page(50)  # Set page size back to default
            rest_items_count = self.model_expected_counts["all"] - self.model_expected_counts["filtered"]
            self.assertEqual(self.objects_list_visible_items, rest_items_count)

            # Filter again and assert that all items were deleted
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)
            self.assertEqual(self.objects_list_visible_items, 0)

    class BulkOperationsTestCase(BulkEditTestCase, BulkDeleteTestCase):
        pass
